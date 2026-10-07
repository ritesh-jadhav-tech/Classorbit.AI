import re


WHITESPACE_RE = re.compile(r"\s+")
ROOM_OR_LOCATION_ANCHOR_RE = re.compile(
    r"(?:"
    r"\b(?:CC|AB|GE)\s*[- ]?\s*\d{1,2}\b"
    r"|\b\d{3,4}[A-Z]?\b"
    r"|\((?:in\s+)?(?:[^()]{0,50}\s+)?lab(?:oratory)?\)"
    r"|\((?:in\s+)?(?:[^()]{1,50}\s+)?department\)"
    r"|\((?:online|online\s+course)\)"
    r")",
    re.I,
)
CATEGORY_PREFIX_RE = re.compile(
    r"^(?P<prefix>(?:Sem(?:ester)?\s+[IVX0-9]+\s+)?(?:Major|Minor|AEC|SEC|VSC|GE|OE)\s+)",
    re.I,
)
STANDALONE_CATEGORY_RE = re.compile(
    r"^[\s().,-]*(?:major(?:\s+core\s+paper)?|minor|mooc(?:\s+course)?|macro|"
    r"vsc|sec|aec|ge|oe)[\s().,-]*$",
    re.I,
)
FACULTY_FRAGMENT_RE = re.compile(
    r"^(?:(?:faculty|teacher|professor|instructor)\s*[:\-]|(?:prof(?:essor)?|dr|mr|mrs|ms)\.?)",
    re.I,
)


def normalize_space(value: str | None) -> str:
    if value is None:
        return ""
    return WHITESPACE_RE.sub(" ", value.replace("\u00a0", " ")).strip()


def is_blank_cell(value: str | None) -> bool:
    text = normalize_space(value)
    return not text or text in {"-", "--", "—", "NA", "N/A"}


def split_cell_entries(raw_cell_text: str) -> list[str]:
    text = raw_cell_text.replace("\r\n", "\n").replace("\r", "\n")
    text = normalize_space(re.sub(r"\n+", " / ", text))
    if is_blank_cell(text):
        return []
    text = re.sub(r"\s*/\s*", "/", text)
    parts = _coalesce_wrapped_parts([normalize_space(part) for part in text.split("/")])
    entries: list[str] = []
    for part in parts:
        if is_blank_cell(part):
            continue
        entries.extend(_split_compound_entry(part))
    return entries


def _coalesce_wrapped_parts(parts: list[str]) -> list[str]:
    """Join visual line wraps until a room/location marker completes the activity."""
    combined: list[str] = []
    pending: list[str] = []
    for part in parts:
        if is_blank_cell(part):
            continue
        if STANDALONE_CATEGORY_RE.fullmatch(part) or FACULTY_FRAGMENT_RE.match(part):
            combined.extend(pending)
            pending = []
            combined.append(part)
            continue
        if ROOM_OR_LOCATION_ANCHOR_RE.search(part):
            combined.append(normalize_space(" ".join([*pending, part])))
            pending = []
            continue
        pending.append(part)
    combined.extend(pending)
    return combined


def _split_compound_entry(value: str) -> list[str]:
    anchors = list(ROOM_OR_LOCATION_ANCHOR_RE.finditer(value))
    if len(anchors) < 2:
        return [value]
    prefix_match = CATEGORY_PREFIX_RE.match(value)
    shared_prefix = prefix_match.group("prefix") if prefix_match else ""
    entries: list[str] = []
    start = 0
    for anchor in anchors:
        candidate = normalize_space(value[start:anchor.end()])
        start = anchor.end()
        if not candidate:
            continue
        if entries and shared_prefix and not CATEGORY_PREFIX_RE.match(candidate):
            candidate = normalize_space(f"{shared_prefix}{candidate}")
        entries.append(candidate)
    remainder = normalize_space(value[start:])
    if remainder:
        entries.append(normalize_space(f"{shared_prefix}{remainder}") if shared_prefix else remainder)
    return entries or [value]


def normalize_room_hint(value: str | None) -> str | None:
    text = normalize_space(value)
    if not text:
        return None
    normalized = text.upper()
    numbered_room = re.fullmatch(r"(?:CLASSROOM|ROOM)\s*[- ]?\s*(\d{1,4}[A-Z]?)", normalized)
    if numbered_room:
        return numbered_room.group(1)
    cc_match = re.fullmatch(r"CC\s*[- ]?\s*(\d{1,2})", normalized)
    if cc_match:
        return f"CC {cc_match.group(1)}"
    ab_match = re.fullmatch(r"AB\s*[- ]?\s*(\d{1,2})", normalized)
    if ab_match:
        return f"AB-{ab_match.group(1)}"
    return re.sub(r"\s*-\s*", "-", normalized)
