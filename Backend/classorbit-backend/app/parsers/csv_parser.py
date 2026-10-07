import csv
from pathlib import Path

from app.parsers.base import ParsedCell, ParsedDocument
from app.utils.text_normalization import normalize_space


class CsvTimetableParser:
    supported_extensions = (".csv",)

    def parse(self, source_path: Path) -> ParsedDocument:
        cells: list[ParsedCell] = []
        with source_path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            for index, row in enumerate(reader, start=2):
                normalized = {normalize_space(key).lower().replace(" ", "_"): value for key, value in row.items() if key}
                raw_cell_text = first_value(
                    normalized,
                    "raw_cell_text",
                    "raw_text",
                    "entry",
                    "cell",
                    "subject",
                    default="",
                )
                room_hint = first_value(normalized, "room", "room_hint", "classroom", "lecture_hall")
                metadata = structured_metadata(normalized, room_hint)
                cells.append(
                    ParsedCell(
                        raw_cell_text=raw_cell_text,
                        class_name=first_value(normalized, "class_name", "class", "course"),
                        division=first_value(normalized, "division", "div"),
                        day=first_value(normalized, "day", "day_of_week"),
                        time_text=first_value(normalized, "time", "time_slot", "slot"),
                        start_time_text=first_value(normalized, "start_time", "start"),
                        end_time_text=first_value(normalized, "end_time", "end"),
                        source_row=index,
                        source_column="raw_cell_text",
                        source_cell_reference=f"row:{index}",
                        extraction_method="CSV_STRUCTURED",
                        parser_name=self.__class__.__name__,
                        template_name="STRUCTURED_ROWS_V1",
                        trace=[{"decision": "named_columns", "row": index}],
                        metadata={**metadata, "row": normalized},
                    )
                )
        return ParsedDocument(
            source_path=source_path,
            source_type="CSV",
            cells=cells,
            page_count=1,
            parser_name=self.__class__.__name__,
            template_name="STRUCTURED_ROWS_V1",
            pages_extracted=1 if cells else 0,
        )


def first_value(row: dict[str, str | None], *keys: str, default: str | None = None) -> str | None:
    for key in keys:
        value = row.get(key)
        if value is not None and normalize_space(str(value)):
            return normalize_space(str(value))
    return default


def structured_metadata(row: dict[str, str | None], room_hint: str | None) -> dict:
    consumed = {
        "raw_cell_text", "raw_text", "entry", "cell", "subject", "room", "room_hint", "classroom",
        "lecture_hall", "class_name", "class", "course", "division", "div", "day", "day_of_week",
        "time", "time_slot", "slot", "start_time", "start", "end_time", "end", "department",
        "department_name", "program", "program_name", "semester", "academic_year", "year", "subject_code",
        "code", "faculty", "teacher", "instructor",
    }
    return {
        "room_hint": room_hint,
        "department_name": first_value(row, "department_name", "department"),
        "program_name": first_value(row, "program_name", "program"),
        "semester": first_value(row, "semester"),
        "academic_year": first_value(row, "academic_year", "year"),
        "subject_code": first_value(row, "subject_code", "code"),
        "faculty_text": first_value(row, "faculty", "teacher", "instructor"),
        "attributes": {
            key: normalize_space(str(value))
            for key, value in row.items()
            if key not in consumed and value is not None and normalize_space(str(value))
        },
    }
