import re

from app.models.enums import LocationType, MappingStatus, ValidationStatus
from app.services.timetable_normalizer import NormalizedTimetableEntry


class TimetableValidator:
    def validate(self, entry: NormalizedTimetableEntry) -> NormalizedTimetableEntry:
        errors: list[str] = []
        warnings: list[str] = []
        if entry.warning:
            warnings.append(entry.warning)

        if not entry.class_name:
            errors.append("Class name is missing.")
        if not entry.day_of_week:
            errors.append("Day is missing or invalid.")
        if not entry.start_time or not entry.end_time:
            errors.append("Start/end time is missing or invalid.")
        elif entry.end_time <= entry.start_time:
            errors.append("End time must be after start time.")
        if not entry.subject_text:
            errors.append("Subject/activity text is missing.")
        elif self._is_non_subject(entry.subject_text):
            errors.append("Extracted value is a header, placeholder, time, or classroom-only fragment.")
        elif entry.room_hint and self._subject_still_contains_room(entry.subject_text, entry.room_hint):
            warnings.append("Room hint may still be included in subject text.")

        if entry.room_hint and entry.location_type in {LocationType.ONLINE, LocationType.DEPARTMENT}:
            warnings.append("Room hint ignored for non-classroom location.")

        if errors:
            entry.validation_status = ValidationStatus.INVALID
            entry.warning = "; ".join(errors + warnings)
        elif warnings:
            entry.validation_status = ValidationStatus.NEEDS_REVIEW
            entry.mapping_status = MappingStatus.AMBIGUOUS if entry.mapping_status == MappingStatus.NONE else entry.mapping_status
            entry.warning = "; ".join(warnings)
        else:
            entry.validation_status = ValidationStatus.VALID
        return entry

    @staticmethod
    def _is_non_subject(value: str) -> bool:
        text = value.strip()
        if not text or text.upper() in {"-", "--", "N/A", "NA", "TIME"}:
            return True
        if text.lower() in {"monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"}:
            return True
        if re.fullmatch(r"(?:CC|AB|GE)?\s*-?\s*\d{1,4}[A-Z]?", text, re.I):
            return True
        if re.fullmatch(r"\d{1,2}[.:]\d{2}(?:\s*(?:am|pm))?", text, re.I):
            return True
        return False

    @staticmethod
    def _subject_still_contains_room(subject: str, room: str) -> bool:
        normalized_subject = re.sub(r"\s+", "", subject).upper()
        normalized_room = re.sub(r"\s+", "", room).upper()
        return bool(normalized_room and normalized_subject.endswith(normalized_room))
