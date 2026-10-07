from pathlib import Path

from app.parsers.base import BaseTimetableParser
from app.parsers.csv_parser import CsvTimetableParser
from app.parsers.excel_parser import ExcelTimetableParser
from app.parsers.image_parser import ImageTimetableParser
from app.parsers.pdf_parser import PdfTimetableParser
from app.parsers.standard_excel_parser import StandardExcelTimetableParser
from app.parsers.word_parser import WordTimetableParser


PARSERS: tuple[BaseTimetableParser, ...] = (
    PdfTimetableParser(),
    ImageTimetableParser(),
    WordTimetableParser(),
    ExcelTimetableParser(),
    CsvTimetableParser(),
)


def get_parser_for_file(source_path: Path) -> BaseTimetableParser:
    suffix = source_path.suffix.lower()
    if suffix in StandardExcelTimetableParser.supported_extensions and StandardExcelTimetableParser.matches(source_path):
        return StandardExcelTimetableParser()
    for parser in PARSERS:
        if suffix in parser.supported_extensions:
            return parser
    supported = ", ".join(extension for parser in PARSERS for extension in parser.supported_extensions)
    raise ValueError(f"Unsupported timetable file type '{suffix}'. Supported types: {supported}")
