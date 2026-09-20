"""Date parsing, normalization and duration calculation for resumes.

Deterministic only. Never invents dates: unparseable input yields ``None``;
year-only values are returned as ``"YYYY"`` with ``uncertain=True``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

MONTHS: dict[str, int] = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}
_MONTH_ALT = "|".join(MONTHS)

PRESENT_WORDS = r"(?:present|current|now|till\s*date|to\s*date|ongoing|date)"

# "Jan 2020", "January 2020", "Sept 2020", "Jan. 2020", "Jan, 2020"
MONTH_YEAR_RE = re.compile(
    rf"\b({_MONTH_ALT})[a-z]*\.?,?\s*(\d{{4}})\b", re.IGNORECASE
)
# Non-capturing fragment used inside composite range patterns.
MONTH_YEAR_FRAGMENT = rf"\b(?:{_MONTH_ALT})[a-z]*\.?,?\s*\d{{4}}\b"
# "01/2020", "1/2020"
NUMERIC_MONTH_YEAR_RE = re.compile(r"\b(\d{1,2})/(\d{4})\b")
# bare year
YEAR_RE = re.compile(r"\b((?:19|20)\d{2})\b")

SEPARATOR = r"\s*(?:-|–|—|—|to|until|through|thru)\s*"

RANGE_PATTERNS: list[re.Pattern[str]] = [
    # Month Year - Month Year / Present
    re.compile(
        rf"({MONTH_YEAR_FRAGMENT}){SEPARATOR}({MONTH_YEAR_FRAGMENT}|{PRESENT_WORDS})",
        re.IGNORECASE,
    ),
    # MM/YYYY - MM/YYYY / Present
    re.compile(
        rf"(\d{{1,2}}/\d{{4}}){SEPARATOR}(\d{{1,2}}/\d{{4}}|{PRESENT_WORDS})", re.IGNORECASE
    ),
    # Month Year - YYYY (mixed)
    re.compile(rf"({MONTH_YEAR_FRAGMENT}){SEPARATOR}((?:19|20)\d{{2}}|{PRESENT_WORDS})", re.IGNORECASE),
    # YYYY - YYYY / Present
    re.compile(rf"(\b(?:19|20)\d{{2}}\b){SEPARATOR}(\b(?:19|20)\d{{2}}\b|{PRESENT_WORDS})", re.IGNORECASE),
]


@dataclass
class DateValue:
    """A parsed resume date.

    ``iso`` is ``YYYY-MM`` for month precision or ``YYYY`` when only the year
    was present (``year_only=True``, ``uncertain=True``).
    """

    iso: str | None = None
    original: str | None = None
    year_only: bool = False
    uncertain: bool = False

    @property
    def year(self) -> int | None:
        if not self.iso:
            return None
        return int(self.iso[:4])

    @property
    def month(self) -> int | None:
        if not self.iso or len(self.iso) < 7:
            return None
        return int(self.iso[5:7])


def _clean_fragment(fragment: str) -> tuple[int, int] | None:
    """Return (year, month) from a raw date fragment, or None."""
    fragment = fragment.strip().strip(",;").strip()
    m = MONTH_YEAR_RE.search(fragment)
    if m:
        month = MONTHS.get(m.group(1)[:3].lower())
        if month:
            return int(m.group(2)), month
    m = NUMERIC_MONTH_YEAR_RE.search(fragment)
    if m:
        month = int(m.group(1))
        if 1 <= month <= 12:
            return int(m.group(2)), month
    m = YEAR_RE.fullmatch(fragment)
    if m:
        return int(m.group(1)), 0  # month 0 => year-only
    return None


def parse_single_date(text: str) -> DateValue | None:
    """Parse the first recognizable date in *text*."""
    text = (text or "").strip()
    if not text:
        return None
    m = MONTH_YEAR_RE.search(text)
    if m:
        month = MONTHS.get(m.group(1)[:3].lower())
        if month:
            return DateValue(iso=f"{m.group(2)}-{month:02d}", original=m.group(0))
    m = NUMERIC_MONTH_YEAR_RE.search(text)
    if m:
        month = int(m.group(1))
        if 1 <= month <= 12:
            return DateValue(iso=f"{m.group(2)}-{month:02d}", original=m.group(0))
    m = YEAR_RE.search(text)
    if m:
        return DateValue(iso=m.group(1), original=m.group(0), year_only=True, uncertain=True)
    return None


def parse_date_range(text: str) -> tuple[DateValue | None, DateValue | None, bool]:
    """Parse a date range from *text*.

    Returns ``(start, end, is_current)``. ``end`` is ``None`` when the range is
    open-ended (e.g. "Present"). Returns ``(None, None, False)`` if nothing
    parses.
    """
    text = (text or "").strip()
    if not text:
        return None, None, False

    for pattern in RANGE_PATTERNS:
        m = pattern.search(text)
        if not m:
            continue
        start_raw, end_raw = m.group(1), m.group(2)

        is_current = bool(re.fullmatch(PRESENT_WORDS, end_raw.strip(), re.IGNORECASE))
        start_val: DateValue | None = None
        end_val: DateValue | None = None

        start_parts = _clean_fragment(start_raw)
        if start_parts:
            year, month = start_parts
            start_val = (
                DateValue(iso=str(year), original=start_raw.strip(), year_only=True, uncertain=True)
                if month == 0
                else DateValue(iso=f"{year}-{month:02d}", original=start_raw.strip())
            )

        if not is_current:
            end_parts = _clean_fragment(end_raw)
            if end_parts:
                year, month = end_parts
                end_val = (
                    DateValue(iso=str(year), original=end_raw.strip(), year_only=True, uncertain=True)
                    if month == 0
                    else DateValue(iso=f"{year}-{month:02d}", original=end_raw.strip())
                )
        elif start_val is not None:
            return start_val, None, True

        if start_val is not None or end_val is not None:
            return start_val, end_val, is_current

    # Fallback: two loose dates in the line ("2018 to 2022" handled above; this
    # catches e.g. "May 2019 December 2020" without separators).
    singles = [
        (mm.start(), parse_single_date(text[max(0, mm.start() - 20): mm.end() + 10]))
        for mm in RANGE_PATTERNS[-1].finditer(text)
    ]
    found = [dv for _, dv in singles if dv]
    if len(found) >= 2:
        return found[0], found[-1], False
    if len(found) == 1:
        return found[0], None, False
    return None, None, False


def looks_like_date_range_line(line: str) -> bool:
    """Heuristic: is this short line primarily a date range?"""
    stripped = (line or "").strip()
    if not stripped or len(stripped) > 70:
        return False
    start, end, _ = parse_date_range(stripped)
    if start is None and end is None:
        return False
    # The non-date residue should be tiny (parentheses, whitespace, dashes).
    residue = re.sub(
        rf"{MONTH_YEAR_RE.pattern}|\d{{1,2}}/\d{{4}}|\b(?:19|20)\d{{2}}\b|{PRESENT_WORDS}|-|–|—|to|[(),\s]",
        "",
        stripped,
        flags=re.IGNORECASE,
    )
    return len(residue) <= 3


def compute_duration_months(
    start: DateValue | None,
    end: DateValue | None,
    is_current: bool,
    today: date | None = None,
) -> int | None:
    """Total months between two parsed dates. ``None`` when not computable."""
    if start is None or start.year is None:
        return None
    today = today or date.today()
    start_y, start_m = start.year, start.month or 1

    if is_current:
        end_y, end_m = today.year, today.month
    else:
        if end is None or end.year is None:
            return None
        end_y, end_m = end.year, end.month or 1

    total = (end_y - start_y) * 12 + (end_m - start_m)
    return max(total, 0)


def format_duration(months: int | None) -> str | None:
    """Human label: ``24 -> "2 years"``, ``18 -> "1 year 6 months"``."""
    if months is None or months < 0:
        return None
    if months == 0:
        return "Less than a month"
    years, rem = divmod(months, 12)
    parts: list[str] = []
    if years > 0:
        parts.append(f"{years} year{'s' if years != 1 else ''}")
    if rem > 0:
        parts.append(f"{rem} month{'s' if rem != 1 else ''}")
    return " ".join(parts) if parts else "Less than a month"
