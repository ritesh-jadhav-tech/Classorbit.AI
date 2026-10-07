import re
from collections.abc import Sequence

from app.parsers.base import ParsedCell
from app.parsers.pdf_parser import PdfTimetableParser
from app.utils.text_normalization import is_blank_cell, normalize_space
from app.utils.time_utils import normalize_day, parse_time_range, time_to_string


MATRIX_METADATA_LABELS = {
    "department": "department_name",
    "academic year": "academic_year",
    "class / program": "class_name",
    "class/program": "class_name",
    "class": "class_name",
    "division": "division",
    "semester": "semester",
    "common hall / default room": "room_hint",
    "common hall/default room": "room_hint",
}


def cells_from_matrix(
    rows: Sequence[Sequence[object]],
    *,
    source_name: str,
    extraction_method: str,
    source_page: int,
    context_prefix: str = "",
) -> list[ParsedCell]:
    matrix = [[_matrix_value(value) for value in row] for row in rows]
    header_indexes = [
        index
        for index, row in enumerate(matrix)
        if len([value for value in row if normalize_day(value)]) >= 2
    ]
    cells: list[ParsedCell] = []
    sheet_metadata = _labeled_matrix_metadata(matrix[:header_indexes[0]]) if header_indexes else {}
    for header_position, header_index in enumerate(header_indexes):
        next_header = header_indexes[header_position + 1] if header_position + 1 < len(header_indexes) else len(matrix)
        header = matrix[header_index]
        day_columns = [(index, normalize_day(value)) for index, value in enumerate(header) if normalize_day(value)]
        first_day_index = min(index for index, _ in day_columns)
        explicit_time = next(
            (index for index, value in enumerate(header[:first_day_index]) if value.lower().rstrip(".:") in {"time", "period", "slot"}),
            None,
        )
        time_column = explicit_time if explicit_time is not None else max(0, first_day_index - 1)
        context_start = header_indexes[header_position - 1] + 1 if header_position else 0
        context_text = " ".join(
            [
                *(value for row in matrix[context_start:header_index] for value in row if value),
                context_prefix,
            ]
        )
        detected_metadata = PdfTimetableParser()._detect_metadata(context_text)
        metadata = {
            **{key: value for key, value in detected_metadata.items() if value not in (None, "", {})},
            **sheet_metadata,
        }
        metadata["program_name"] = metadata.get("program_name") or metadata.get("class_name")
        section_room = _section_lab_hint(matrix[context_start:header_index])
        if section_room:
            metadata["room_hint"] = section_room
            metadata["location_type"] = "LAB"
        attributes = dict(metadata.get("attributes") or {})
        if len(header_indexes) > 1:
            attributes.update({
                "parallel_activity": True,
                "schedule_track": section_room or f"{source_name} table {header_position + 1}",
            })
        metadata["attributes"] = attributes
        row_records: list[tuple[int, str, str, Sequence[str]]] = []
        slot_order: list[str] = []
        for row_index in range(header_index + 1, next_header):
            row = matrix[row_index]
            time_text = row[time_column] if time_column < len(row) else ""
            start_time, end_time = parse_time_range(time_text)
            if not start_time or not end_time or end_time <= start_time:
                continue
            start_text, end_text = time_to_string(start_time), time_to_string(end_time)
            slot = f"{start_text}-{end_text}"
            if slot not in slot_order:
                slot_order.append(slot)
            row_records.append((row_index, start_text or "", end_text or "", row))

        source_metadata = {
            **metadata,
            "column_order": [day for _, day in day_columns],
            "time_slot_order": slot_order,
            "matrix_source": source_name,
        }
        for row_index, start_text, end_text, row in row_records:
            for column_index, day in day_columns:
                raw_text = row[column_index] if column_index < len(row) else ""
                if is_blank_cell(raw_text):
                    continue
                cells.append(
                    ParsedCell(
                        raw_cell_text=raw_text,
                        class_name=metadata.get("class_name"),
                        division=metadata.get("division"),
                        day=day,
                        start_time_text=start_text,
                        end_time_text=end_text,
                        source_page=source_page,
                        source_sheet=source_name,
                        source_row=row_index + 1,
                        source_column=day,
                        source_cell_reference=f"{source_name}!row:{row_index + 1}:column:{column_index + 1}",
                        extraction_method=extraction_method,
                        parser_name="MatrixTimetableParser",
                        template_name="DETECTED_MATRIX_V1",
                        trace=[
                            {"decision": "detected_matrix_header", "row": header_index + 1},
                            {"decision": "matrix_cell", "row": row_index + 1, "column": column_index + 1},
                        ],
                        metadata=source_metadata,
                    )
                )
    return cells


def _matrix_value(value: object) -> str:
    if value is None:
        return ""
    text = str(value).replace("\r\n", "\n").replace("\r", "\n")
    return normalize_space(re.sub(r"\n+", " / ", text))


def _metadata_key(value: str) -> str:
    return normalize_space(value).lower().rstrip(":")


def _labeled_matrix_metadata(rows: Sequence[Sequence[str]]) -> dict:
    metadata: dict[str, str | None] = {}
    for row in rows:
        for index, value in enumerate(row):
            target = MATRIX_METADATA_LABELS.get(_metadata_key(value))
            if not target:
                continue
            candidate = None
            for item in row[index + 1:]:
                normalized = normalize_space(item)
                if not normalized:
                    continue
                if _metadata_key(normalized) in MATRIX_METADATA_LABELS:
                    break
                candidate = normalized
                break
            # Keep explicit blanks so heuristic metadata cannot consume the next label's value.
            metadata[target] = candidate
    if metadata.get("class_name"):
        metadata["program_name"] = metadata["class_name"]
    return metadata


def _section_lab_hint(rows: Sequence[Sequence[str]]) -> str | None:
    for row in reversed(rows):
        values = [normalize_space(value) for value in row if normalize_space(value)]
        if len(values) != 1:
            continue
        match = re.search(r"\(([^()]*(?:lab|laboratory))\)", values[0], re.I)
        if match:
            return normalize_space(match.group(1))
    return None
