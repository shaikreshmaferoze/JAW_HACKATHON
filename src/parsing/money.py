from __future__ import annotations

import re
from decimal import Decimal, ROUND_HALF_UP

CRORE = Decimal("10000000")
LAKH = Decimal("100000")

_MONEY_RE = re.compile(
    r"(?ix)"
    r"(?:rs\.?|inr|rupees|₹)?\s*"
    r"(?P<num>[-+]?\d[\d,]*(?:\.\d+)?)"
    r"\s*(?:/-)?\s*"
    r"(?P<unit>crores?|cr\.?|lakhs?|lacs?)?"
)


def _clean_number(number: str) -> Decimal:
    return Decimal(number.replace(",", "").strip())


def parse_money(text: object) -> int | float | None:
    """Parse Indian money renderings and return rupees.

    The parser intentionally uses Decimal until the final conversion so values
    such as 33.38 Cr and 3,338.00 Lakh round exactly to INR.
    """
    if text is None:
        return None
    raw = str(text).strip()
    if not raw:
        return None

    negative = False
    if raw.startswith("(") and raw.endswith(")"):
        negative = True
        raw = raw[1:-1]

    raw = raw.replace("\u20b9", " INR ")
    raw = raw.replace("\u00a0", " ")
    match = _MONEY_RE.search(raw)
    if not match:
        return None

    value = _clean_number(match.group("num"))
    unit = (match.group("unit") or "").lower().rstrip(".")
    if unit in {"cr", "crore", "crores"}:
        value *= CRORE
    elif unit in {"lakh", "lakhs", "lac", "lacs"}:
        value *= LAKH

    if negative:
        value = -value

    rounded = value.quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return int(rounded)


_SMALL = {
    "zero": 0,
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "thirteen": 13,
    "fourteen": 14,
    "fifteen": 15,
    "sixteen": 16,
    "seventeen": 17,
    "eighteen": 18,
    "nineteen": 19,
}

_TENS = {
    "twenty": 20,
    "thirty": 30,
    "forty": 40,
    "fifty": 50,
    "sixty": 60,
    "seventy": 70,
    "eighty": 80,
    "ninety": 90,
}


def parse_number_words(text: str) -> Decimal | None:
    words = re.findall(r"[a-z]+", text.lower().replace("-", " "))
    if not words:
        return None
    total = Decimal(0)
    current = Decimal(0)
    seen = False
    for word in words:
        if word in _SMALL:
            current += _SMALL[word]
            seen = True
        elif word in _TENS:
            current += _TENS[word]
            seen = True
        elif word == "hundred":
            current = max(current, Decimal(1)) * 100
            seen = True
        elif word == "thousand":
            total += max(current, Decimal(1)) * 1000
            current = Decimal(0)
            seen = True
        else:
            if seen:
                break
    if not seen:
        return None
    return total + current


def parse_money_threshold(text: str) -> int | None:
    """Parse numeric or worded thresholds such as INR 20 Cr or seventy-three crore."""
    parsed = parse_money(text)
    if parsed is not None and re.search(r"(?i)(inr|rs\.?|₹|cr|crore|lakh|lac|\d[\d,]*(?:\.\d+)?)", text):
        return int(parsed)

    match = re.search(
        r"(?i)\b((?:zero|one|two|three|four|five|six|seven|eight|nine|ten|"
        r"eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|"
        r"nineteen|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|"
        r"hundred|thousand|[-\s])+)\s+(crores?|cr|lakhs?|lacs?)\b",
        text,
    )
    if not match:
        return None
    number = parse_number_words(match.group(1))
    if number is None:
        return None
    unit = match.group(2).lower()
    multiplier = CRORE if unit.startswith(("cr", "crore")) else LAKH
    return int((number * multiplier).quantize(Decimal("1"), rounding=ROUND_HALF_UP))

