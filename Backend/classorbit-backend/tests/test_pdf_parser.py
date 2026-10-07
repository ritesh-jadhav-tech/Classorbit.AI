from app.parsers.pdf_parser import OcrWord, PdfTimetableParser
from app.parsers.templates import detect_template
from app.services.timetable_normalizer import TimetableNormalizer
from app.models.enums import ConfidenceLevel, ValidationStatus
from app.parsers.base import ParsedCell, ParsedDocument
from app.services.extraction_quality import ExtractionQualityAnalyzer
from pathlib import Path


def test_department_metadata_keeps_program_variant() -> None:
    metadata = PdfTimetableParser()._detect_metadata(
        "Time Table 2026-2027 Class: SYBA Department: Marathi (Non-Grant) Revised and Updated"
    )

    assert metadata["class_name"] == "SYBA"
    assert metadata["department_name"] == "Marathi"
    assert metadata["program_name"] == "Marathi (Non-Grant)"


def test_hall_metadata_is_inherited_as_room_hint() -> None:
    metadata = PdfTimetableParser()._detect_metadata(
        "Time Table 2026-2027 Class: FYBSc Div. B Hall No.: 305"
    )

    assert metadata["class_name"] == "FYBSc"
    assert metadata["division"] == "B"
    assert metadata["hall_name"] == "305"
    assert metadata["room_hint"] == "305"


def test_document_class_does_not_select_layout_strategy() -> None:
    names = {
        detect_template("Class: FYBA Monday Tuesday").name,
        detect_template("Class: New Programme Monday Tuesday").name,
        detect_template("Class: TYBA Department: Marathi Monday Tuesday").name,
    }

    assert names == {"DETECTED_GRID_V2"}


def test_metadata_accepts_unseen_class_and_multi_character_division() -> None:
    metadata = PdfTimetableParser()._detect_metadata(
        "Time Table 2026-2027 Class: New Integrated Programme Div. Alpha-2 Hall No.: LAB-305 Time Monday"
    )

    assert metadata["class_name"] == "New Integrated Programme"
    assert metadata["division"] == "Alpha-2"
    assert metadata["room_hint"] == "LAB-305"


def test_positioned_page_header_keeps_each_division_separate() -> None:
    words = [
        OcrWord("Class:", 100, 100, 60, 12, 95),
        OcrWord("FYBA", 170, 100, 50, 12, 95),
        OcrWord("Div:", 600, 100, 45, 12, 95),
        OcrWord("Alpha-2", 655, 100, 70, 12, 95),
        OcrWord("Revised", 450, 145, 70, 12, 95),
    ]

    metadata = PdfTimetableParser._positioned_header_metadata(words)

    assert metadata == {"class_name": "FYBA", "division": "Alpha-2"}


def test_detected_headers_preserve_an_extra_source_column() -> None:
    words = [
        OcrWord(label, 100 + index * 100, 100, 60, 12, 95)
        for index, label in enumerate(("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Workshop"))
    ]

    headers = PdfTimetableParser()._detected_column_headers(words, detect_template())

    assert [label for _, label in headers] == [
        "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Workshop"
    ]


def test_printed_noon_times_are_not_interpreted_as_midnight() -> None:
    words = [
        OcrWord("11.15", 5, 100, 30, 10, 95),
        OcrWord("12.15", 5, 130, 30, 10, 95),
        OcrWord("12.15", 5, 170, 30, 10, 95),
        OcrWord("1.15", 5, 200, 30, 10, 95),
    ]

    rows = PdfTimetableParser()._time_rows_from_words(words, 0, 50)

    assert [(row[2], row[3]) for row in rows] == [("11:15", "12:15"), ("12:15", "13:15")]


def test_short_pt_ocr_variant_is_corrected() -> None:
    parser = PdfTimetableParser()

    assert parser._normalize_short_activity_ocr("PG") == "P.T."
    assert parser._normalize_short_activity_ocr("PI.") == "P.T."
    assert parser._normalize_short_activity_ocr("Political Science") == "Political Science"


def test_cell_lines_split_subject_room_pairs() -> None:
    value = PdfTimetableParser._combine_cell_lines(
        ["Minor", "Marathi 701", "Political Sci. 419", "Psychology", "(In Department)"]
    )

    assert value == "Marathi 701 / Political Sci. 419 / Psychology (In Department)"


def test_attached_numeric_room_is_separated_from_subject() -> None:
    subject, room, *_ = TimetableNormalizer()._parse_entry_text("History-702")

    assert subject == "History"
    assert room == "702"


def test_category_room_and_confidence_are_structured() -> None:
    document = ParsedDocument(
        source_path=Path("sample.pdf"),
        source_type="PDF",
        page_count=1,
        pages_extracted=1,
        parser_name="PdfTimetableParser",
        template_name="MODERN_COLLEGE_SIX_DAY_V1",
        metadata={"class_name": "TYBA", "academic_year": "2026-2027"},
        cells=[
            ParsedCell(
                raw_cell_text="Economics Major 428",
                class_name="TYBA",
                day="Wednesday",
                start_time_text="08:15",
                end_time_text="09:15",
                parser_name="PdfTimetableParser",
                template_name="MODERN_COLLEGE_SIX_DAY_V1",
                extraction_method="PDF_COORDINATES",
            )
        ],
    )

    report = ExtractionQualityAnalyzer().analyze(document)

    assert report["valid"] == 1
    assert report["high_confidence"] == 1
    assert report["preview"][0]["subject"] == "Economics"
    assert report["preview"][0]["room"] == "428"
    assert report["preview"][0]["subject_type"] == "MAJOR"


def test_department_is_subject_for_category_only_major_cell() -> None:
    cell = ParsedCell(
        raw_cell_text="Major 103",
        class_name="TYBA",
        day="Monday",
        start_time_text="07:15",
        end_time_text="08:15",
        metadata={"department_name": "Marathi"},
    )

    entry = TimetableNormalizer().normalize_cell(cell, {})[0]

    assert entry.subject_text == "Marathi"
    assert entry.subject_type == "MAJOR"
    assert entry.room_hint == "103"


def test_classroom_only_fragment_is_invalid() -> None:
    normalizer = TimetableNormalizer()
    document = ParsedDocument(
        source_path=Path("sample.csv"),
        source_type="CSV",
        metadata={"class_name": "FYBA"},
        cells=[
            ParsedCell(
                raw_cell_text="428",
                class_name="FYBA",
                day="Monday",
                start_time_text="08:15",
                end_time_text="09:15",
            )
        ],
    )
    entry = normalizer.normalize_cell(document.cells[0], document.metadata)[0]
    from app.services.timetable_validator import TimetableValidator

    entry = TimetableValidator().validate(entry)
    assert entry.validation_status == ValidationStatus.INVALID
