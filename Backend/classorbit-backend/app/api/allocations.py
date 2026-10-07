from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.api.master_data import commit_or_400
from app.db.session import get_db
from app.models.enums import RoleName
from app.models.master_data import Classroom
from app.models.timetable import ClassroomAllocation
from app.models.user import User
from app.schemas.timetable import ClassroomAllocationCreate, ClassroomAllocationRead


router = APIRouter(prefix="/allocations", tags=["allocations"])


@router.get("", response_model=list[ClassroomAllocationRead])
def list_allocations(db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> list[ClassroomAllocation]:
    return db.query(ClassroomAllocation).order_by(ClassroomAllocation.created_at.desc()).all()


@router.post("", response_model=ClassroomAllocationRead, status_code=status.HTTP_201_CREATED)
def create_allocation(
    payload: ClassroomAllocationCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(RoleName.ADMIN)),
) -> ClassroomAllocation:
    if not db.get(Classroom, payload.classroom_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Classroom not found.")
    if payload.end_time <= payload.start_time:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="end_time must be after start_time.")
    allocation = ClassroomAllocation(**payload.model_dump())
    db.add(allocation)
    commit_or_400(db)
    db.refresh(allocation)
    return allocation
