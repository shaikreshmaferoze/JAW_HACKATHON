from __future__ import annotations

import re
import unicodedata


def clean_text(text: object) -> str:
    if text is None:
        return ""
    value = str(text)
    value = value.replace("\x00", "")
    value = value.replace("\u2013", "-").replace("\u2014", "-")
    value = value.replace("\u2018", "'").replace("\u2019", "'")
    value = value.replace("\u201c", '"').replace("\u201d", '"')
    value = value.replace("\u00a0", " ")
    value = "".join(ch if ch in "\n\t" or ord(ch) >= 32 else " " for ch in value)
    value = unicodedata.normalize("NFKC", value)
    value = re.sub(r"[ \t]+", " ", value)
    value = re.sub(r"\n{3,}", "\n\n", value)
    return value.strip()


def compact_spaces(text: object) -> str:
    return re.sub(r"\s+", " ", clean_text(text)).strip()


def normalize_key(text: object) -> str:
    value = clean_text(text).lower()
    value = value.replace("&", " and ")
    value = re.sub(r"\bgovt\b", "government", value)
    value = re.sub(r"\bdept\b", "department", value)
    value = re.sub(r"\bpkg\b", "package", value)
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def normalize_client(text: object) -> str:
    value = compact_spaces(text)
    value = re.sub(r"\s*\((government|private|psu)\)\s*$", "", value, flags=re.I)
    return compact_spaces(value)


def normalize_project(text: object) -> str:
    return normalize_key(text)


def extract_package_id(text: object) -> str | None:
    value = clean_text(text)
    match = re.search(r"(?i)\b(?:pkg|package)\s*-?\s*(\d{1,4})\b", value)
    if match:
        return f"Pkg-{int(match.group(1))}"
    return None


def package_number(package_id: str | None) -> int | None:
    if not package_id:
        return None
    match = re.search(r"\d+", package_id)
    return int(match.group(0)) if match else None


def normalize_category(text: object) -> str:
    value = normalize_key(text)
    aliases = {
        "bridges flyovers": "bridges flyovers",
        "large bridges": "large bridges",
        "expressways": "expressways",
        "roads highways": "roads highways",
        "roads maintenance": "roads maintenance",
        "road maintenance": "roads maintenance",
        "buildings": "buildings",
        "small buildings": "small buildings",
        "water treatment": "water treatment",
        "water supply": "water supply",
        "sewerage drainage": "sewerage drainage",
        "drainage": "sewerage drainage",
        "irrigation": "irrigation",
        "tunnels": "tunnels",
        "industrial epc": "industrial epc",
        "power distribution": "power distribution",
    }
    return aliases.get(value, value)

