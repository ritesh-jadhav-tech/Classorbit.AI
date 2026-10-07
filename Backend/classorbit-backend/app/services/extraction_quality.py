from collections import Counter

from app.models.enums import ValidationStatus
from app.parsers.base import ParsedDocument
from app.services.timetable_confidence import TimetableConfidenceScorer
from app.services.timetable_normalizer import TimetableNormalizer
from app.services.timetable_validator import TimetableValidator


class ExtractionQualityAnalyzer:
    def __init__(self) -> None:
        self.normalizer = TimetableNormalizer()
        self.validator = TimetableValidator()
        self.confidence = TimetableConfidenceScorer()

    def analyze(self, document: ParsedDocument, *, preview_limit: int = 20) -> dict:
        validation = Counter()
        confidence = Counter()
        warnings: set[str] = set(document.warnings)
        semantic_keys: set[tuple] = set()
        duplicates = 0
        entries = []
        classes: set[str] = set()
        departments: set[str] = set()
        divisions: set[str] = set()
        rooms: set[str] = set()
        subject_types: set[str] = set()
        attribute_keys: set[str] = set()
        contexts: set[tuple] = set()
        unknown_items: set[tuple[str, str]] = set()
        for cell in document.cells:
            source_attributes = cell.metadata.get("attributes") or {}
            attribute_keys.update(source_attributes)
            unknown_items.update(
                (key, str(value))
                for key, value in source_attributes.items()
                if key.startswith("source_")
            )

        for cell in document.cells:
            for entry in self.normalizer.normalize_cell(cell, document.metadata):
                entry = self.validator.validate(entry)
                entry = self.confidence.score(entry)
                validation[entry.validation_status.value] += 1
                confidence[entry.confidence_level.value] += 1
                if entry.warning:
                    warnings.add(entry.warning)
                if entry.class_name:
                    classes.add(entry.class_name)
                if entry.department_name:
                    departments.add(entry.department_name)
                if entry.division:
                    divisions.add(entry.division)
                if entry.room_hint:
                    rooms.add(entry.room_hint)
                if entry.subject_type:
                    subject_types.add(entry.subject_type)
                attribute_keys.update(entry.attributes_json)
                contexts.add((entry.class_name, entry.department_name, entry.division, entry.program_name))
                key = (
                    entry.academic_year,
                    entry.class_name,
                    entry.department_name,
                    entry.division,
                    entry.day_of_week,
                    entry.start_time,
                    entry.end_time,
                    (entry.subject_text or "").casefold(),
                    (entry.room_hint or "").casefold(),
                )
                if key in semantic_keys:
                    duplicates += 1
                semantic_keys.add(key)
                if len(entries) < preview_limit:
                    entries.append(
                        {
                            "page": entry.source_page,
                            "class": entry.class_name,
                            "department": entry.department_name,
                            "division": entry.division,
                            "day": entry.day_of_week,
                            "start": entry.start_time_text,
                            "end": entry.end_time_text,
                            "subject": entry.subject_text,
                            "room": entry.room_hint,
                            "subject_type": entry.subject_type,
                            "session_type": entry.session_type,
                            "delivery_mode": entry.delivery_mode,
                            "confidence": entry.confidence_level.value,
                            "validation": entry.validation_status.value,
                        }
                    )

        generated = sum(validation.values())
        return {
            "pdf_name": document.source_path.name,
            "pages_processed": document.page_count or 0,
            "pages_successfully_extracted": document.pages_extracted,
            "timetable_cells_detected": len(document.cells),
            "timetable_entries_generated": generated,
            "high_confidence": confidence["HIGH"],
            "medium_confidence": confidence["MEDIUM"],
            "low_confidence": confidence["LOW"],
            "valid": validation[ValidationStatus.VALID.value],
            "needs_review": validation[ValidationStatus.NEEDS_REVIEW.value],
            "validation_failures": validation[ValidationStatus.INVALID.value],
            "possible_duplicates": duplicates,
            "unparsed_cells": sum(1 for cell in document.cells if not cell.raw_cell_text.strip()),
            "ocr_fallback_used": bool(document.ocr_pages),
            "ocr_pages": document.ocr_pages,
            "template_detected": document.template_name,
            "parser": document.parser_name,
            "parser_strategy_used": document.template_name,
            "detected_timetable_structures": len(contexts),
            "recognized_entities": {
                "classes": sorted(classes),
                "departments": sorted(departments),
                "divisions": sorted(divisions),
                "rooms": sorted(rooms),
                "subject_types": sorted(subject_types),
                "dynamic_attributes": sorted(attribute_keys),
            },
            "unknown_unclassified_content": len(unknown_items),
            "warnings": sorted(warnings),
            "preview": entries,
        }
