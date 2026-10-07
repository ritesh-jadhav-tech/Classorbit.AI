from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from app.models.import_record import FileImport, ImportReview
from app.models.master_data import Building, Classroom, Department, Faculty, Floor, RoomType, Subject
from app.models.timetable import ClassroomAllocation, Timetable, TimetableEntry, TimeSlot
from app.models.user import User


RESET_MODELS = (
    ImportReview,
    ClassroomAllocation,
    TimetableEntry,
    Timetable,
    FileImport,
    TimeSlot,
    Subject,
    Faculty,
    Classroom,
    Floor,
    RoomType,
    Building,
    Department,
)


def reset_test_data(db: Session) -> tuple[dict[str, int], int]:
    # Users are retained, so remove their links to departments before master data is cleared.
    db.execute(update(User).values(department_id=None).execution_options(synchronize_session=False))

    deleted_counts: dict[str, int] = {}
    for model in RESET_MODELS:
        result = db.execute(delete(model).execution_options(synchronize_session=False))
        deleted_counts[model.__tablename__] = result.rowcount or 0

    preserved_users = db.scalar(select(func.count()).select_from(User)) or 0
    db.commit()
    return deleted_counts, preserved_users

