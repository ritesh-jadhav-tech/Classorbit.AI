from pathlib import Path

from app.parsers.base import ParsedDocument
from app.parsers.matrix_parser import cells_from_matrix


class WordTimetableParser:
    supported_extensions = (".docx",)

    def parse(self, source_path: Path) -> ParsedDocument:
        try:
            from docx import Document
            from docx.table import Table
            from docx.text.paragraph import Paragraph
        except ImportError as exc:
            raise RuntimeError("Word import requires python-docx.") from exc

        document = Document(source_path)
        cells = []
        context: list[str] = []
        table_index = 0
        for child in document.element.body.iterchildren():
            if child.tag.endswith("}p"):
                text = Paragraph(child, document).text.strip()
                if text:
                    context.append(text)
                continue
            if not child.tag.endswith("}tbl"):
                continue
            table_index += 1
            table = Table(child, document)
            rows = [[cell.text for cell in row.cells] for row in table.rows]
            cells.extend(
                cells_from_matrix(
                    rows,
                    source_name=f"table:{table_index}",
                    extraction_method="DOCX_TABLE",
                    source_page=table_index,
                    context_prefix=" ".join(context),
                )
            )
            context = []
        return ParsedDocument(
            source_path=source_path,
            source_type="DOCX",
            page_count=table_index,
            cells=cells,
            warnings=[] if cells else ["No timetable-like Word table was detected."],
            parser_name=self.__class__.__name__,
            template_name="DETECTED_MATRIX_V1",
            pages_extracted=len({cell.source_page for cell in cells if cell.source_page}),
            trace={"strategy": "DETECTED_MATRIX_V1", "tables": table_index},
        )
