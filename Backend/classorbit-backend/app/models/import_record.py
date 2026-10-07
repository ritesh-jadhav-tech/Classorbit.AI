from sqlalchemy import JSON, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, IdTimestampMixin
from app.models.enums import ConfidenceLevel, ImportStatus, LocationType, MappingStatus, ReviewAction, ValidationStatus


class FileImport(Base, IdTimestampMixin):
    __tablename__ = "file_imports"

    original_filename: Mapped[str] = mapped_column(String(260), nullable=False)
    file_type: Mapped[str] = mapped_column(String(24), nullable=False)
    stored_path: Mapped[str] = mapped_column(String(500), nullable=False)
    uploaded_by_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    status: Mapped[ImportStatus] = mapped_column(
        Enum(ImportStatus, native_enum=False), default=ImportStatus.UPLOADED, nullable=False
    )
    page_count: Mapped[int | None] = mapped_column(Integer)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    summary_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text)
    sha256: Mapped[str | None] = mapped_column(String(64), index=True)
    parser_version: Mapped[str | None] = mapped_column(String(32))

    uploaded_by: Mapped["User | None"] = relationship()
    review_records: Mapped[list["ImportReview"]] = relationship(back_populates="file_import", cascade="all, delete-orphan")
    timetables: Mapped[list["Timetable"]] = relationship(back_populates="source_import")
    entries: Mapped[list["TimetableEntry"]] = relationship(back_populates="source_file")


class ImportReview(Base, IdTimestampMixin):
    __tablename__ = "import_reviews"

    file_import_id: Mapped[str] = mapped_column(ForeignKey("file_imports.id"), nullable=False)
    timetable_entry_id: Mapped[str | None] = mapped_column(ForeignKey("timetable_entries.id"))
    source_page: Mapped[int | None] = mapped_column(Integer)
    source_sheet: Mapped[str | None] = mapped_column(String(120))
    source_row: Mapped[int | None] = mapped_column(Integer)
    source_column: Mapped[str | None] = mapped_column(String(80))
    source_cell_reference: Mapped[str | None] = mapped_column(String(120))

    college_name: Mapped[str | None] = mapped_column(String(260))
    academic_year: Mapped[str | None] = mapped_column(String(32))
    class_name: Mapped[str | None] = mapped_column(String(80))
    division: Mapped[str | None] = mapped_column(String(32))
    semester: Mapped[str | None] = mapped_column(String(64))
    department_name: Mapped[str | None] = mapped_column(String(180))
    program_name: Mapped[str | None] = mapped_column(String(180))
    day_of_week: Mapped[str | None] = mapped_column(String(16))
    start_time: Mapped[str | None] = mapped_column(String(16))
    end_time: Mapped[str | None] = mapped_column(String(16))
    subject_text: Mapped[str | None] = mapped_column(String(260))
    subject_code: Mapped[str | None] = mapped_column(String(80))
    subject_type: Mapped[str | None] = mapped_column(String(80))
    session_type: Mapped[str | None] = mapped_column(String(80))
    delivery_mode: Mapped[str | None] = mapped_column(String(80))
    faculty_text: Mapped[str | None] = mapped_column(String(180))
    room_hint: Mapped[str | None] = mapped_column(String(80))
    matched_classroom_id: Mapped[str | None] = mapped_column(ForeignKey("classrooms.id"))
    location_type: Mapped[LocationType] = mapped_column(
        Enum(LocationType, native_enum=False), default=LocationType.UNKNOWN, nullable=False
    )
    activity_type: Mapped[str | None] = mapped_column(String(80))
    mapping_status: Mapped[MappingStatus] = mapped_column(
        Enum(MappingStatus, native_enum=False), default=MappingStatus.NONE, nullable=False
    )
    validation_status: Mapped[ValidationStatus] = mapped_column(
        Enum(ValidationStatus, native_enum=False), default=ValidationStatus.NEEDS_REVIEW, nullable=False
    )
    action: Mapped[ReviewAction] = mapped_column(
        Enum(ReviewAction, native_enum=False), default=ReviewAction.PENDING, nullable=False
    )
    warning: Mapped[str | None] = mapped_column(Text)
    raw_cell_text: Mapped[str | None] = mapped_column(Text)
    raw_entry_text: Mapped[str | None] = mapped_column(Text)
    normalized_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    confidence_level: Mapped[ConfidenceLevel] = mapped_column(
        Enum(ConfidenceLevel, native_enum=False), default=ConfidenceLevel.MEDIUM, nullable=False
    )
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    parser_name: Mapped[str | None] = mapped_column(String(120))
    template_name: Mapped[str | None] = mapped_column(String(120))
    extraction_method: Mapped[str | None] = mapped_column(String(80))
    bounding_box_json: Mapped[list | None] = mapped_column(JSON)
    attributes_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    file_import: Mapped[FileImport] = relationship(back_populates="review_records")
    matched_classroom: Mapped["Classroom | None"] = relationship()
    timetable_entry: Mapped["TimetableEntry | None"] = relationship()
