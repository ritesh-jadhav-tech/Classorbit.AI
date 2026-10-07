from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.schedule import AvailabilityResult, ScheduleResult
from app.services.schedule_service import ScheduleService


router = APIRouter(tags=["schedule"])
service = ScheduleService()


@router.get("/schedule/by-room", response_model=list[ScheduleResult])
def schedule_by_room(
    room: str,
    day: str | None = None,
    date: str | None = None,
    time: str | None = None,
    start_time: str | None = None,
    end_time: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[ScheduleResult]:
    return service.scheduled_for_room(
        db,
        room=room,
        day=day,
        on_date=date,
        at_time=time,
        start_time=start_time,
        end_time=end_time,
    )


@router.get("/schedule/by-class", response_model=list[ScheduleResult])
def schedule_by_class(
    class_name: str,
    division: str | None = None,
    day: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[ScheduleResult]:
    return service.scheduled_for_class(db, class_name=class_name, division=division, day=day)


@router.get("/availability", response_model=AvailabilityResult)
def availability(
    room: str,
    day: str | None = None,
    date: str | None = None,
    start_time: str | None = None,
    end_time: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> AvailabilityResult:
    return service.availability(db, room=room, day=day, on_date=date, start_time=start_time, end_time=end_time)
