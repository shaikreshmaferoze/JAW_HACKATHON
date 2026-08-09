from __future__ import annotations

from datetime import date, datetime

_DATE_FORMATS = [
    "%d %B %Y",
    "%d %b %Y",
    "%B %d, %Y",
    "%b %d, %Y",
    "%Y-%m-%d",
    "%d/%m/%Y",
    "%d-%m-%Y",
    "%d.%m.%Y",
]


def parse_date(text: object) -> str | None:
    if text is None:
        return None
    if isinstance(text, datetime):
        return text.date().isoformat()
    if isinstance(text, date):
        return text.isoformat()
    raw = str(text).strip().replace(",", ", ")
    raw = " ".join(raw.split())
    if not raw or raw.upper() == "N/A":
        return None
    raw = raw.replace("Sept ", "Sep ")
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(raw, fmt).date().isoformat()
        except ValueError:
            pass
    return None


def days_between(date1: object, date2: object) -> int:
    """Elapsed days from date1 to date2, excluding the start day."""
    d1 = parse_date(date1)
    d2 = parse_date(date2)
    if not d1 or not d2:
        raise ValueError(f"cannot parse date pair: {date1!r}, {date2!r}")
    a = datetime.strptime(d1, "%Y-%m-%d").date()
    b = datetime.strptime(d2, "%Y-%m-%d").date()
    return (b - a).days

