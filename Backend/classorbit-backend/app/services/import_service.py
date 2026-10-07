import uuid
import logging
import hashlib
import re
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.enums import (
    AllocationType,
    AllocationStatus,
    ConfidenceLevel,
    ImportStatus,
    MappingStatus,
    ReviewAction,
    TimetableEntryStatus,
    ValidationStatus,
)
from app.models.import_record import FileImport, ImportReview
from app.models.master_data import Building, Classroom, Department, Faculty, Floor, RoomType, Subject
from app.models.timetable import ClassroomAllocation, Timetable, TimetableEntry, TimeSlot
from app.models.user import User
from app.parsers.base import ParsedDocument, ParserCapabilityError
from app.parsers.factory import get_parser_for_file
from app.services.timetable_mapper import TimetableMapper
from app.services.timetable_confidence import TimetableConfidenceScorer
from app.services.timetable_normalizer import NormalizedTimetableEntry, TimetableNormalizer
from app.services.timetable_validator import TimetableValidator
from app.utils.text_normalization import normalize_room_hint, normalize_space
from app.utils.time_utils import overlaps, parse_time_value, time_to_string


logger = logging.getLogger(__name__)
PARSER_VERSION = "12.0"


class ImportService:
    def __init__(self) -> None:
        self.normalizer = TimetableNormalizer()
        self.validator = TimetableValidator()
        self.mapper = TimetableMapper()
        self.confidence = TimetableConfidenceScorer()

    async def create_import_from_upload(
        self,
        db: Session,
        upload: UploadFile,
        uploaded_by: User,
        *,
        standard_only: bool = False,
    ) -> FileImport:
        settings = get_settings()
        filename = upload.filename or "timetable-upload"
        suffix = Path(filename).suffix.lower()
        safe_name = f"{uuid.uuid4()}{suffix}"
        destination = settings.uploads_path / safe_name
        content = await upload.read()
        if len(content) > settings.max_upload_mb * 1024 * 1024:
            raise ValueError(f"Upload is larger than {settings.max_upload_mb} MB.")
        content_hash = hashlib.sha256(content).hexdigest()
        existing = db.execute(
            select(FileImport).where(
                FileImport.sha256 == content_hash,
                FileImport.parser_version == PARSER_VERSION,
                FileImport.status.in_([ImportStatus.COMPLETED, ImportStatus.NEEDS_REVIEW]),
            ).order_by(FileImport.created_at.desc())
        ).scalars().first()
        if existing and (not standard_only or (existing.metadata_json or {}).get("standard_template")):
            return existing
        destination.write_bytes(content)

        file_import = FileImport(
            original_filename=filename,
            file_type=suffix.lstrip(".") or "unknown",
            stored_path=str(destination),
            uploaded_by_id=uploaded_by.id,
            status=ImportStatus.UPLOADED,
            sha256=content_hash,
            parser_version=PARSER_VERSION,
        )
        db.add(file_import)
        db.commit()
        db.refresh(file_import)
        return self.process_import(db, file_import, standard_only=standard_only)

    def process_import(self, db: Session, file_import: FileImport, *, standard_only: bool = False) -> FileImport:
        file_import.status = ImportStatus.PROCESSING
        db.commit()

        source_path = Path(file_import.stored_path)
        try:
            parser = get_parser_for_file(source_path)
            if standard_only and parser.__class__.__name__ != "ClassOrbitTemplateParser":
                raise ParserCapabilityError(
                    "This workbook does not match the official ClassOrbit timetable template. "
                    "Download a fresh template and keep its timetable structure unchanged."
                )
            parsed_document = parser.parse(source_path)
            is_standard_template = bool(parsed_document.metadata.get("standard_template"))
            is_authoritative_timetable = bool(
                is_standard_template or parsed_document.metadata.get("authoritative_timetable")
            )
            classroom_summary = self._import_classroom_records(
                db, parsed_document.metadata.get("classroom_records") or []
            )
            detected_time_slots = self._detected_time_slots(parsed_document)
            for start_time, end_time in detected_time_slots:
                self._get_or_create_time_slot(db, start_time, end_time)
            file_import.page_count = parsed_document.page_count
            file_import.parser_version = PARSER_VERSION
            file_import.metadata_json = parsed_document.metadata
            generated = 0
            valid = 0
            needs_review = 0
            invalid = 0
            unmatched_rooms: set[str] = set()
            matched_classrooms = 0
            created_classrooms = 0
            departments: set[str] = set()
            programs: set[str] = set()
            warnings = list(parsed_document.warnings)
            warnings.extend(classroom_summary["warnings"])
            confidence_counts = {level.value: 0 for level in ConfidenceLevel}
            duplicate_count = 0
            conflict_count = 0
            failed_records = 0
            seen_semantic_entries: set[tuple] = set()
            staged_entries: list[tuple[NormalizedTimetableEntry, Classroom | None]] = []
            active_entries = db.execute(
                select(TimetableEntry).join(Timetable).where(Timetable.status == "ACTIVE")
            ).scalars().all()
            active_allocations = db.execute(
                select(ClassroomAllocation).where(
                    ClassroomAllocation.status == AllocationStatus.ALLOCATED,
                    ClassroomAllocation.timetable_entry_id.is_(None),
                )
            ).scalars().all()
            preview: list[dict] = []

            slot_conflicts = self._overlapping_slot_warnings(detected_time_slots)
            conflict_count += len(slot_conflicts)
            warnings.extend(slot_conflicts)

            for cell in parsed_document.cells:
                normalized_entries = self.normalizer.normalize_cell(cell, parsed_document.metadata)
                for normalized_entry in normalized_entries:
                    if normalized_entry.department_name:
                        departments.add(normalized_entry.department_name)
                    if normalized_entry.program_name:
                        programs.add(normalized_entry.program_name)
                    generated += 1
                    normalized_entry = self.validator.validate(normalized_entry)
                    if (
                        is_standard_template
                        and cell.metadata.get("standard_warning")
                        and normalized_entry.validation_status == ValidationStatus.INVALID
                    ):
                        normalized_entry.validation_status = ValidationStatus.NEEDS_REVIEW
                    semantic_key = (
                        normalized_entry.academic_year,
                        normalized_entry.class_name,
                        normalized_entry.department_name,
                        normalized_entry.division,
                        normalized_entry.day_of_week,
                        normalized_entry.start_time,
                        normalized_entry.end_time,
                        (normalized_entry.subject_text or "").casefold(),
                        (normalized_entry.room_hint or "").casefold(),
                    )
                    if semantic_key in seen_semantic_entries:
                        duplicate_count += 1
                        normalized_entry.validation_status = ValidationStatus.NEEDS_REVIEW
                        normalized_entry.warning = self._append_warning(
                            normalized_entry.warning, "Possible semantic duplicate in this import."
                        )
                    seen_semantic_entries.add(semantic_key)

                    try:
                        with db.begin_nested():
                            normalized_entry, classroom = self.mapper.map_classroom(
                                db,
                                normalized_entry,
                                create_missing=(
                                    get_settings().create_missing_classrooms_from_import
                                    and normalized_entry.validation_status == ValidationStatus.VALID
                                ),
                            )
                            if normalized_entry.mapping_status in {MappingStatus.UNMATCHED, MappingStatus.AMBIGUOUS}:
                                normalized_entry.validation_status = ValidationStatus.NEEDS_REVIEW
                                normalized_entry.warning = self._append_warning(
                                    normalized_entry.warning,
                                    "Room mapping is unresolved; admin mapping is required.",
                                )
                            conflict_warnings = self._entry_conflict_warnings(
                                normalized_entry,
                                classroom,
                                staged_entries,
                                active_entries,
                                active_allocations,
                            )
                            if conflict_warnings:
                                conflict_count += len(conflict_warnings)
                                if (
                                    not is_authoritative_timetable
                                    and normalized_entry.validation_status != ValidationStatus.INVALID
                                ):
                                    normalized_entry.validation_status = ValidationStatus.NEEDS_REVIEW
                                for conflict_warning in conflict_warnings:
                                    normalized_entry.warning = self._append_warning(
                                        normalized_entry.warning, conflict_warning
                                    )
                            normalized_entry = self.confidence.score(normalized_entry)
                            confidence_counts[normalized_entry.confidence_level.value] += 1
                            if len(preview) < 20:
                                preview.append(self._preview_entry(normalized_entry))
                            review = self._create_review_record(
                                db, file_import, normalized_entry, classroom.id if classroom else None
                            )
                            if classroom:
                                matched_classrooms += 1
                                if (normalized_entry.normalized_json.get("classroom_mapping") or {}).get("action") == "created":
                                    created_classrooms += 1
                            staged_entries.append((normalized_entry, classroom))
                            if normalized_entry.validation_status == ValidationStatus.VALID:
                                valid += 1
                                entry = self._persist_review_record(db, review)
                                review.timetable_entry_id = entry.id
                                review.action = ReviewAction.ACCEPTED
                            elif normalized_entry.validation_status == ValidationStatus.NEEDS_REVIEW:
                                needs_review += 1
                            else:
                                invalid += 1
                                review.action = ReviewAction.INVALID
                    except Exception as exc:
                        failed_records += 1
                        invalid += 1
                        warning = f"Cell {normalized_entry.source_cell_reference or 'unknown'} failed: {exc}"
                        warnings.append(warning)
                        logger.warning(warning)
                    if normalized_entry.mapping_status.value == "UNMATCHED" and normalized_entry.room_hint:
                        unmatched_rooms.add(normalized_entry.room_hint)
                    if normalized_entry.warning:
                        warnings.append(normalized_entry.warning)

            file_import.summary_json = {
                "source_cells": len(parsed_document.cells),
                "generated_timetable_entries": generated,
                "valid": valid,
                "needs_review": needs_review,
                "invalid": invalid,
                "unmatched_rooms": sorted(unmatched_rooms),
                "matched_classrooms": matched_classrooms,
                "created_classrooms": created_classrooms,
                "classroom_import": classroom_summary,
                "departments": sorted(departments),
                "programs": sorted(programs),
                "warnings": sorted(set(warnings)),
                "pages_processed": parsed_document.page_count or 0,
                "pages_successfully_extracted": parsed_document.pages_extracted,
                "ocr_pages": parsed_document.ocr_pages,
                "template_detected": parsed_document.template_name,
                "parser": parsed_document.parser_name,
                "confidence": confidence_counts,
                "possible_duplicates": duplicate_count,
                "conflicts": conflict_count,
                "empty_slots": max(
                    0,
                    len(detected_time_slots) * len(parsed_document.metadata.get("column_order") or [])
                    - len(parsed_document.cells),
                ),
                "pending_confirmation": bool(needs_review or invalid),
                "unparsed_cells": failed_records,
                "preview": preview,
                "trace": parsed_document.trace,
                "detected_structure": {
                    "columns": list(dict.fromkeys([
                        *(parsed_document.metadata.get("column_order") or []),
                        *(cell.source_column for cell in parsed_document.cells if cell.source_column),
                    ])),
                    "time_slots": [
                        f"{time_to_string(start)}-{time_to_string(end)}"
                        for start, end in detected_time_slots
                    ],
                },
                "recognized_entities": {
                    "classes": sorted({cell.class_name for cell in parsed_document.cells if cell.class_name}),
                    "departments": sorted(departments),
                    "programs": sorted(programs),
                },
                "unknown_unclassified_content": len({
                    (key, str(value))
                    for cell in parsed_document.cells
                    for key, value in (cell.metadata.get("attributes") or {}).items()
                    if key.startswith("source_")
                }),
            }
            self._supersede_previous_file_versions(db, file_import)
            file_import.status = (
                ImportStatus.NEEDS_REVIEW
                if (
                    needs_review
                    or invalid
                    or generated == 0
                    or classroom_summary["invalid"]
                    or (conflict_count and not is_authoritative_timetable)
                )
                else ImportStatus.COMPLETED
            )
            db.commit()
            db.refresh(file_import)
            return file_import
        except (ParserCapabilityError, ValueError, RuntimeError) as exc:
            db.rollback()
            file_import = db.get(FileImport, file_import.id)
            file_import.status = ImportStatus.FAILED
            file_import.error_message = str(exc)
            file_import.summary_json = {"error": str(exc)}
            db.commit()
            db.refresh(file_import)
            return file_import
        except Exception as exc:
            db.rollback()
            logger.exception("Unexpected timetable import failure for %s", file_import.id)
            file_import = db.get(FileImport, file_import.id)
            file_import.status = ImportStatus.FAILED
            file_import.error_message = f"Unexpected import error: {exc}"
            file_import.summary_json = {"error": file_import.error_message}
            db.commit()
            db.refresh(file_import)
            return file_import

    def update_review_record(
        self,
        db: Session,
        review: ImportReview,
        *,
        changes: dict,
    ) -> ImportReview:
        matched_classroom_id = changes.get("matched_classroom_id")
        for field, value in changes.items():
            if hasattr(review, field):
                setattr(review, field, value)
        if matched_classroom_id:
            classroom = db.get(Classroom, matched_classroom_id)
            if not classroom:
                raise ValueError("Mapped classroom does not exist.")
            review.room_hint = classroom.room_number
            review.mapping_status = MappingStatus.MATCHED
        elif "room_hint" in changes:
            if not review.room_hint:
                review.matched_classroom_id = None
                review.mapping_status = MappingStatus.NONE
            else:
                room_key = self.mapper._room_key(review.room_hint)
                matches = [
                    classroom
                    for classroom in db.execute(select(Classroom)).scalars().all()
                    if room_key in {
                        self.mapper._room_key(classroom.room_number),
                        self.mapper._room_key(classroom.display_name),
                    }
                ]
                if len(matches) == 1:
                    review.matched_classroom_id = matches[0].id
                    review.room_hint = matches[0].room_number
                    review.mapping_status = MappingStatus.MATCHED
                else:
                    review.matched_classroom_id = None
                    review.mapping_status = MappingStatus.AMBIGUOUS if len(matches) > 1 else MappingStatus.UNMATCHED
        if review.action in {ReviewAction.ACCEPTED, ReviewAction.EDITED}:
            start_time = parse_time_value(review.start_time)
            end_time = parse_time_value(review.end_time)
            if not review.class_name or not review.day_of_week or not review.subject_text:
                review.validation_status = ValidationStatus.NEEDS_REVIEW
                review.warning = self._append_warning(review.warning, "Class, day, and subject are required.")
            elif not start_time or not end_time or end_time <= start_time:
                review.validation_status = ValidationStatus.NEEDS_REVIEW
                review.warning = self._append_warning(review.warning, "A valid start/end time is required.")
            elif review.room_hint and review.mapping_status != MappingStatus.MATCHED:
                review.validation_status = ValidationStatus.NEEDS_REVIEW
                review.warning = self._append_warning(review.warning, "Classroom mapping is still unresolved.")
            else:
                review.validation_status = ValidationStatus.VALID
        db.commit()
        db.refresh(review)
        return review

    def confirm_import(self, db: Session, file_import: FileImport) -> tuple[int, int, int]:
        created = 0
        skipped = 0
        unresolved = 0
        reviews = db.execute(select(ImportReview).where(ImportReview.file_import_id == file_import.id)).scalars().all()
        for review in reviews:
            if review.timetable_entry_id:
                skipped += 1
                continue
            if review.action in {ReviewAction.REJECTED, ReviewAction.IGNORED, ReviewAction.INVALID}:
                skipped += 1
                continue
            if review.validation_status == ValidationStatus.INVALID:
                skipped += 1
                continue
            if (
                review.room_hint
                and review.mapping_status == MappingStatus.UNMATCHED
                and not review.matched_classroom_id
            ):
                unresolved += 1
                continue
            if review.validation_status == ValidationStatus.NEEDS_REVIEW and review.action not in {
                ReviewAction.ACCEPTED,
                ReviewAction.EDITED,
            }:
                unresolved += 1
                continue
            try:
                entry = self._persist_review_record(db, review)
            except ValueError:
                skipped += 1
                continue
            review.timetable_entry_id = entry.id
            review.action = ReviewAction.ACCEPTED if review.action == ReviewAction.PENDING else review.action
            created += 1

        file_import.status = ImportStatus.NEEDS_REVIEW if unresolved else ImportStatus.COMPLETED
        file_import.summary_json = {
            **(file_import.summary_json or {}),
            "confirmed_entries": created,
            "unresolved": unresolved,
            "pending_confirmation": bool(unresolved),
        }
        db.commit()
        return created, skipped, unresolved

    def _create_review_record(
        self,
        db: Session,
        file_import: FileImport,
        entry: NormalizedTimetableEntry,
        matched_classroom_id: str | None,
    ) -> ImportReview:
        review = ImportReview(
            file_import_id=file_import.id,
            source_page=entry.source_page,
            source_sheet=entry.source_sheet,
            source_row=entry.source_row,
            source_column=entry.source_column,
            source_cell_reference=entry.source_cell_reference,
            college_name=entry.college_name,
            academic_year=entry.academic_year,
            class_name=entry.class_name,
            division=entry.division,
            semester=entry.semester,
            department_name=entry.department_name,
            program_name=entry.program_name,
            day_of_week=entry.day_of_week,
            start_time=entry.start_time_text,
            end_time=entry.end_time_text,
            subject_text=entry.subject_text,
            subject_code=entry.subject_code,
            subject_type=entry.subject_type,
            session_type=entry.session_type,
            delivery_mode=entry.delivery_mode,
            faculty_text=entry.faculty_text,
            room_hint=entry.room_hint,
            matched_classroom_id=matched_classroom_id,
            location_type=entry.location_type,
            activity_type=entry.activity_type,
            mapping_status=entry.mapping_status,
            validation_status=entry.validation_status,
            warning=entry.warning,
            raw_cell_text=entry.raw_cell_text,
            raw_entry_text=entry.raw_entry_text,
            normalized_json=entry.normalized_json,
            confidence_level=entry.confidence_level,
            confidence_score=entry.confidence_score,
            parser_name=entry.parser_name,
            template_name=entry.template_name,
            extraction_method=entry.extraction_method,
            bounding_box_json=list(entry.bounding_box) if entry.bounding_box else None,
            attributes_json=entry.attributes_json,
        )
        db.add(review)
        db.flush()
        return review

    def _persist_review_record(self, db: Session, review: ImportReview) -> TimetableEntry:
        start_time = parse_time_value(review.start_time)
        end_time = parse_time_value(review.end_time)
        if not review.class_name or not review.day_of_week or not start_time or not end_time or not review.subject_text:
            raise ValueError("Review record is missing required timetable fields.")

        department = self._get_or_create_department(db, review.department_name)
        timetable = self._get_or_create_timetable(db, review, department)
        time_slot = self._get_or_create_time_slot(db, start_time, end_time)
        subject_department = self._resolve_subject_department(db, review.subject_text, department)
        canonical_subject = self._canonical_subject_name(review.subject_text, subject_department)
        subject = self._get_or_create_subject(db, canonical_subject, subject_department)
        faculty = self._get_or_create_faculty(db, review.faculty_text, department)

        existing = db.execute(
            select(TimetableEntry).where(
                TimetableEntry.timetable_id == timetable.id,
                TimetableEntry.day_of_week == review.day_of_week,
                TimetableEntry.time_slot_id == time_slot.id,
                TimetableEntry.subject_text == review.subject_text,
                TimetableEntry.room_hint == review.room_hint,
                TimetableEntry.raw_entry_text == review.raw_entry_text,
            )
        ).scalar_one_or_none()
        if existing:
            return existing

        entry = TimetableEntry(
            timetable_id=timetable.id,
            day_of_week=review.day_of_week,
            time_slot_id=time_slot.id,
            subject_text=review.subject_text,
            subject_code=review.subject_code,
            subject_type=review.subject_type,
            session_type=review.session_type,
            delivery_mode=review.delivery_mode,
            subject_id=subject.id if subject else None,
            faculty_text=review.faculty_text,
            faculty_id=faculty.id if faculty else None,
            classroom_id=review.matched_classroom_id,
            room_hint=review.room_hint,
            location_type=review.location_type,
            activity_type=review.activity_type,
            mapping_status=review.mapping_status,
            validation_status=review.validation_status,
            status=TimetableEntryStatus.SCHEDULED,
            source_file_id=review.file_import_id,
            source_page=review.source_page,
            source_sheet=review.source_sheet,
            source_row=review.source_row,
            source_column=review.source_column,
            source_cell_reference=review.source_cell_reference,
            raw_cell_text=review.raw_cell_text,
            raw_entry_text=review.raw_entry_text,
            confidence_level=review.confidence_level,
            confidence_score=review.confidence_score,
            parser_name=review.parser_name,
            template_name=review.template_name,
            extraction_method=review.extraction_method,
            bounding_box_json=review.bounding_box_json,
            trace_json=review.normalized_json,
            attributes_json=review.attributes_json,
        )
        db.add(entry)
        db.flush()
        if entry.classroom_id:
            existing_allocation = db.execute(
                select(ClassroomAllocation).where(
                    ClassroomAllocation.classroom_id == entry.classroom_id,
                    ClassroomAllocation.status == AllocationStatus.ALLOCATED,
                    ClassroomAllocation.day_of_week == entry.day_of_week,
                    ClassroomAllocation.start_time == time_slot.start_time,
                    ClassroomAllocation.end_time == time_slot.end_time,
                    func.lower(ClassroomAllocation.title) == entry.subject_text.lower(),
                )
            ).scalars().first()
            if not existing_allocation:
                db.add(ClassroomAllocation(
                    classroom_id=entry.classroom_id,
                    timetable_entry_id=entry.id,
                    allocation_type=AllocationType.TIMETABLE,
                    title=entry.subject_text,
                    day_of_week=entry.day_of_week,
                    start_time=time_slot.start_time,
                    end_time=time_slot.end_time,
                    class_name=timetable.class_name,
                    division=timetable.division,
                    faculty_text=entry.faculty_text,
                ))
        db.flush()
        return entry

    def _import_classroom_records(self, db: Session, records: list[dict]) -> dict:
        summary = {"total": len(records), "created": 0, "updated": 0, "invalid": 0, "warnings": []}
        for record in records:
            source = f"{record.get('source_sheet', 'Classrooms')} row {record.get('source_row', '?')}"
            room_number = normalize_room_hint(record.get("room_number"))
            if not room_number:
                summary["invalid"] += 1
                summary["warnings"].append(f"{source}: room_number is required.")
                continue
            try:
                with db.begin_nested():
                    department = self._get_or_create_department(db, normalize_space(record.get("department")) or None)
                    building = self._get_or_create_building(db, normalize_space(record.get("building")) or None)
                    room_type = self._get_or_create_room_type(db, normalize_space(record.get("room_type")) or None)
                    floor = self._get_or_create_floor(db, building, normalize_space(record.get("floor")) or None)
                    capacity = self._parse_capacity(record.get("capacity"))
                    facilities = [
                        normalize_space(value)
                        for value in re.split(r"[,;|]", record.get("facilities") or "")
                        if normalize_space(value)
                    ]
                    classroom = db.execute(
                        select(Classroom).where(func.lower(Classroom.room_number) == room_number.lower())
                    ).scalar_one_or_none()
                    created = classroom is None
                    if classroom is None:
                        classroom = Classroom(room_number=room_number, facilities=[])
                        db.add(classroom)
                    classroom.display_name = normalize_space(record.get("display_name")) or classroom.display_name or room_number
                    classroom.building_id = building.id if building else classroom.building_id
                    classroom.floor_id = floor.id if floor else classroom.floor_id
                    classroom.room_type_id = room_type.id if room_type else classroom.room_type_id
                    classroom.department_id = department.id if department else classroom.department_id
                    classroom.capacity = capacity if capacity is not None else classroom.capacity
                    classroom.facilities = facilities or classroom.facilities
                    classroom.status = (normalize_space(record.get("status")) or classroom.status or "ACTIVE").upper()
                    db.flush()
                    summary["created" if created else "updated"] += 1
            except (ValueError, TypeError, IntegrityError) as exc:
                summary["invalid"] += 1
                summary["warnings"].append(f"{source}: {exc}")
        return summary

    @staticmethod
    def _parse_capacity(value: object) -> int | None:
        text = normalize_space(str(value)) if value is not None else ""
        if not text:
            return None
        try:
            capacity = int(float(text))
        except ValueError as exc:
            raise ValueError(f"capacity '{text}' is not a number.") from exc
        if capacity < 0:
            raise ValueError("capacity cannot be negative.")
        return capacity

    @staticmethod
    def _get_or_create_building(db: Session, name: str | None) -> Building | None:
        if not name:
            return None
        building = db.execute(select(Building).where(func.lower(Building.name) == name.lower())).scalar_one_or_none()
        if building:
            return building
        building = Building(name=name)
        db.add(building)
        db.flush()
        return building

    @staticmethod
    def _get_or_create_room_type(db: Session, name: str | None) -> RoomType | None:
        if not name:
            return None
        room_type = db.execute(select(RoomType).where(func.lower(RoomType.name) == name.lower())).scalar_one_or_none()
        if room_type:
            return room_type
        room_type = RoomType(name=name)
        db.add(room_type)
        db.flush()
        return room_type

    @staticmethod
    def _get_or_create_floor(db: Session, building: Building | None, value: str | None) -> Floor | None:
        if not building or not value:
            return None
        level_match = re.search(r"-?\d+", value)
        if not level_match:
            raise ValueError(f"floor '{value}' must contain a numeric level.")
        level = int(level_match.group())
        floor = db.execute(
            select(Floor).where(Floor.building_id == building.id, Floor.level == level)
        ).scalar_one_or_none()
        if floor:
            return floor
        floor = Floor(building_id=building.id, name=value, level=level)
        db.add(floor)
        db.flush()
        return floor

    @staticmethod
    def _overlapping_slot_warnings(slots: list[tuple]) -> list[str]:
        warnings: list[str] = []
        for index, (start_time, end_time) in enumerate(slots):
            for other_start, other_end in slots[index + 1:]:
                if overlaps(start_time, end_time, other_start, other_end):
                    warnings.append(
                        "Overlapping time slots detected: "
                        f"{time_to_string(start_time)}-{time_to_string(end_time)} and "
                        f"{time_to_string(other_start)}-{time_to_string(other_end)}."
                    )
        return warnings

    @staticmethod
    def _entry_conflict_warnings(
        entry: NormalizedTimetableEntry,
        classroom: Classroom | None,
        staged_entries: list[tuple[NormalizedTimetableEntry, Classroom | None]],
        active_entries: list[TimetableEntry],
        active_allocations: list[ClassroomAllocation],
    ) -> list[str]:
        if not entry.day_of_week or not entry.start_time or not entry.end_time:
            return []
        warnings: list[str] = []
        for other, other_classroom in staged_entries:
            if (
                other.day_of_week != entry.day_of_week
                or not other.start_time
                or not other.end_time
                or not overlaps(entry.start_time, entry.end_time, other.start_time, other.end_time)
            ):
                continue
            same_activity = (
                ImportService._activity_identity(other.subject_text)
                == ImportService._activity_identity(entry.subject_text)
                and other.start_time == entry.start_time
                and other.end_time == entry.end_time
                and bool(classroom and other_classroom and classroom.id == other_classroom.id)
            )
            if same_activity:
                continue
            same_class = (
                other.class_name == entry.class_name
                and other.division == entry.division
                and other.academic_year == entry.academic_year
                and other.department_name == entry.department_name
            )
            parallel_activity = bool(
                entry.attributes_json.get("parallel_activity")
                and other.attributes_json.get("parallel_activity")
            )
            if same_class and not parallel_activity:
                warnings.append("Class/division has overlapping scheduled activities in this import.")
            if classroom and other_classroom and classroom.id == other_classroom.id and not parallel_activity:
                warnings.append(f"Classroom {classroom.room_number} has overlapping activities in this import.")

        for existing in active_entries:
            if (
                existing.day_of_week != entry.day_of_week
                or not overlaps(entry.start_time, entry.end_time, existing.start_time, existing.end_time)
            ):
                continue
            timetable = existing.timetable
            same_context = (
                timetable.class_name == entry.class_name
                and timetable.division == entry.division
                and timetable.academic_year == entry.academic_year
                and timetable.semester == entry.semester
                and timetable.program_name == entry.program_name
            )
            if same_context:
                continue
            if classroom and existing.classroom_id == classroom.id:
                warnings.append(f"Classroom {classroom.room_number} overlaps an active allocation.")
        if classroom:
            for allocation in active_allocations:
                if (
                    allocation.classroom_id == classroom.id
                    and allocation.day_of_week == entry.day_of_week
                    and overlaps(entry.start_time, entry.end_time, allocation.start_time, allocation.end_time)
                ):
                    warnings.append(f"Classroom {classroom.room_number} overlaps an active manual allocation.")
        return list(dict.fromkeys(warnings))

    @staticmethod
    def _activity_identity(value: str | None) -> str:
        text = re.sub(r"\bsem\s+ill\b", "sem iii", (value or "").casefold())
        return " ".join(re.sub(r"[^a-z0-9]+", " ", text).split())

    @staticmethod
    def _append_warning(current: str | None, warning: str) -> str:
        return "; ".join(value for value in (current, warning) if value)

    @staticmethod
    def _preview_entry(entry: NormalizedTimetableEntry) -> dict:
        return {
            "class": entry.class_name,
            "department": entry.department_name,
            "division": entry.division,
            "day": entry.day_of_week,
            "start_time": entry.start_time_text,
            "end_time": entry.end_time_text,
            "subject": entry.subject_text,
            "room": entry.room_hint,
            "subject_type": entry.subject_type,
            "session_type": entry.session_type,
            "delivery_mode": entry.delivery_mode,
            "confidence": entry.confidence_level.value,
        }

    def _get_or_create_time_slot(self, db: Session, start_time, end_time) -> TimeSlot:
        time_slot = db.execute(
            select(TimeSlot).where(TimeSlot.start_time == start_time, TimeSlot.end_time == end_time)
        ).scalar_one_or_none()
        if time_slot:
            return time_slot
        time_slot = TimeSlot(start_time=start_time, end_time=end_time)
        db.add(time_slot)
        db.flush()
        return time_slot

    @staticmethod
    def _detected_time_slots(parsed_document: ParsedDocument) -> list[tuple]:
        values: list[str] = []
        values.extend(parsed_document.metadata.get("time_slot_order") or [])
        for cell in parsed_document.cells:
            values.extend(cell.metadata.get("time_slot_order") or [])
            if cell.start_time_text and cell.end_time_text:
                values.append(f"{cell.start_time_text}-{cell.end_time_text}")

        slots: list[tuple] = []
        for value in dict.fromkeys(values):
            match = re.fullmatch(r"\s*(\d{1,2}[.:]\d{2})\s*-\s*(\d{1,2}[.:]\d{2})\s*", value)
            if not match:
                continue
            start_time = parse_time_value(match.group(1))
            end_time = parse_time_value(match.group(2))
            if start_time and end_time and end_time > start_time and (start_time, end_time) not in slots:
                slots.append((start_time, end_time))
        return slots

    def _supersede_previous_file_versions(self, db: Session, file_import: FileImport) -> None:
        previous = db.execute(
            select(Timetable)
            .join(FileImport, Timetable.source_import_id == FileImport.id)
            .where(
                FileImport.original_filename == file_import.original_filename,
                Timetable.source_import_id != file_import.id,
                Timetable.status == "ACTIVE",
            )
        ).scalars().all()
        for timetable in previous:
            timetable.status = "SUPERSEDED"

    def _get_or_create_timetable(
        self, db: Session, review: ImportReview, department: Department | None
    ) -> Timetable:
        timetable = db.execute(
            select(Timetable).where(
                Timetable.academic_year == review.academic_year,
                Timetable.class_name == review.class_name,
                Timetable.division == review.division,
                Timetable.semester == review.semester,
                Timetable.department_id == (department.id if department else None),
                Timetable.program_name == review.program_name,
                Timetable.source_import_id == review.file_import_id,
            )
        ).scalar_one_or_none()
        if timetable:
            self._merge_timetable_metadata(timetable, review)
            return timetable

        existing_versions = db.execute(
            select(Timetable).where(
                Timetable.academic_year == review.academic_year,
                Timetable.class_name == review.class_name,
                Timetable.division == review.division,
                Timetable.semester == review.semester,
                Timetable.department_id == (department.id if department else None),
                Timetable.program_name == review.program_name,
                Timetable.status == "ACTIVE",
                Timetable.source_import_id != review.file_import_id,
            )
        ).scalars().all()
        for existing_version in existing_versions:
            existing_version.status = "SUPERSEDED"

        timetable = Timetable(
            college_name=review.college_name,
            academic_year=review.academic_year,
            class_name=review.class_name or "UNKNOWN",
            division=review.division,
            semester=review.semester,
            department_id=department.id if department else None,
            program_name=review.program_name,
            metadata_json=self._timetable_metadata(review),
            source_import_id=review.file_import_id,
        )
        db.add(timetable)
        db.flush()
        return timetable

    @staticmethod
    def _timetable_metadata(review: ImportReview) -> dict:
        source = (review.normalized_json or {}).get("source_metadata", {})
        return {
            key: value
            for key, value in source.items()
            if key in {"column_order", "time_slot_order", "attributes", "layout", "hall_name"}
            and value not in (None, {}, [])
        }

    def _merge_timetable_metadata(self, timetable: Timetable, review: ImportReview) -> None:
        current = dict(timetable.metadata_json or {})
        incoming = self._timetable_metadata(review)
        for key in ("column_order", "time_slot_order"):
            current[key] = list(dict.fromkeys([*(current.get(key) or []), *(incoming.get(key) or [])]))
        current["attributes"] = {
            **(current.get("attributes") or {}),
            **(incoming.get("attributes") or {}),
        }
        for key in ("layout", "hall_name"):
            if incoming.get(key) is not None:
                current[key] = incoming[key]
        timetable.metadata_json = current

    def _get_or_create_department(self, db: Session, name: str | None) -> Department | None:
        if not name:
            return None
        department = db.execute(
            select(Department).where(func.lower(Department.name) == name.lower())
        ).scalar_one_or_none()
        if department:
            return department
        department = Department(name=name, description="Created from timetable import")
        db.add(department)
        db.flush()
        return department

    def _get_or_create_subject(
        self, db: Session, subject_text: str | None, department: Department | None
    ) -> Subject | None:
        if not subject_text:
            return None
        candidates = db.execute(
            select(Subject).where(Subject.department_id == (department.id if department else None))
        ).scalars().all()
        matches = [subject for subject in candidates if self._master_text_key(subject.name) == self._master_text_key(subject_text)]
        if len(matches) == 1:
            return matches[0]
        subject = Subject(name=subject_text, department_id=department.id if department else None)
        db.add(subject)
        db.flush()
        return subject

    @staticmethod
    def _master_text_key(value: str) -> str:
        return "".join(character.casefold() for character in normalize_space(value) if character.isalnum())

    def _resolve_subject_department(
        self, db: Session, subject_text: str | None, timetable_department: Department | None
    ) -> Department | None:
        if not subject_text:
            return timetable_department
        normalized_subject = " ".join(
            part for part in "".join(character.lower() if character.isalnum() else " " for character in subject_text).split()
        )
        departments = db.execute(select(Department)).scalars().all()
        matches: list[Department] = []
        for department in departments:
            normalized_name = " ".join(
                part for part in "".join(
                    character.lower() if character.isalnum() else " " for character in department.name
                ).split()
            )
            if normalized_name and f" {normalized_name} " in f" {normalized_subject} ":
                matches.append(department)
        if matches:
            return max(matches, key=lambda item: len(item.name))
        return timetable_department

    def _canonical_subject_name(self, subject_text: str | None, department: Department | None) -> str | None:
        if not subject_text:
            return None
        if department:
            normalized_subject = " ".join(
                "".join(character.lower() if character.isalnum() else " " for character in subject_text).split()
            )
            normalized_department = " ".join(
                "".join(character.lower() if character.isalnum() else " " for character in department.name).split()
            )
            if f" {normalized_department} " in f" {normalized_subject} ":
                return department.name
        return subject_text

    def _get_or_create_faculty(
        self, db: Session, faculty_text: str | None, department: Department | None
    ) -> Faculty | None:
        if not faculty_text:
            return None
        query = select(Faculty).where(func.lower(Faculty.name) == faculty_text.lower())
        if department:
            query = query.where(Faculty.department_id == department.id)
        else:
            query = query.where(Faculty.department_id.is_(None))
        faculty = db.execute(query).scalar_one_or_none()
        if faculty:
            return faculty
        faculty = Faculty(
            name=faculty_text,
            department_id=department.id if department else None,
            status="ACTIVE",
        )
        db.add(faculty)
        db.flush()
        return faculty
