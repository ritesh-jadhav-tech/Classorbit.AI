from datetime import datetime, timezone

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.enums import AllocationType, ConfidenceLevel, MappingStatus, ReviewAction, ValidationStatus
from app.models.master_data import Classroom, Subject
from app.models.import_record import ImportReview
from app.models.timetable import ClassroomAllocation, TimetableEntry, TimeSlot
from app.models.user import User
from app.schemas.timetable import TimetableEntryUpdate
from app.utils.text_normalization import normalize_room_hint, normalize_space


class TimetableEntryEditError(ValueError):
    pass


def update_timetable_entry(
    db: Session,
    entry: TimetableEntry,
    payload: TimetableEntryUpdate,
    editor: User,
) -> TimetableEntry:
    updates = payload.model_dump(exclude_unset=True)
    time_slot = entry.time_slot
    if time_slot_id := updates.pop("time_slot_id", None):
        time_slot = db.get(TimeSlot, time_slot_id)
        if not time_slot:
            raise TimetableEntryEditError("Time slot not found.")
        entry.time_slot_id = time_slot.id

    if "subject_text" in updates:
        subject_text = normalize_space(updates.pop("subject_text"))
        if not subject_text:
            raise TimetableEntryEditError("Subject is required.")
        entry.subject_text = subject_text
        subject = db.execute(
            select(Subject).where(
                func.lower(Subject.name) == subject_text.lower(),
                Subject.department_id == entry.timetable.department_id,
            )
        ).scalar_one_or_none()
        if not subject:
            subject = Subject(name=subject_text, department_id=entry.timetable.department_id)
            db.add(subject)
            db.flush()
        entry.subject_id = subject.id

    if "room_hint" in updates:
        room_hint = normalize_room_hint(updates.pop("room_hint"))
        entry.room_hint = room_hint
        classroom = None
        if room_hint:
            classroom = db.execute(
                select(Classroom).where(
                    or_(
                        func.lower(Classroom.room_number) == room_hint.lower(),
                        func.lower(Classroom.display_name) == room_hint.lower(),
                    )
                )
            ).scalar_one_or_none()
        entry.classroom_id = classroom.id if classroom else None
        entry.mapping_status = MappingStatus.MATCHED if classroom else MappingStatus.UNMATCHED if room_hint else MappingStatus.NONE

    for field, value in updates.items():
        setattr(entry, field, normalize_space(value) or None if isinstance(value, str) else value)

    entry.validation_status = ValidationStatus.VALID
    entry.confidence_level = ConfidenceLevel.HIGH
    entry.confidence_score = 1.0
    entry.extraction_method = "MANUAL_EDIT"
    trace = dict(entry.trace_json or {})
    trace["manual_edits"] = [
        *(trace.get("manual_edits") or []),
        {
            "edited_at": datetime.now(timezone.utc).isoformat(),
            "edited_by_user_id": editor.id,
            "fields": sorted(payload.model_dump(exclude_unset=True)),
        },
    ]
    entry.trace_json = trace
    db.flush()

    allocations = db.execute(
        select(ClassroomAllocation).where(ClassroomAllocation.timetable_entry_id == entry.id)
    ).scalars().all()
    if entry.classroom_id:
        allocation = allocations[0] if allocations else ClassroomAllocation(
            classroom_id=entry.classroom_id,
            timetable_entry_id=entry.id,
            allocation_type=AllocationType.TIMETABLE,
            title=entry.subject_text,
            start_time=time_slot.start_time,
            end_time=time_slot.end_time,
        )
        if not allocations:
            db.add(allocation)
        allocation.classroom_id = entry.classroom_id
        allocation.title = entry.subject_text
        allocation.day_of_week = entry.day_of_week
        allocation.start_time = time_slot.start_time
        allocation.end_time = time_slot.end_time
        allocation.class_name = entry.timetable.class_name
        allocation.division = entry.timetable.division
        allocation.faculty_text = entry.faculty_text
        for duplicate in allocations[1:]:
            db.delete(duplicate)
    else:
        for allocation in allocations:
            db.delete(allocation)

    db.commit()
    db.refresh(entry)
    return entry


def delete_timetable_entry(db: Session, entry: TimetableEntry) -> None:
    for review in db.execute(
        select(ImportReview).where(ImportReview.timetable_entry_id == entry.id)
    ).scalars():
        review.timetable_entry_id = None
        review.action = ReviewAction.IGNORED
        review.warning = "; ".join(
            value for value in (review.warning, "Removed by an admin as no activity / extraction noise.") if value
        )
    for allocation in db.execute(
        select(ClassroomAllocation).where(ClassroomAllocation.timetable_entry_id == entry.id)
    ).scalars():
        db.delete(allocation)
    db.delete(entry)
    db.commit()
