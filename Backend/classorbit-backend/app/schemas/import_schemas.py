from pydantic import BaseModel

from app.models.enums import ConfidenceLevel, ImportStatus, LocationType, MappingStatus, ReviewAction, ValidationStatus
from app.schemas.common import TimestampedRead


class FileImportRead(TimestampedRead):
    original_filename: str
    file_type: str
    status: ImportStatus
    page_count: int | None = None
    metadata_json: dict
    summary_json: dict
    error_message: str | None = None
    sha256: str | None = None
    parser_version: str | None = None


class ImportReviewRead(TimestampedRead):
    file_import_id: str
    timetable_entry_id: str | None = None
    source_page: int | None = None
    source_sheet: str | None = None
    source_row: int | None = None
    source_column: str | None = None
    source_cell_reference: str | None = None
    college_name: str | None = None
    academic_year: str | None = None
    class_name: str | None = None
    division: str | None = None
    semester: str | None = None
    department_name: str | None = None
    program_name: str | None = None
    day_of_week: str | None = None
    start_time: str | None = None
    end_time: str | None = None
    subject_text: str | None = None
    subject_code: str | None = None
    subject_type: str | None = None
    session_type: str | None = None
    delivery_mode: str | None = None
    faculty_text: str | None = None
    room_hint: str | None = None
    matched_classroom_id: str | None = None
    location_type: LocationType
    activity_type: str | None = None
    mapping_status: MappingStatus
    validation_status: ValidationStatus
    action: ReviewAction
    warning: str | None = None
    raw_cell_text: str | None = None
    raw_entry_text: str | None = None
    normalized_json: dict
    confidence_level: ConfidenceLevel
    confidence_score: float
    parser_name: str | None = None
    template_name: str | None = None
    extraction_method: str | None = None
    bounding_box_json: list | None = None
    attributes_json: dict


class ImportReviewUpdate(BaseModel):
    action: ReviewAction | None = None
    class_name: str | None = None
    division: str | None = None
    department_name: str | None = None
    program_name: str | None = None
    day_of_week: str | None = None
    start_time: str | None = None
    end_time: str | None = None
    subject_text: str | None = None
    subject_code: str | None = None
    subject_type: str | None = None
    session_type: str | None = None
    delivery_mode: str | None = None
    faculty_text: str | None = None
    room_hint: str | None = None
    matched_classroom_id: str | None = None
    location_type: LocationType | None = None
    activity_type: str | None = None
    validation_status: ValidationStatus | None = None
    warning: str | None = None


class ImportConfirmResponse(BaseModel):
    import_id: str
    created_entries: int
    skipped_records: int
    unresolved_review_records: int
    status: ImportStatus
