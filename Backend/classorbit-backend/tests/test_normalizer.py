from app.models.enums import LocationType, ValidationStatus
from app.parsers.base import ParsedCell
from app.services.timetable_normalizer import TimetableNormalizer
from app.services.import_service import ImportService
from app.services.timetable_validator import TimetableValidator


def test_multi_subject_cell_is_split_conservatively() -> None:
    cell = ParsedCell(
        raw_cell_text="English 414 / Marathi 417 / Hindi CC 4 / Geography (In Lab) / Open Elective (Online Course) / -",
        class_name="FYBA",
        division="A",
        day="Mon",
        start_time_text="7:15",
        end_time_text="8:15",
    )

    normalizer = TimetableNormalizer()
    validator = TimetableValidator()
    entries = [validator.validate(entry) for entry in normalizer.normalize_cell(cell, {})]

    assert len(entries) == 5
    assert entries[0].subject_text == "English"
    assert entries[0].room_hint == "414"
    assert entries[1].subject_text == "Marathi"
    assert entries[1].room_hint == "417"
    assert entries[2].subject_text == "Hindi"
    assert entries[2].room_hint == "CC 4"
    assert entries[2].validation_status == ValidationStatus.VALID
    assert entries[3].location_type == LocationType.LAB
    assert entries[4].location_type == LocationType.ONLINE


def test_inline_subject_room_pairs_and_department_labs_are_split() -> None:
    cell = ParsedCell(
        raw_cell_text="Minor Economics 415 Psychology (In Department) Music (In Music Department)",
        class_name="SYBA",
        day="Monday",
        start_time_text="07:15",
        end_time_text="08:15",
        metadata={"department_name": "Performing Arts"},
    )

    entries = TimetableNormalizer().normalize_cell(cell, {})

    assert [(entry.subject_text, entry.room_hint) for entry in entries] == [
        ("Economics", "415"),
        ("Psychology", "PSYCHOLOGY DEPARTMENT LAB"),
        ("Music", "MUSIC DEPARTMENT LAB"),
    ]
    assert entries[1].location_type == LocationType.LAB
    assert entries[1].attributes_json["location_department"] == "Psychology"
    assert entries[2].attributes_json["location_department"] == "Music"


def test_annotations_are_not_subjects_and_faculty_is_extracted() -> None:
    cell = ParsedCell(
        raw_cell_text="Economics 417 / (Major Core Paper) / (MOOC Course) / (Macro) / Prof. A. Patil",
        class_name="SYBA",
        day="Monday",
        start_time_text="10:15",
        end_time_text="11:15",
    )

    entries = TimetableNormalizer().normalize_cell(cell, {})

    assert len(entries) == 1
    assert entries[0].subject_text == "Economics"
    assert entries[0].room_hint == "417"
    assert entries[0].faculty_text == "Prof. A. Patil"
    assert entries[0].attributes_json["curriculum_annotations"] == [
        "(Major Core Paper)",
        "(MOOC Course)",
        "(Macro)",
    ]


def test_category_label_applies_to_real_subjects_in_same_cell() -> None:
    cell = ParsedCell(
        raw_cell_text="Minor / English 701 / History 702",
        class_name="SYBA",
        day="Tuesday",
        start_time_text="08:15",
        end_time_text="09:15",
    )

    entries = TimetableNormalizer().normalize_cell(cell, {})

    assert [(entry.subject_text, entry.subject_type) for entry in entries] == [
        ("English", "MINOR"),
        ("History", "MINOR"),
    ]
    assert all(entry.attributes_json["parallel_activity"] for entry in entries)


def test_parallel_options_do_not_report_a_false_room_conflict() -> None:
    cell = ParsedCell(
        raw_cell_text="English 701 / History 701",
        class_name="SYBA",
        day="Tuesday",
        start_time_text="08:15",
        end_time_text="09:15",
    )
    entries = TimetableNormalizer().normalize_cell(cell, {})

    class Room:
        id = "room-701"
        room_number = "701"

    warnings = ImportService._entry_conflict_warnings(
        entries[1], Room(), [(entries[0], Room())], [], []
    )

    assert warnings == []


def test_wrapped_subject_lines_are_reconstructed_before_normalizing() -> None:
    cell = ParsedCell(
        raw_cell_text="Sem III / AEC English / (Grant) 417",
        class_name="SYBA",
        day="Monday",
        start_time_text="11:15",
        end_time_text="12:15",
    )

    entries = TimetableNormalizer().normalize_cell(cell, {})

    assert len(entries) == 1
    assert entries[0].subject_text == "Sem III AEC English (Grant)"
    assert entries[0].room_hint == "417"
