from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol


@dataclass
class TimetableContext:
    college_name: str | None = None
    academic_year: str | None = None
    class_name: str | None = None
    department_name: str | None = None
    program_name: str | None = None
    division: str | None = None
    semester: str | None = None
    hall_name: str | None = None
    template_name: str | None = None
    confidence: float | None = None
    attributes: dict[str, Any] = field(default_factory=dict)

    def as_metadata(self) -> dict[str, Any]:
        return {key: value for key, value in vars(self).items() if value is not None and value != {}}


class ParserCapabilityError(RuntimeError):
    pass


@dataclass
class ParsedCell:
    raw_cell_text: str
    class_name: str | None = None
    division: str | None = None
    day: str | None = None
    time_text: str | None = None
    start_time_text: str | None = None
    end_time_text: str | None = None
    source_page: int | None = None
    source_sheet: str | None = None
    source_row: int | None = None
    source_column: str | None = None
    source_cell_reference: str | None = None
    bounding_box: tuple[int, int, int, int] | None = None
    extraction_method: str = "STRUCTURED"
    ocr_used: bool = False
    ocr_confidence: float | None = None
    parser_name: str | None = None
    template_name: str | None = None
    trace: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ParsedDocument:
    source_path: Path
    source_type: str
    page_count: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    cells: list[ParsedCell] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    parser_name: str | None = None
    template_name: str | None = None
    pages_extracted: int = 0
    ocr_pages: list[int] = field(default_factory=list)
    trace: dict[str, Any] = field(default_factory=dict)


class BaseTimetableParser(Protocol):
    supported_extensions: tuple[str, ...]

    def parse(self, source_path: Path) -> ParsedDocument:
        ...
