from datetime import date, time

from pydantic import BaseModel, Field, field_serializer

from app.models.enums import AllocationStatus, AllocationType, ConfidenceLevel, LocationType, MappingStatus, TimetableEntryStatus, ValidationStatus
from app.schemas.common import TimestampedRead


class TimetableCreate(BaseModel):
    college_name: str | None = None
    academic_year: str | None = Field(default=None, max_length=32)
    class_name: str = Field(min_length=1, max_length=80)
    division: str | None = Field(default=None, max_length=32)
    semester: str | None = Field(default=None, max_length=64)
    department_id: str | None = None
    program_name: str | None = Field(default=None, max_length=180)
    metadata_json: dict = Field(default_factory=dict)
    status: str = "ACTIVE"


class TimetableUpdate(BaseModel):
    college_name: str | None = None
    academic_year: str | None = Field(default=None, max_length=32)
    class_name: str | None = Field(default=None, min_length=1, max_length=80)
    division: str | None = Field(default=None, max_length=32)
    semester: str | None = Field(default=None, max_length=64)
    department_id: str | None = None
    program_name: str | None = Field(default=None, max_length=180)
    metadata_json: dict | None = None
    status: str | None = None


class TimetableRead(TimestampedRead):
    college_name: str | None = None
    academic_year: str | None = None
    class_name: str
    division: str | None = None
    semester: str | None = None
    department_id: str | None = None
    program_name: str | None = None
    metadata_json: dict
    source_import_id: str | None = None
    status: str


class TimetableEntryCreate(BaseModel):
    timetable_id: str
    day_of_week: str
    time_slot_id: str
    subject_text: str
    subject_code: str | None = None
    subject_type: str | None = None
    session_type: str | None = None
    delivery_mode: str | None = None
    subject_id: str | None = None
    faculty_text: str | None = None
    faculty_id: str | None = None
    classroom_id: str | None = None
    room_hint: str | None = None
    location_type: LocationType = LocationType.UNKNOWN
    activity_type: str | None = None
    mapping_status: MappingStatus = MappingStatus.NONE
    validation_status: ValidationStatus = ValidationStatus.VALID
    status: TimetableEntryStatus = TimetableEntryStatus.SCHEDULED
    attributes_json: dict = Field(default_factory=dict)


class TimetableEntryUpdate(BaseModel):
    day_of_week: str | None = Field(default=None, min_length=1, max_length=16)
    time_slot_id: str | None = None
    subject_text: str | None = Field(default=None, min_length=1, max_length=260)
    subject_code: str | None = Field(default=None, max_length=80)
    subject_type: str | None = Field(default=None, max_length=80)
    session_type: str | None = Field(default=None, max_length=80)
    delivery_mode: str | None = Field(default=None, max_length=80)
    faculty_text: str | None = Field(default=None, max_length=180)
    room_hint: str | None = Field(default=None, max_length=80)
    activity_type: str | None = Field(default=None, max_length=80)
    status: TimetableEntryStatus | None = None
    attributes_json: dict | None = None


class TimetableEntryRead(TimestampedRead):
    timetable_id: str
    day_of_week: str
    time_slot_id: str
    start_time: time
    end_time: time
    subject_text: str
    subject_code: str | None = None
    subject_type: str | None = None
    session_type: str | None = None
    delivery_mode: str | None = None
    subject_id: str | None = None
    faculty_text: str | None = None
    faculty_id: str | None = None
    classroom_id: str | None = None
    room_hint: str | None = None
    location_type: LocationType
    activity_type: str | None = None
    mapping_status: MappingStatus
    validation_status: ValidationStatus
    status: TimetableEntryStatus
    source_file_id: str | None = None
    source_page: int | None = None
    source_sheet: str | None = None
    source_row: int | None = None
    source_column: str | None = None
    source_cell_reference: str | None = None
    raw_cell_text: str | None = None
    raw_entry_text: str | None = None
    confidence_level: ConfidenceLevel
    confidence_score: float
    parser_name: str | None = None
    template_name: str | None = None
    extraction_method: str | None = None
    bounding_box_json: list | None = None
    trace_json: dict
    attributes_json: dict

    @field_serializer("start_time", "end_time")
    def serialize_time(self, value: time) -> str:
        return value.strftime("%H:%M")


class TimeSlotCreate(BaseModel):
    start_time: time
    end_time: time


class TimeSlotRead(TimestampedRead):
    start_time: time
    end_time: time

    @field_serializer("start_time", "end_time")
    def serialize_time(self, value: time) -> str:
        return value.strftime("%H:%M")


class TimetableStructureRead(BaseModel):
    timetable: TimetableRead
    columns: list[str]
    time_slots: list[TimeSlotRead]
    entries: list[TimetableEntryRead]
    attribute_keys: list[str]


class ClassroomAllocationCreate(BaseModel):
    classroom_id: str
    timetable_entry_id: str | None = None
    allocation_type: AllocationType = AllocationType.MANUAL
    status: AllocationStatus = AllocationStatus.ALLOCATED
    title: str = Field(min_length=1, max_length=260)
    allocation_date: date | None = None
    day_of_week: str | None = None
    start_time: time
    end_time: time
    class_name: str | None = None
    division: str | None = None
    faculty_text: str | None = None
    notes: str | None = None


class ClassroomAllocationRead(TimestampedRead):
    classroom_id: str
    timetable_entry_id: str | None = None
    allocation_type: AllocationType
    status: AllocationStatus
    title: str
    allocation_date: date | None = None
    day_of_week: str | None = None
    start_time: time
    end_time: time
    class_name: str | None = None
    division: str | None = None
    faculty_text: str | None = None
    notes: str | None = None

    @field_serializer("start_time", "end_time")
    def serialize_time(self, value: time) -> str:
        return value.strftime("%H:%M")
