from enum import StrEnum


class RoleName(StrEnum):
    ADMIN = "ADMIN"
    FACULTY = "FACULTY"
    EXAM_COORDINATOR = "EXAM_COORDINATOR"


class AccountStatus(StrEnum):
    ACTIVE = "ACTIVE"
    INVITED = "INVITED"
    INACTIVE = "INACTIVE"


class ImportStatus(StrEnum):
    UPLOADED = "UPLOADED"
    PROCESSING = "PROCESSING"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ReviewAction(StrEnum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    EDITED = "EDITED"
    REJECTED = "REJECTED"
    IGNORED = "IGNORED"
    INVALID = "INVALID"


class ValidationStatus(StrEnum):
    VALID = "VALID"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    INVALID = "INVALID"


class ConfidenceLevel(StrEnum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class MappingStatus(StrEnum):
    NONE = "NONE"
    MATCHED = "MATCHED"
    UNMATCHED = "UNMATCHED"
    AMBIGUOUS = "AMBIGUOUS"


class LocationType(StrEnum):
    CLASSROOM = "CLASSROOM"
    LAB = "LAB"
    DEPARTMENT = "DEPARTMENT"
    ONLINE = "ONLINE"
    OFF_CAMPUS = "OFF_CAMPUS"
    PT = "PT"
    OTHER = "OTHER"
    UNKNOWN = "UNKNOWN"


class TimetableEntryStatus(StrEnum):
    SCHEDULED = "SCHEDULED"
    DRAFT = "DRAFT"
    CANCELLED = "CANCELLED"


class AllocationStatus(StrEnum):
    ALLOCATED = "ALLOCATED"
    CANCELLED = "CANCELLED"
    COMPLETED = "COMPLETED"


class AllocationType(StrEnum):
    TIMETABLE = "TIMETABLE"
    EXTRA_LECTURE = "EXTRA_LECTURE"
    EVENT = "EVENT"
    EXAMINATION = "EXAMINATION"
    MANUAL = "MANUAL"


class ScheduledStatus(StrEnum):
    SCHEDULED = "SCHEDULED"
    UNSCHEDULED = "UNSCHEDULED"
    UNKNOWN = "UNKNOWN"
