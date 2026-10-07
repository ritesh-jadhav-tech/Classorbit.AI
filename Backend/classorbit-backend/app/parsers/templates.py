from dataclasses import dataclass


@dataclass(frozen=True)
class TimetableLayoutTemplate:
    """Generic constraints for detecting a timetable from page evidence."""

    name: str = "DETECTED_GRID_V2"
    minimum_day_columns: int = 2
    header_y_tolerance: int = 28
    boundary_snap_ratio: float = 0.32


DETECTED_GRID = TimetableLayoutTemplate()


def detect_template(_: str = "") -> TimetableLayoutTemplate:
    """Return the generic detector; source class names never select geometry."""

    return DETECTED_GRID
