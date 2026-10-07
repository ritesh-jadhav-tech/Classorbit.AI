import re
from dataclasses import dataclass, field
from datetime import time

from app.models.enums import ConfidenceLevel, LocationType, MappingStatus, ValidationStatus
from app.parsers.base import ParsedCell
from app.utils.text_normalization import normalize_room_hint, normalize_space, split_cell_entries
from app.utils.time_utils import normalize_day, parse_time_range, time_to_string


CONFIDENT_ROOM_RE = re.compile(
    r"^(?P<subject>.+?)(?:\s+|(?<=[A-Za-z])-)(?P<room>(?:CC\s*[- ]?\s*\d{1,2}|AB\s*[- ]?\s*\d{1,2}|[A-Z]{1,3}-?\d{2,4}|\d{3,4}[A-Z]?))$",
    re.I,
)
SHORT_TRAILING_NUMBER_RE = re.compile(r".+\b\d{1,2}$")
CATEGORY_RE = re.compile(r"\b(Major|Minor|AEC|SEC|VSC|GE|OE|Open\s+Elective)\b", re.I)
ANNOTATION_ONLY_RE = re.compile(
    r"^(?:[\s,.;:/()\-]*(?:major(?:\s+core\s+paper)?|minor|mooc(?:\s+course)?|macro|"
    r"vsc|sec|aec|ge|oe|open\s+elective(?:\s+course)?)[\s,.;:/()\-]*)+$",
    re.I,
)
FACULTY_LABEL_RE = re.compile(r"^(?:faculty|teacher|professor|instructor)\s*[:\-]\s*(?P<name>.+)$", re.I)
TITLED_FACULTY_RE = re.compile(
    r"^(?P<name>(?:(?:prof(?:essor)?|dr|mr|mrs|ms)\.?\s*)[A-Za-z][A-Za-z .&'-]{1,120})$",
    re.I,
)


@dataclass
class NormalizedTimetableEntry:
    college_name: str | None
    academic_year: str | None
    class_name: str | None
    division: str | None
    semester: str | None
    department_name: str | None
    program_name: str | None
    day_of_week: str | None
    start_time: time | None
    end_time: time | None
    subject_text: str | None
    subject_code: str | None = None
    subject_type: str | None = None
    session_type: str | None = None
    delivery_mode: str | None = None
    faculty_text: str | None = None
    room_hint: str | None = None
    location_type: LocationType = LocationType.UNKNOWN
    activity_type: str | None = None
    mapping_status: MappingStatus = MappingStatus.NONE
    validation_status: ValidationStatus = ValidationStatus.VALID
    warning: str | None = None
    source_page: int | None = None
    source_sheet: str | None = None
    source_row: int | None = None
    source_column: str | None = None
    source_cell_reference: str | None = None
    raw_cell_text: str | None = None
    raw_entry_text: str | None = None
    normalized_json: dict = field(default_factory=dict)
    confidence_level: ConfidenceLevel = ConfidenceLevel.MEDIUM
    confidence_score: float = 0.0
    parser_name: str | None = None
    template_name: str | None = None
    extraction_method: str | None = None
    bounding_box: tuple[int, int, int, int] | None = None
    attributes_json: dict = field(default_factory=dict)

    @property
    def start_time_text(self) -> str | None:
        return time_to_string(self.start_time)

    @property
    def end_time_text(self) -> str | None:
        return time_to_string(self.end_time)


