from typing import TypeVar

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.enums import RoleName
from app.models.master_data import Building, Classroom, Department, Faculty, Floor, RoomType, Subject
from app.models.timetable import TimetableEntry
from app.models.user import User
from app.schemas.master_data import (
    BuildingCreate,
    BuildingRead,
    BuildingUpdate,
    ClassroomCreate,
    ClassroomRead,
    ClassroomUpdate,
    DepartmentCreate,
    DepartmentRead,
    DepartmentUpdate,
    FacultyCreate,
    FacultyRead,
    FacultyUpdate,
    FloorCreate,
    FloorRead,
    FloorUpdate,
    RoomTypeCreate,
    RoomTypeRead,
    RoomTypeUpdate,
    SubjectCreate,
    SubjectRead,
    SubjectUpdate,
)


router = APIRouter(tags=["master-data"])
ModelT = TypeVar("ModelT")


def commit_or_400(db: Session, message: str = "Record violates a database constraint.") -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message) from exc


def get_or_404(db: Session, model: type[ModelT], record_id: str, name: str) -> ModelT:
    record = db.get(model, record_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{name} not found.")
    return record


def apply_updates(record: object, payload) -> object:
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(record, field, value)
    return record


@router.get("/departments", response_model=list[DepartmentRead])
def list_departments(db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> list[Department]:
    return db.query(Department).order_by(Department.name).all()


@router.post("/departments", response_model=DepartmentRead, status_code=status.HTTP_201_CREATED)
def create_department(
    payload: DepartmentCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(RoleName.ADMIN)),
) -> Department:
    record = Department(**payload.model_dump())
    db.add(record)
    commit_or_400(db)
    db.refresh(record)
    return record


@router.patch("/departments/{department_id}", response_model=DepartmentRead)
def update_department(
    department_id: str,
    payload: DepartmentUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(RoleName.ADMIN)),
) -> Department:
    record = get_or_404(db, Department, department_id, "Department")
    apply_updates(record, payload)
    commit_or_400(db)
    db.refresh(record)
    return record


@router.get("/faculty", response_model=list[FacultyRead])
def list_faculty(db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> list[Faculty]:
    return db.query(Faculty).order_by(Faculty.name).all()


@router.post("/faculty", response_model=FacultyRead, status_code=status.HTTP_201_CREATED)
def create_faculty(
    payload: FacultyCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(RoleName.ADMIN)),
) -> Faculty:
    record = Faculty(**payload.model_dump())
    db.add(record)
    commit_or_400(db)
    db.refresh(record)
    return record


@router.patch("/faculty/{faculty_id}", response_model=FacultyRead)
def update_faculty(
    faculty_id: str,
    payload: FacultyUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(RoleName.ADMIN)),
) -> Faculty:
    record = get_or_404(db, Faculty, faculty_id, "Faculty")
    previous_name = record.name
    apply_updates(record, payload)
    if record.name != previous_name:
        for entry in db.query(TimetableEntry).filter(TimetableEntry.faculty_id == record.id).all():
            if entry.faculty_text == previous_name:
                entry.faculty_text = record.name
    commit_or_400(db)
    db.refresh(record)
    return record


@router.delete("/faculty/{faculty_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_faculty(
    faculty_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(RoleName.ADMIN)),
) -> Response:
    record = get_or_404(db, Faculty, faculty_id, "Faculty")
    db.query(TimetableEntry).filter(TimetableEntry.faculty_id == record.id).update(
        {TimetableEntry.faculty_id: None}, synchronize_session=False
    )
    db.delete(record)
    commit_or_400(db)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/subjects", response_model=list[SubjectRead])
def list_subjects(db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> list[Subject]:
    return db.query(Subject).order_by(Subject.name).all()


@router.post("/subjects", response_model=SubjectRead, status_code=status.HTTP_201_CREATED)
def create_subject(
    payload: SubjectCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(RoleName.ADMIN)),
) -> Subject:
    record = Subject(**payload.model_dump())
    db.add(record)
    commit_or_400(db)
    db.refresh(record)
    return record


