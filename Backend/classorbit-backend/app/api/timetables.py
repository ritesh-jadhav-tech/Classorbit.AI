from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.api.master_data import commit_or_400, get_or_404
from app.core.config import get_settings
from app.db.session import get_db
from app.models.enums import AllocationType, RoleName
from app.models.timetable import ClassroomAllocation, Timetable, TimetableEntry, TimeSlot
from app.models.user import User
from app.schemas.timetable import (
    TimeSlotCreate,
    TimeSlotRead,
    TimetableCreate,
    TimetableEntryCreate,
    TimetableEntryRead,
    TimetableEntryUpdate,
    TimetableRead,
    TimetableStructureRead,
    TimetableUpdate,
)
from app.services.timetable_entry_service import delete_timetable_entry, TimetableEntryEditError, update_timetable_entry


router = APIRouter(tags=["timetables"])


@router.get("/timetables/template/download")
def download_timetable_template(
    _: User = Depends(require_roles(RoleName.ADMIN)),
) -> FileResponse:
    template_path = get_settings().project_root / "assets" / "ClassOrbit_Timetable_Template.xlsx"
    if not template_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Timetable template is unavailable.")
    return FileResponse(
        template_path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename="ClassOrbit_Timetable_Template.xlsx",
    )


@router.get("/timetables", response_model=list[TimetableRead])
def list_timetables(db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> list[Timetable]:
    return db.query(Timetable).order_by(Timetable.created_at.desc()).all()


@router.get("/timetable-structures", response_model=list[TimetableStructureRead])
def list_timetable_structures(
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[dict]:
    query = db.query(Timetable).order_by(Timetable.created_at.desc())
    if not include_inactive:
        query = query.filter(Timetable.status == "ACTIVE")

    structures: list[dict] = []
    global_slots = db.query(TimeSlot).all()
    slots_by_range = {
        f"{slot.start_time.strftime('%H:%M')}-{slot.end_time.strftime('%H:%M')}": slot
        for slot in global_slots
    }
    for timetable in query.all():
        entries = sorted(
            timetable.entries,
            key=lambda entry: (
                entry.source_page or 0,
                entry.source_row or 0,
                entry.day_of_week,
                entry.time_slot.start_time,
            ),
        )
        metadata = timetable.metadata_json or {}
        columns = list(metadata.get("column_order") or [])
        for entry in entries:
            if entry.day_of_week not in columns:
                columns.append(entry.day_of_week)

        slots_by_id = {entry.time_slot_id: entry.time_slot for entry in entries}
        for value in metadata.get("time_slot_order") or []:
            slot = slots_by_range.get(value)
            if slot:
                slots_by_id[slot.id] = slot
        slot_order = {
            value: index for index, value in enumerate(metadata.get("time_slot_order") or [])
        }
        time_slots = sorted(
            slots_by_id.values(),
            key=lambda slot: (
                slot_order.get(
                    f"{slot.start_time.strftime('%H:%M')}-{slot.end_time.strftime('%H:%M')}",
                    len(slot_order),
                ),
                slot.start_time,
                slot.end_time,
            ),
        )
        attribute_keys = sorted(
            {
                key
                for entry in entries
                for key in (entry.attributes_json or {})
            }
        )
        structures.append(
            {
                "timetable": timetable,
                "columns": columns,
                "time_slots": time_slots,
                "entries": entries,
                "attribute_keys": attribute_keys,
            }
        )
    return structures


@router.post("/timetables", response_model=TimetableRead, status_code=status.HTTP_201_CREATED)
def create_timetable(
    payload: TimetableCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(RoleName.ADMIN)),
) -> Timetable:
    timetable = Timetable(**payload.model_dump())
    db.add(timetable)
    commit_or_400(db)
    db.refresh(timetable)
    return timetable


@router.get("/timetables/{timetable_id}", response_model=TimetableRead)
def get_timetable(
    timetable_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> Timetable:
    return get_or_404(db, Timetable, timetable_id, "Timetable")


@router.patch("/timetables/{timetable_id}", response_model=TimetableRead)
def update_timetable(
    timetable_id: str,
    payload: TimetableUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(RoleName.ADMIN)),
) -> Timetable:
    timetable = get_or_404(db, Timetable, timetable_id, "Timetable")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(timetable, field, value)
    commit_or_400(db)
    db.refresh(timetable)
    return timetable


@router.get("/timetable-entries", response_model=list[TimetableEntryRead])
def list_timetable_entries(
    timetable_id: str | None = None,
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[TimetableEntry]:
    query = db.query(TimetableEntry).join(Timetable)
    if not include_inactive:
        query = query.filter(Timetable.status == "ACTIVE")
    if timetable_id:
        query = query.filter(TimetableEntry.timetable_id == timetable_id)
    return query.join(TimeSlot).order_by(TimetableEntry.day_of_week, TimeSlot.start_time).all()


@router.post("/timetable-entries", response_model=TimetableEntryRead, status_code=status.HTTP_201_CREATED)
def create_timetable_entry(
    payload: TimetableEntryCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(RoleName.ADMIN)),
) -> TimetableEntry:
    timetable = db.get(Timetable, payload.timetable_id)
    if not timetable:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Timetable not found.")
    if not db.get(TimeSlot, payload.time_slot_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Time slot not found.")
    entry = TimetableEntry(**payload.model_dump())
    db.add(entry)
    db.flush()
    if entry.classroom_id:
        db.add(
            ClassroomAllocation(
                classroom_id=entry.classroom_id,
                timetable_entry_id=entry.id,
                allocation_type=AllocationType.MANUAL,
                title=entry.subject_text,
                day_of_week=entry.day_of_week,
                start_time=entry.time_slot.start_time,
                end_time=entry.time_slot.end_time,
                class_name=timetable.class_name,
                division=timetable.division,
                faculty_text=entry.faculty_text,
            )
        )
    commit_or_400(db)
    db.refresh(entry)
    return entry


@router.patch("/timetable-entries/{entry_id}", response_model=TimetableEntryRead)
def edit_timetable_entry(
    entry_id: str,
    payload: TimetableEntryUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_roles(RoleName.ADMIN)),
) -> TimetableEntry:
    entry = get_or_404(db, TimetableEntry, entry_id, "Timetable entry")
    try:
        return update_timetable_entry(db, entry, payload, current_admin)
    except TimetableEntryEditError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.delete("/timetable-entries/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_timetable_entry(
    entry_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(RoleName.ADMIN)),
) -> None:
    entry = get_or_404(db, TimetableEntry, entry_id, "Timetable entry")
    delete_timetable_entry(db, entry)


@router.get("/time-slots", response_model=list[TimeSlotRead])
def list_time_slots(db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> list[TimeSlot]:
    return db.query(TimeSlot).order_by(TimeSlot.start_time, TimeSlot.end_time).all()


@router.post("/time-slots", response_model=TimeSlotRead, status_code=status.HTTP_201_CREATED)
def create_time_slot(
    payload: TimeSlotCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(RoleName.ADMIN)),
) -> TimeSlot:
    if payload.end_time <= payload.start_time:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="end_time must be after start_time.")
    existing = db.query(TimeSlot).filter(
        TimeSlot.start_time == payload.start_time,
        TimeSlot.end_time == payload.end_time,
    ).one_or_none()
    if existing:
        return existing
    time_slot = TimeSlot(**payload.model_dump())
    db.add(time_slot)
    commit_or_400(db)
    db.refresh(time_slot)
    return time_slot