class TimetableNormalizer:
    def normalize_cell(self, cell: ParsedCell, document_metadata: dict) -> list[NormalizedTimetableEntry]:
        raw_entries = split_cell_entries(cell.raw_cell_text)
        is_standard_row = bool(cell.metadata.get("standard_template"))
        if is_standard_row:
            raw_entries = [normalize_space(cell.raw_cell_text)]
        faculty_text = first_present(cell.metadata.get("faculty_text"))
        annotations: list[str] = []
        contextual_subject_type = None
        activity_entries: list[str] = []
        for raw_entry in raw_entries:
            subject_fragment, detected_faculty = self._extract_faculty(raw_entry)
            faculty_text = faculty_text or detected_faculty
            if not subject_fragment:
                continue
            annotation_type = self._annotation_type(subject_fragment)
            if annotation_type:
                annotations.append(normalize_space(subject_fragment))
                if annotation_type != "ANNOTATION":
                    contextual_subject_type = contextual_subject_type or annotation_type
                continue
            activity_entries.append(subject_fragment)
        if is_standard_row and not activity_entries and cell.metadata.get("raw_room"):
            activity_entries.append("")
        raw_entries = activity_entries
        if not raw_entries:
            return []

        start_time, end_time = parse_time_range(
            cell.time_text,
            start_value=cell.start_time_text,
            end_value=cell.end_time_text,
        )
        entries: list[NormalizedTimetableEntry] = []
        for raw_entry in raw_entries:
            location_department = self._department_location(raw_entry)
            (
                subject_text,
                room_hint,
                location_type,
                activity_type,
                warning,
                subject_type,
                session_type,
                delivery_mode,
            ) = self._parse_entry_text(
                raw_entry, cell.metadata.get("room_hint")
            )
            subject_type = subject_type or contextual_subject_type
            warning = self._append_warning(warning, cell.metadata.get("standard_warning"))
            missing_metadata = cell.metadata.get("required_metadata_missing") or []
            if missing_metadata:
                warning = self._append_warning(
                    warning,
                    f"Missing required metadata: {', '.join(missing_metadata)}.",
                )
            explicit_location = self._location_type(cell.metadata.get("location_type"))
            if explicit_location is not None:
                location_type = explicit_location
                if location_type in {LocationType.ONLINE, LocationType.DEPARTMENT, LocationType.OFF_CAMPUS}:
                    room_hint = None
            activity_type = first_present(cell.metadata.get("activity_type"), activity_type)
            if is_standard_row and "/" in raw_entry:
                warning = self._append_warning(
                    warning,
                    "Standard template row contains slash-separated content; confirm it is one activity.",
                )
            department_name = first_present(
                cell.metadata.get("department_name"), document_metadata.get("department_name")
            )
            subject_department_hint = self._subject_department_hint(subject_text)
            if location_type == LocationType.DEPARTMENT:
                location_department = location_department or subject_department_hint or department_name
                if location_department:
                    room_hint = normalize_room_hint(f"{location_department} Department Lab")
                    location_type = LocationType.LAB
                    session_type = session_type or "LAB"
            elif location_type == LocationType.LAB and not room_hint:
                location_department = location_department or subject_department_hint or department_name
                if location_department:
                    room_hint = normalize_room_hint(f"{location_department} Department Lab")
            attributes = {
                key: value
                for key, value in (cell.metadata.get("attributes") or {}).items()
                if not key.startswith("source_")
            }
            if annotations:
                attributes["curriculum_annotations"] = annotations
            if len(raw_entries) > 1:
                attributes["parallel_activity"] = True
                attributes.setdefault("schedule_track", cell.source_cell_reference or "same timetable cell")
            if location_department:
                attributes["location_department"] = location_department
            if subject_type and subject_text and CATEGORY_RE.fullmatch(subject_text) and department_name:
                subject_text = department_name
            entry = NormalizedTimetableEntry(
                college_name=first_present(cell.metadata.get("college_name"), document_metadata.get("college_name")),
                academic_year=first_present(cell.metadata.get("academic_year"), document_metadata.get("academic_year")),
                class_name=first_present(cell.class_name, cell.metadata.get("class_name"), document_metadata.get("class_name")),
                division=first_present(cell.division, cell.metadata.get("division"), document_metadata.get("division")),
                semester=first_present(cell.metadata.get("semester"), document_metadata.get("semester")),
                department_name=department_name,
                program_name=first_present(cell.metadata.get("program_name"), document_metadata.get("program_name")),
                day_of_week=normalize_day(cell.day) or first_present(cell.day),
                start_time=start_time,
                end_time=end_time,
                subject_text=subject_text,
                subject_code=first_present(cell.metadata.get("subject_code")),
                subject_type=subject_type,
                session_type=session_type,
                delivery_mode=delivery_mode,
                faculty_text=faculty_text,
                room_hint=room_hint,
                location_type=location_type,
                activity_type=activity_type,
                warning=warning,
                source_page=cell.source_page,
                source_sheet=cell.source_sheet,
                source_row=cell.source_row,
                source_column=cell.source_column,
                source_cell_reference=cell.source_cell_reference,
                raw_cell_text=cell.raw_cell_text,
                raw_entry_text=raw_entry,
                parser_name=cell.parser_name,
                template_name=cell.template_name,
                extraction_method=cell.extraction_method,
                bounding_box=cell.bounding_box,
                attributes_json=attributes,
            )
            entry.normalized_json = {
                "raw_entry_text": raw_entry,
                "source_metadata": cell.metadata,
                "provenance": {
                    "bounding_box": cell.bounding_box,
                    "extraction_method": cell.extraction_method,
                    "ocr_used": cell.ocr_used,
                    "ocr_confidence": cell.ocr_confidence,
                    "parser_name": cell.parser_name,
                    "template_name": cell.template_name,
                },
                "decisions": [
                    *cell.trace,
                    {
                        "decision": "subject_room_separation",
                        "raw": raw_entry,
                        "subject": subject_text,
                        "room": room_hint,
                        "rule": "confident_trailing_room" if room_hint else "no_confident_room",
                    },
                    {
                        "decision": "standard_source_values",
                        "raw_subject": cell.metadata.get("raw_subject"),
                        "raw_room": cell.metadata.get("raw_room"),
                        "time_cell": cell.metadata.get("time_cell"),
                        "subject_cell": cell.metadata.get("subject_cell"),
                        "room_cell": cell.metadata.get("room_cell"),
                    } if is_standard_row else {},
                    *(
                        [{"decision": "department_subject_inheritance", "subject": subject_text}]
                        if subject_type and subject_text == department_name
                        else []
                    ),
                ],
            }
            entries.append(entry)
        return entries

    @staticmethod
    def _extract_faculty(value: str) -> tuple[str | None, str | None]:
        text = normalize_space(value)
        candidate = text[1:-1].strip() if text.startswith("(") and text.endswith(")") else text
        label_match = FACULTY_LABEL_RE.fullmatch(candidate)
        if label_match:
            return None, normalize_space(label_match.group("name"))
        title_match = TITLED_FACULTY_RE.fullmatch(candidate)
        if title_match:
            return None, normalize_space(title_match.group("name"))
        inline_match = re.fullmatch(
            r"(?P<subject>.+?)\s+(?:-|:)\s*(?P<faculty>(?:(?:prof(?:essor)?|dr|mr|mrs|ms)\.?\s+)"
            r"[A-Za-z][A-Za-z .'-]{1,120})",
            text,
            re.I,
        )
        if inline_match:
            return normalize_space(inline_match.group("subject")), normalize_space(inline_match.group("faculty"))
        return text or None, None

    @staticmethod
    def _annotation_type(value: str) -> str | None:
        text = normalize_space(value)
        if not text or not ANNOTATION_ONLY_RE.fullmatch(text):
            return None
        match = CATEGORY_RE.search(text)
        return normalize_space(match.group(1)).upper().replace(" ", "_") if match else "ANNOTATION"

    @staticmethod
    def _location_type(value: object) -> LocationType | None:
        text = normalize_space(str(value)) if value is not None else ""
        if not text:
            return None
        normalized = text.upper().replace("-", "_").replace(" ", "_")
        aliases = {"OFFCAMPUS": "OFF_CAMPUS", "IN_DEPARTMENT": "DEPARTMENT"}
        normalized = aliases.get(normalized, normalized)
        try:
            return LocationType(normalized)
        except ValueError:
            return LocationType.OTHER

    @staticmethod
    def _append_warning(current: str | None, warning: str) -> str:
        return "; ".join(value for value in (current, warning) if value)

    def _parse_entry_text(
        self, raw_entry: str, explicit_room_hint: str | None = None
    ) -> tuple[
        str | None,
        str | None,
        LocationType,
        str | None,
        str | None,
        str | None,
        str | None,
        str | None,
    ]:
        text = normalize_space(raw_entry)
        lower = text.lower()
        room_hint = normalize_room_hint(explicit_room_hint)
        location_type = LocationType.UNKNOWN
        activity_type = None
        warning = None
        subject_type = None
        session_type = None
        delivery_mode = None

        named_lab_match = re.search(r"\(([^()]*(?:lab|laboratory))\)\s*$", text, re.I)
        batch_lab_match = re.search(r"\bBatch\s+[A-Z0-9]+\s+([A-Z][A-Za-z0-9 .&-]{0,40}\s+Lab)\b", text, re.I)
        if named_lab_match and normalize_space(named_lab_match.group(1)).lower() not in {"lab", "in lab"}:
            room_hint = normalize_room_hint(named_lab_match.group(1))
            location_type = LocationType.LAB
            session_type = "LAB"
        elif batch_lab_match:
            room_hint = normalize_room_hint(batch_lab_match.group(1))
            location_type = LocationType.LAB
            session_type = "LAB"
        if "online" in lower:
            location_type = LocationType.ONLINE
            delivery_mode = "ONLINE"
        elif "department" in lower:
            location_type = LocationType.DEPARTMENT
        elif "lab" in lower:
            location_type = LocationType.LAB
            session_type = "LAB"
        elif lower in {"p.t.", "pt", "p.t"} or "p.t." in lower:
            location_type = LocationType.PT
            activity_type = "PT"
        elif "sec" == lower or lower.startswith("sec "):
            activity_type = "SEC"

        if "practical" in lower:
            session_type = "PRACTICAL"
        elif re.search(r"\blecture\b", lower):
            session_type = "LECTURE"

        category_match = CATEGORY_RE.search(text)
        if category_match:
            subject_type = normalize_space(category_match.group(1)).upper().replace(" ", "_")
            activity_type = activity_type or subject_type

        subject_text = text
        if not room_hint:
            match = CONFIDENT_ROOM_RE.match(text)
            if match:
                subject_text = normalize_space(match.group("subject"))
                room_hint = normalize_room_hint(match.group("room"))
                location_type = LocationType.CLASSROOM if location_type == LocationType.UNKNOWN else location_type
            elif SHORT_TRAILING_NUMBER_RE.match(text) and location_type not in {LocationType.ONLINE, LocationType.DEPARTMENT, LocationType.LAB}:
                warning = "Trailing short number is ambiguous and was not treated as a classroom."

        subject_text = self._strip_location_notes(subject_text)
        subject_text = self._strip_category(subject_text, subject_type)
        return (
            subject_text or None,
            room_hint,
            location_type,
            activity_type,
            warning,
            subject_type,
            session_type,
            delivery_mode,
        )

    @staticmethod
    def _department_location(value: str) -> str | None:
        match = re.search(
            r"\((?:in\s+)?(?:(?P<name>[A-Za-z][A-Za-z .&-]{0,80}?)\s+)?department\)",
            value,
            re.I,
        )
        if not match or not match.group("name"):
            return None
        return normalize_space(match.group("name"))

    @staticmethod
    def _subject_department_hint(value: str | None) -> str | None:
        if not value:
            return None
        candidate = re.sub(r"^Sem(?:ester)?\s+[IVX0-9]+\s+", "", value, flags=re.I)
        candidate = re.sub(r"\b(?:Major|Minor|VSC|SEC|AEC|Practical|Lab Course)\b", " ", candidate, flags=re.I)
        candidate = re.sub(r"\bLab\b$", "", candidate, flags=re.I)
        candidate = normalize_space(candidate).strip("-:()")
        if not candidate or any(character.isdigit() for character in candidate) or len(candidate.split()) > 4:
            return None
        return candidate

    def _strip_location_notes(self, value: str) -> str:
        return normalize_space(
            re.sub(r"\((?:in\s+)?(?:[^)]*\s+)?(?:lab|department|online course|online)\)", "", value, flags=re.I)
        )

    def _strip_category(self, value: str, subject_type: str | None) -> str:
        if not subject_type:
            return value
        category = subject_type.replace("_", r"\s+")
        stripped = re.sub(rf"^(?:{category})\s+|\s+(?:{category})$", "", value, flags=re.I)
        return normalize_space(stripped) or value


def first_present(*values: object) -> str | None:
    for value in values:
        if value is None:
            continue
        text = normalize_space(str(value))
        if text:
            return text
    return None
