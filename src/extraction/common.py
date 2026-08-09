from __future__ import annotations

import re
from typing import Iterable

from src.parsing.normalization import clean_text, compact_spaces


def iter_lines(text: str) -> Iterable[str]:
    for line in clean_text(text).splitlines():
        line = compact_spaces(line)
        if line:
            yield line


def find_field(text: str, labels: list[str]) -> str | None:
    lines = list(iter_lines(text))
    for label in sorted(labels, key=len, reverse=True):
        pattern = re.compile(rf"(?i)^\s*{re.escape(label)}\s*:?\s*(.+?)\s*$")
        for line in lines:
            match = pattern.match(line)
            if match:
                return compact_spaces(match.group(1))
    return None


def regex_first(text: str, patterns: list[str], flags: int = re.I | re.S) -> str | None:
    for pattern in patterns:
        match = re.search(pattern, text, flags)
        if match:
            return compact_spaces(match.group(1))
    return None

