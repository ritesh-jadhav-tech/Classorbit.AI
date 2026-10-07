from __future__ import annotations

from datetime import date as Date

from pydantic import BaseModel

from app.models.enums import ScheduledStatus


class ScheduleResult(BaseModel):
    scheduled_status: ScheduledStatus
    classroom_id: str | None = None
    room: str | None = None
    class_name: str | None = None
    division: str | None = None
    subject: str | None = None
    faculty: str | None = None
    day: str | None = None
    date: Date | None = None
    start_time: str | None = None
    end_time: str | None = None
    allocation_type: str | None = None
    source: str | None = None


class AvailabilityResult(BaseModel):
    room: str
    date: Date | None = None
    day: str
    start_time: str
    end_time: str
    scheduled_availability: str
    conflicts: list[ScheduleResult]
