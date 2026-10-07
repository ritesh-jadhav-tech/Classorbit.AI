from datetime import date, time

from sqlalchemy import JSON, Date, Enum, Float, ForeignKey, String, Text, Time, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, IdTimestampMixin
from app.models.enums import AllocationStatus, AllocationType, ConfidenceLevel, LocationType, MappingStatus, TimetableEntryStatus, ValidationStatus


class Timetable(Base, IdTimestampMixin):
    __tablename__ = "timetables"
    __table_args__ = (
        UniqueConstraint(
            "academic_year",
            "class_name",
            "division",
            "semester",
            "department_id",
            "program_name",
            "source_import_id",
            name="uq_timetable_context_source",
        ),
    )

    college_name: Mapped[str | None] = mapped_column(String(260))
    academic_year: Mapped[str | None] = mapped_column(String(32))
    class_name: Mapped[str] = mapped_column(String(80), nullable=False)
    division: Mapped[str | None] = mapped_column(String(32))
    semester: Mapped[str | None] = mapped_column(String(64))
    department_id: Mapped[str | None] = mapped_column(ForeignKey("departments.id"))
    program_name: Mapped[str | None] = mapped_column(String(180))
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    source_import_id: Mapped[str | None] = mapped_column(ForeignKey("file_imports.id"))
    status: Mapped[str] = mapped_column(String(32), default="ACTIVE", nullable=False)

    source_import: Mapped["FileImport | None"] = relationship(back_populates="timetables")
    department: Mapped["Department | None"] = relationship(back_populates="timetables")
    entries: Mapped[list["TimetableEntry"]] = relationship(back_populates="timetable", cascade="all, delete-orphan")


class TimeSlot(Base, IdTimestampMixin):
    __tablename__ = "time_slots"
    __table_args__ = (UniqueConstraint("start_time", "end_time", name="uq_time_slot_range"),)

    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)

    timetable_entries: Mapped[list["TimetableEntry"]] = relationship(back_populates="time_slot")


class TimetableEntry(Base, IdTimestampMixin):
    __tablename__ = "timetable_entries"
    __table_args__ = (
        UniqueConstraint(
            "timetable_id",
            "day_of_week",
            "time_slot_id",
            "subject_text",
            "room_hint",
            "raw_entry_text",
            name="uq_timetable_entry_source_identity",
        ),
    )

    timetable_id: Mapped[str] = mapped_column(ForeignKey("timetables.id"), nullable=False)
    day_of_week: Mapped[str] = mapped_column(String(16), index=True, nullable=False)
    time_slot_id: Mapped[str] = mapped_column(ForeignKey("time_slots.id"), nullable=False, index=True)
    subject_text: Mapped[str] = mapped_column(String(260), nullable=False)
    subject_code: Mapped[str | None] = mapped_column(String(80))
    subject_type: Mapped[str | None] = mapped_column(String(80))
    session_type: Mapped[str | None] = mapped_column(String(80))
    delivery_mode: Mapped[str | None] = mapped_column(String(80))
    subject_id: Mapped[str | None] = mapped_column(ForeignKey("subjects.id"))
    faculty_text: Mapped[str | None] = mapped_column(String(180))
    faculty_id: Mapped[str | None] = mapped_column(ForeignKey("faculty.id"))
    classroom_id: Mapped[str | None] = mapped_column(ForeignKey("classrooms.id"))
    room_hint: Mapped[str | None] = mapped_column(String(80))
    location_type: Mapped[LocationType] = mapped_column(
        Enum(LocationType, native_enum=False), default=LocationType.UNKNOWN, nullable=False
    )
    activity_type: Mapped[str | None] = mapped_column(String(80))
    mapping_status: Mapped[MappingStatus] = mapped_column(
        Enum(MappingStatus, native_enum=False), default=MappingStatus.NONE, nullable=False
    )
    validation_status: Mapped[ValidationStatus] = mapped_column(
        Enum(ValidationStatus, native_enum=False), default=ValidationStatus.VALID, nullable=False
    )
    status: Mapped[TimetableEntryStatus] = mapped_column(
        Enum(TimetableEntryStatus, native_enum=False), default=TimetableEntryStatus.SCHEDULED, nullable=False
    )
    source_file_id: Mapped[str | None] = mapped_column(ForeignKey("file_imports.id"))
    source_page: Mapped[int | None]
    source_sheet: Mapped[str | None] = mapped_column(String(120))
    source_row: Mapped[int | None]
    source_column: Mapped[str | None] = mapped_column(String(80))
    source_cell_reference: Mapped[str | None] = mapped_column(String(120))
    raw_cell_text: Mapped[str | None] = mapped_column(Text)
    raw_entry_text: Mapped[str | None] = mapped_column(Text)
    confidence_level: Mapped[ConfidenceLevel] = mapped_column(
        Enum(ConfidenceLevel, native_enum=False), default=ConfidenceLevel.MEDIUM, nullable=False
    )
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    parser_name: Mapped[str | None] = mapped_column(String(120))
    template_name: Mapped[str | None] = mapped_column(String(120))
    extraction_method: Mapped[str | None] = mapped_column(String(80))
    bounding_box_json: Mapped[list | None] = mapped_column(JSON)
    trace_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    attributes_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    timetable: Mapped[Timetable] = relationship(back_populates="entries")
    time_slot: Mapped[TimeSlot] = relationship(back_populates="timetable_entries")
    subject: Mapped["Subject | None"] = relationship(back_populates="timetable_entries")
    faculty: Mapped["Faculty | None"] = relationship(back_populates="timetable_entries")
    classroom: Mapped["Classroom | None"] = relationship(back_populates="timetable_entries")
    source_file: Mapped["FileImport | None"] = relationship(back_populates="entries")
    allocations: Mapped[list["ClassroomAllocation"]] = relationship(back_populates="timetable_entry")

    @property
    def start_time(self) -> time:
        return self.time_slot.start_time

    @property
    def end_time(self) -> time:
        return self.time_slot.end_time


class ClassroomAllocation(Base, IdTimestampMixin):
    __tablename__ = "classroom_allocations"

    classroom_id: Mapped[str] = mapped_column(ForeignKey("classrooms.id"), nullable=False)
    timetable_entry_id: Mapped[str | None] = mapped_column(ForeignKey("timetable_entries.id"))
    allocation_type: Mapped[AllocationType] = mapped_column(
        Enum(AllocationType, native_enum=False), default=AllocationType.MANUAL, nullable=False
    )
    status: Mapped[AllocationStatus] = mapped_column(
        Enum(AllocationStatus, native_enum=False), default=AllocationStatus.ALLOCATED, nullable=False
    )
    title: Mapped[str] = mapped_column(String(260), nullable=False)
    allocation_date: Mapped[date | None] = mapped_column(Date)
    day_of_week: Mapped[str | None] = mapped_column(String(16), index=True)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    class_name: Mapped[str | None] = mapped_column(String(80))
    division: Mapped[str | None] = mapped_column(String(32))
    faculty_text: Mapped[str | None] = mapped_column(String(180))
    notes: Mapped[str | None] = mapped_column(Text)

    classroom: Mapped["Classroom"] = relationship(back_populates="allocations")
    timetable_entry: Mapped[TimetableEntry | None] = relationship(back_populates="allocations")
