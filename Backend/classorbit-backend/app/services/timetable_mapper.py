import re

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.enums import LocationType, MappingStatus
from app.models.master_data import Classroom, Department, RoomType
from app.services.timetable_normalizer import NormalizedTimetableEntry


class TimetableMapper:
    def map_classroom(
        self, db: Session, entry: NormalizedTimetableEntry, *, create_missing: bool = True
    ) -> tuple[NormalizedTimetableEntry, Classroom | None]:
        if not entry.room_hint:
            if entry.mapping_status != MappingStatus.AMBIGUOUS:
                entry.mapping_status = MappingStatus.NONE
            return entry, None
        if entry.location_type in {LocationType.ONLINE, LocationType.DEPARTMENT}:
            entry.mapping_status = MappingStatus.NONE
            return entry, None

        room_key = self._room_key(entry.room_hint)
        classrooms = db.execute(select(Classroom)).scalars().all()
        matches = [
            classroom
            for classroom in classrooms
            if room_key in {
                self._room_key(classroom.room_number),
                self._room_key(classroom.display_name),
            }
        ]
        if len(matches) == 1:
            entry.mapping_status = MappingStatus.MATCHED
            entry.normalized_json["classroom_mapping"] = {
                "action": "matched",
                "classroom_id": matches[0].id,
                "room_number": matches[0].room_number,
            }
            return entry, matches[0]
        if len(matches) > 1:
            entry.mapping_status = MappingStatus.AMBIGUOUS
            entry.normalized_json["classroom_mapping"] = {
                "action": "ambiguous",
                "candidate_ids": [classroom.id for classroom in matches],
            }
            return entry, None

        if not create_missing:
            entry.mapping_status = MappingStatus.UNMATCHED
            return entry, None

        department = None
        room_department_name = entry.attributes_json.get("location_department") or entry.department_name
        if room_department_name:
            department = db.execute(
                select(Department).where(func.lower(Department.name) == room_department_name.lower())
            ).scalar_one_or_none()
            if department is None:
                department = Department(
                    name=room_department_name,
                    description="Created from timetable import",
                )
                db.add(department)
                db.flush()
        room_type_name = "Laboratory" if entry.location_type == LocationType.LAB else "Classroom"
        room_type = db.execute(
            select(RoomType).where(func.lower(RoomType.name) == room_type_name.lower())
        ).scalar_one_or_none()
        if room_type is None:
            room_type = RoomType(name=room_type_name, description="Created from timetable import")
            db.add(room_type)
            db.flush()

        classroom = Classroom(
            room_number=entry.room_hint,
            display_name=(
                entry.room_hint.title()
                if entry.location_type == LocationType.LAB and entry.attributes_json.get("location_department")
                else f"Laboratory {entry.room_hint}"
                if entry.location_type == LocationType.LAB
                else f"Classroom {entry.room_hint}"
            ),
            room_type_id=room_type.id,
            department_id=department.id if department else None,
            facilities=[],
            status="ACTIVE",
        )
        db.add(classroom)
        db.flush()
        entry.mapping_status = MappingStatus.MATCHED
        entry.normalized_json["classroom_mapping"] = {
            "action": "created",
            "classroom_id": classroom.id,
            "room_number": classroom.room_number,
        }
        return entry, classroom

    @staticmethod
    def _room_key(value: str | None) -> str:
        normalized = re.sub(r"[^a-z0-9]", "", (value or "").casefold())
        return re.sub(r"^room(?=\d)", "", normalized)
