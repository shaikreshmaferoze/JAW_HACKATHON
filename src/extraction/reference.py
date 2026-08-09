from __future__ import annotations

import re
from typing import Any

from src.extraction.common import find_field, regex_first
from src.parsing.dates import parse_date
from src.parsing.money import parse_money
from src.parsing.normalization import (
    clean_text,
    compact_spaces,
    extract_package_id,
    normalize_category,
    normalize_client,
    normalize_project,
)


def parse_reference_letter(doc: dict[str, Any]) -> dict[str, Any]:
    text = clean_text(doc.get("text", ""))
    project = (
        find_field(text, ["Project Name", "Name of Work", "Work"])
        or regex_first(text, [r"work\s+[\"'](.+?Pkg-\d+)[\"']", r"work\s+(.+?Pkg-\d+)"])
    )
    client = find_field(text, ["Client"])
    if not client:
        lines = [compact_spaces(line) for line in text.splitlines() if compact_spaces(line)]
        for line in lines[:5]:
            if not re.search(r"(?i)(letter|recommendation|reference|whomsoever|national infrastructure)", line):
                client = line
                break
    value_text = find_field(text, ["Contract Value", "Value"])
    if not value_text:
        value_text = regex_first(text, [r"\((INR|Rs\.?|₹)[^)]+?\)", r"(INR\s+[\d,.]+\s*(?:Cr|Crore|Lakh|Lac)?)"])
    completion = find_field(text, ["Date of Completion", "Completion Date"])
    if not completion:
        completion = regex_first(text, [r"completed on\s+([A-Za-z0-9,\-/ ]+?)\."])
    role = find_field(text, ["Contractor's Role", "Contractor Role"])
    category = find_field(text, ["Work Category", "Category", "Nature / Category"])
    return {
        "project_name": compact_spaces(project),
        "normalized_project_name": normalize_project(project),
        "package_id": extract_package_id(project) or extract_package_id(text),
        "client_name": normalize_client(client),
        "category": compact_spaces(category),
        "normalized_category": normalize_category(category),
        "contract_value_inr": parse_money(value_text),
        "completion_date": parse_date(completion),
        "contractor_role": compact_spaces(role),
        "source_document_id": doc["doc_id"],
    }