@router.patch("/subjects/{subject_id}", response_model=SubjectRead)
def update_subject(
    subject_id: str,
    payload: SubjectUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(RoleName.ADMIN)),
) -> Subject:
    record = get_or_404(db, Subject, subject_id, "Subject")
    previous_name = record.name
    apply_updates(record, payload)
    if record.name != previous_name:
        for entry in db.query(TimetableEntry).filter(TimetableEntry.subject_id == record.id).all():
            if entry.subject_text != previous_name:
                continue
            entry.subject_text = record.name
            for allocation in entry.allocations:
                allocation.title = record.name
    commit_or_400(db)
    db.refresh(record)
    return record


@router.delete("/subjects/{subject_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_subject(
    subject_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(RoleName.ADMIN)),
) -> Response:
    record = get_or_404(db, Subject, subject_id, "Subject")
    db.query(TimetableEntry).filter(TimetableEntry.subject_id == record.id).update(
        {TimetableEntry.subject_id: None}, synchronize_session=False
    )
    db.delete(record)
    commit_or_400(db)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/buildings", response_model=list[BuildingRead])
def list_buildings(db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> list[Building]:
    return db.query(Building).order_by(Building.name).all()


@router.post("/buildings", response_model=BuildingRead, status_code=status.HTTP_201_CREATED)
def create_building(
    payload: BuildingCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(RoleName.ADMIN)),
) -> Building:
    record = Building(**payload.model_dump())
    db.add(record)
    commit_or_400(db)
    db.refresh(record)
    return record


@router.patch("/buildings/{building_id}", response_model=BuildingRead)
def update_building(
    building_id: str,
    payload: BuildingUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(RoleName.ADMIN)),
) -> Building:
    record = get_or_404(db, Building, building_id, "Building")
    apply_updates(record, payload)
    commit_or_400(db)
    db.refresh(record)
    return record


@router.get("/floors", response_model=list[FloorRead])
def list_floors(db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> list[Floor]:
    return db.query(Floor).order_by(Floor.level).all()


@router.post("/floors", response_model=FloorRead, status_code=status.HTTP_201_CREATED)
def create_floor(
    payload: FloorCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(RoleName.ADMIN)),
) -> Floor:
    record = Floor(**payload.model_dump())
    db.add(record)
    commit_or_400(db)
    db.refresh(record)
    return record


@router.patch("/floors/{floor_id}", response_model=FloorRead)
def update_floor(
    floor_id: str,
    payload: FloorUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(RoleName.ADMIN)),
) -> Floor:
    record = get_or_404(db, Floor, floor_id, "Floor")
    apply_updates(record, payload)
    commit_or_400(db)
    db.refresh(record)
    return record


@router.get("/room-types", response_model=list[RoomTypeRead])
def list_room_types(db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> list[RoomType]:
    return db.query(RoomType).order_by(RoomType.name).all()


@router.post("/room-types", response_model=RoomTypeRead, status_code=status.HTTP_201_CREATED)
def create_room_type(
    payload: RoomTypeCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(RoleName.ADMIN)),
) -> RoomType:
    record = RoomType(**payload.model_dump())
    db.add(record)
    commit_or_400(db)
    db.refresh(record)
    return record


@router.patch("/room-types/{room_type_id}", response_model=RoomTypeRead)
def update_room_type(
    room_type_id: str,
    payload: RoomTypeUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(RoleName.ADMIN)),
) -> RoomType:
    record = get_or_404(db, RoomType, room_type_id, "Room type")
    apply_updates(record, payload)
    commit_or_400(db)
    db.refresh(record)
    return record


@router.get("/classrooms", response_model=list[ClassroomRead])
def list_classrooms(db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> list[Classroom]:
    return db.query(Classroom).order_by(Classroom.room_number).all()


@router.post("/classrooms", response_model=ClassroomRead, status_code=status.HTTP_201_CREATED)
def create_classroom(
    payload: ClassroomCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(RoleName.ADMIN)),
) -> Classroom:
    record = Classroom(**payload.model_dump())
    db.add(record)
    commit_or_400(db)
    db.refresh(record)
    return record


@router.patch("/classrooms/{classroom_id}", response_model=ClassroomRead)
def update_classroom(
    classroom_id: str,
    payload: ClassroomUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(RoleName.ADMIN)),
) -> Classroom:
    record = get_or_404(db, Classroom, classroom_id, "Classroom")
    apply_updates(record, payload)
    commit_or_400(db)
    db.refresh(record)
    return record
