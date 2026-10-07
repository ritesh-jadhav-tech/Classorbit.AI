from pathlib import Path

from app.parsers.base import ParsedCell, ParsedDocument
from app.parsers.csv_parser import first_value, structured_metadata
from app.parsers.matrix_parser import cells_from_matrix
from app.utils.text_normalization import normalize_space


class ExcelTimetableParser:
    supported_extensions = (".xlsx", ".xls", ".xlsm")

    def parse(self, source_path: Path) -> ParsedDocument:
        try:
            import pandas as pd
        except ImportError as exc:
            raise RuntimeError("Excel import requires pandas, openpyxl, and xlrd.") from exc

        workbook = pd.read_excel(source_path, sheet_name=None, header=None, dtype=str)
        cells: list[ParsedCell] = []
        authoritative_timetable = False
        for sheet_number, (sheet_name, frame) in enumerate(workbook.items(), start=1):
            matrix = frame.fillna("").values.tolist()
            authoritative_timetable = authoritative_timetable or any(
                normalize_space(str(value)).upper() == "CLASSORBIT TIMETABLE TEMPLATE"
                for row in matrix[:10]
                for value in row
            )
            header_index = self._structured_header_index(matrix)
            if header_index is not None:
                cells.extend(self._structured_cells(matrix, header_index, sheet_name, sheet_number))
                continue
            matrix_cells = cells_from_matrix(
                matrix,
                source_name=sheet_name,
                extraction_method="EXCEL_GRID",
                source_page=sheet_number,
            )
            for cell in matrix_cells:
                cell.parser_name = self.__class__.__name__
            cells.extend(matrix_cells)
        return ParsedDocument(
            source_path=source_path,
            source_type="EXCEL",
            cells=cells,
            page_count=len(workbook),
            metadata={
                "authoritative_timetable": authoritative_timetable,
                "source_sheets": list(workbook),
            },
            warnings=[] if cells else ["No structured rows or timetable grid were detected in the workbook."],
            parser_name=self.__class__.__name__,
            template_name="AUTO_EXCEL_V2",
            pages_extracted=len({cell.source_page for cell in cells if cell.source_page}),
            trace={"strategy": "AUTO_EXCEL_V2", "sheets": list(workbook)},
        )

    @staticmethod
    def _structured_header_index(matrix: list[list[object]]) -> int | None:
        for index, row in enumerate(matrix[:30]):
            headers = {normalize_space(str(value)).lower().replace(" ", "_") for value in row}
            has_day = bool(headers & {"day", "day_of_week"})
            has_subject = bool(headers & {"subject", "entry", "raw_cell_text", "raw_text"})
            has_time = bool(headers & {"time", "time_slot", "start_time", "start"})
            if has_day and has_subject and has_time:
                return index
        return None

    def _structured_cells(
        self,
        matrix: list[list[object]],
        header_index: int,
        sheet_name: str,
        sheet_number: int,
    ) -> list[ParsedCell]:
        headers = [normalize_space(str(value)).lower().replace(" ", "_") for value in matrix[header_index]]
        cells: list[ParsedCell] = []
        for row_index, row in enumerate(matrix[header_index + 1 :], start=header_index + 2):
            normalized = {
                header: normalize_space(str(row[index]))
                for index, header in enumerate(headers)
                if header and index < len(row) and normalize_space(str(row[index]))
            }
            raw_cell_text = first_value(normalized, "raw_cell_text", "raw_text", "entry", "cell", "subject", default="")
            if not raw_cell_text:
                continue
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
                    source_page=sheet_number,
                    source_row=row_index,
                    source_column=sheet_name,
                    source_cell_reference=f"{sheet_name}!row:{row_index}",
                    extraction_method="EXCEL_STRUCTURED",
                    parser_name=self.__class__.__name__,
                    template_name="STRUCTURED_ROWS_V1",
                    trace=[{"decision": "named_columns", "sheet": sheet_name, "row": row_index}],
                    metadata={**metadata, "sheet": sheet_name, "row": normalized},
                )
            )
        return cells
