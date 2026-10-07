from datetime import date, time, timedelta, datetime

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, joinedload

from app.models.enums import ScheduledStatus, TimetableEntryStatus
from app.models.master_data import Classroom
from app.models.timetable import ClassroomAllocation, Timetable, TimetableEntry, TimeSlot
from app.schemas.schedule import AvailabilityResult, ScheduleResult
from app.utils.text_normalization import normalize_space
from app.utils.time_utils import day_from_date, normalize_day, overlaps, parse_date, parse_time_value, time_to_string


class ScheduleService:
    def scheduled_for_room(
        self,
        db: Session,
        *,
        room: str,
        day: str | None = None,
        on_date: str | date | None = None,
        at_time: str | time | None = None,
        start_time: str | time | None = None,
        end_time: str | time | None = None,
    ) -> list[ScheduleResult]:
        query_date = parse_date(on_date)
        query_day = day_from_date(query_date) if query_date else (normalize_day(day) or normalize_space(day))
        start, end = self._query_window(at_time=at_time, start_time=start_time, end_time=end_time)
        classroom = self._find_classroom(db, room)

        results: list[ScheduleResult] = []
        if classroom:
            results.extend(self._entries_for_classroom(db, classroom, query_day, start, end, query_date))
            results.extend(self._allocations_for_classroom(db, classroom, query_day, start, end, query_date))
        else:
            results.extend(self._entries_for_room_hint(db, room, query_day, start, end, query_date))

        if not results:
            return [
                ScheduleResult(
                    scheduled_status=ScheduledStatus.UNSCHEDULED if query_day and start and end else ScheduledStatus.UNKNOWN,
                    room=room,
                    day=query_day,
                    date=query_date,
                    start_time=time_to_string(start),
                    end_time=time_to_string(end),
                )
            ]
        return results

    def scheduled_for_class(
        self,
        db: Session,
        *,
        class_name: str,
        division: str | None = None,
        day: str | None = None,
    ) -> list[ScheduleResult]:
        query = (
            select(TimetableEntry)
            .join(Timetable)
            .join(TimeSlot)
            .options(
                joinedload(TimetableEntry.timetable),
                joinedload(TimetableEntry.classroom),
                joinedload(TimetableEntry.time_slot),
            )
            .where(Timetable.class_name == class_name, TimetableEntry.status == TimetableEntryStatus.SCHEDULED)
        )
        if division:
            query = query.where(Timetable.division == division)
        normalized_day = normalize_day(day) or normalize_space(day)
        if normalized_day:
            query = query.where(TimetableEntry.day_of_week == normalized_day)
        entries = db.execute(query.order_by(TimetableEntry.day_of_week, TimeSlot.start_time)).scalars().all()
        return [self._entry_result(entry) for entry in entries]

    def availability(
        self,
        db: Session,
        *,
        room: str,
        day: str | None = None,
        on_date: str | date | None = None,
        start_time: str | time | None = None,
        end_time: str | time | None = None,
    ) -> AvailabilityResult:
        query_date = parse_date(on_date)
        query_day = day_from_date(query_date) if query_date else (normalize_day(day) or normalize_space(day))
        start = parse_time_value(start_time)
        end = parse_time_value(end_time)
        if not query_day or not start or not end:
            return AvailabilityResult(
                room=room,
                date=query_date,
                day=query_day or "UNKNOWN",
                start_time=time_to_string(start) or "",
                end_time=time_to_string(end) or "",
                scheduled_availability="UNKNOWN",
                conflicts=[],
            )
        conflicts = [
            result
            for result in self.scheduled_for_room(
                db, room=room, day=query_day, on_date=query_date, start_time=start, end_time=end
            )
            if result.scheduled_status == ScheduledStatus.SCHEDULED
        ]
        return AvailabilityResult(
            room=room,
            date=query_date,
            day=query_day,
            start_time=start.strftime("%H:%M"),
            end_time=end.strftime("%H:%M"),
            scheduled_availability="ALLOCATED" if conflicts else "AVAILABLE",
            conflicts=conflicts,
        )

    def _query_window(
        self,
        *,
        at_time: str | time | None,
        start_time: str | time | None,
        end_time: str | time | None,
    ) -> tuple[time | None, time | None]:
        if at_time:
            start = parse_time_value(at_time)
            if not start:
                return None, None
            end_dt = datetime.combine(date.today(), start) + timedelta(minutes=1)
            return start, end_dt.time()
        return parse_time_value(start_time), parse_time_value(end_time)

    def _find_classroom(self, db: Session, room: str) -> Classroom | None:
        return db.execute(
            select(Classroom).where(or_(Classroom.room_number == room, Classroom.display_name == room))
        ).scalar_one_or_none()

    def _entries_for_classroom(
        self,
        db: Session,
        classroom: Classroom,
        day: str | None,
        start: time | None,
        end: time | None,
        query_date: date | None,
    ) -> list[ScheduleResult]:
        query = (
            select(TimetableEntry)
            .options(joinedload(TimetableEntry.timetable), joinedload(TimetableEntry.classroom), joinedload(TimetableEntry.time_slot))
            .where(TimetableEntry.classroom_id == classroom.id, TimetableEntry.status == TimetableEntryStatus.SCHEDULED)
        )
        return self._entry_query_results(db, query, day, start, end, query_date)

    def _entries_for_room_hint(
        self,
        db: Session,
        room: str,
        day: str | None,
        start: time | None,
        end: time | None,
        query_date: date | None,
    ) -> list[ScheduleResult]:
        query = (
            select(TimetableEntry)
            .options(joinedload(TimetableEntry.timetable), joinedload(TimetableEntry.classroom), joinedload(TimetableEntry.time_slot))
            .where(TimetableEntry.room_hint == room, TimetableEntry.status == TimetableEntryStatus.SCHEDULED)
        )
        return self._entry_query_results(db, query, day, start, end, query_date)

    def _entry_query_results(
        self,
        db: Session,
        query,
        day: str | None,
        start: time | None,
        end: time | None,
        query_date: date | None,
    ) -> list[ScheduleResult]:
        if day:
            query = query.where(TimetableEntry.day_of_week == day)
        query = query.join(TimeSlot)
        entries = db.execute(query.order_by(TimetableEntry.day_of_week, TimeSlot.start_time)).scalars().all()
        return [
            self._entry_result(entry, query_date)
            for entry in entries
            if not start or not end or overlaps(entry.start_time, entry.end_time, start, end)
        ]

    def _allocations_for_classroom(
        self,
        db: Session,
        classroom: Classroom,
        day: str | None,
        start: time | None,
        end: time | None,
        query_date: date | None,
    ) -> list[ScheduleResult]:
        query = select(ClassroomAllocation).where(ClassroomAllocation.classroom_id == classroom.id)
        if query_date:
            query = query.where(
                or_(ClassroomAllocation.allocation_date == query_date, ClassroomAllocation.day_of_week == day)
            )
        elif day:
            query = query.where(ClassroomAllocation.day_of_week == day)
        allocations = db.execute(query.order_by(ClassroomAllocation.start_time)).scalars().all()
        results = []
        for allocation in allocations:
            if start and end and not overlaps(allocation.start_time, allocation.end_time, start, end):
                continue
            if allocation.timetable_entry_id:
                continue
            results.append(
                ScheduleResult(
                    scheduled_status=ScheduledStatus.SCHEDULED,
                    classroom_id=classroom.id,
                    room=classroom.room_number,
                    class_name=allocation.class_name,
                    division=allocation.division,
                    subject=allocation.title,
                    faculty=allocation.faculty_text,
                    day=allocation.day_of_week or day,
                    date=allocation.allocation_date or query_date,
                    start_time=time_to_string(allocation.start_time),
                    end_time=time_to_string(allocation.end_time),
                    allocation_type=allocation.allocation_type.value,
                    source="CLASSROOM_ALLOCATION",
                )
            )
        return results

    def _entry_result(self, entry: TimetableEntry, query_date: date | None = None) -> ScheduleResult:
        classroom = entry.classroom
        timetable = entry.timetable
        return ScheduleResult(
            scheduled_status=ScheduledStatus.SCHEDULED,
            classroom_id=entry.classroom_id,
            room=classroom.room_number if classroom else entry.room_hint,
            class_name=timetable.class_name,
            division=timetable.division,
            subject=entry.subject_text,
            faculty=entry.faculty_text,
            day=entry.day_of_week,
            date=query_date,
            start_time=time_to_string(entry.start_time),
            end_time=time_to_string(entry.end_time),
            allocation_type="TIMETABLE",
            source="TIMETABLE_ENTRY",
        )
