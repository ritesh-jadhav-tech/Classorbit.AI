import re
from datetime import date, datetime, time


DAY_ALIASES = {
    "mon": "Monday",
    "monday": "Monday",
    "tue": "Tuesday",
    "tues": "Tuesday",
    "tuesday": "Tuesday",
    "wed": "Wednesday",
    "wednesday": "Wednesday",
    "thu": "Thursday",
    "thur": "Thursday",
    "thurs": "Thursday",
    "thursday": "Thursday",
    "fri": "Friday",
    "friday": "Friday",
    "sat": "Saturday",
    "saturday": "Saturday",
    "sun": "Sunday",
    "sunday": "Sunday",
}

TIME_RE = re.compile(r"(?P<hour>\d{1,2})[.:](?P<minute>\d{2})(?:\s*(?P<suffix>a\.?m\.?|p\.?m\.?))?", re.I)


def normalize_day(value: str | None) -> str | None:
    if not value:
        return None
    key = value.strip().lower().rstrip(".")
    return DAY_ALIASES.get(key)


def day_from_date(value: date) -> str:
    return value.strftime("%A")


def parse_time_value(value: str | time | None, *, assume_academic_day: bool = True) -> time | None:
    if isinstance(value, time):
        return value
    if not value:
        return None
    match = TIME_RE.search(str(value).strip())
    if not match:
        return None
    hour = int(match.group("hour"))
    minute = int(match.group("minute"))
    suffix = (match.group("suffix") or "").lower().replace(".", "")
    if suffix == "pm" and hour != 12:
        hour += 12
    elif suffix == "am" and hour == 12:
        hour = 0
    elif not suffix and assume_academic_day and 1 <= hour <= 6:
        hour += 12
    if not 0 <= hour <= 23 or not 0 <= minute <= 59:
        return None
    return time(hour=hour, minute=minute)


def parse_time_range(
    value: str | None,
    *,
    start_value: str | time | None = None,
    end_value: str | time | None = None,
) -> tuple[time | None, time | None]:
    start = parse_time_value(start_value)
    end = parse_time_value(end_value)
    if start and end:
        return start, end
    if not value:
        return start, end
    matches = list(TIME_RE.finditer(value))
    if len(matches) >= 2:
        return parse_time_value(matches[0].group(0)), parse_time_value(matches[1].group(0))
    return start, end


def time_to_string(value: time | None) -> str | None:
    if value is None:
        return None
    return value.strftime("%H:%M")


def parse_date(value: str | date | None) -> date | None:
    if isinstance(value, date):
        return value
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(str(value), fmt).date()
        except ValueError:
            continue
    return None


def overlaps(start_a: time, end_a: time, start_b: time, end_b: time) -> bool:
    return start_a < end_b and start_b < end_a
