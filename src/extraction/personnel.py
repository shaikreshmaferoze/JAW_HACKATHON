from __future__ import annotations

import re
from typing import Any

from src.extraction.common import find_field, regex_first
from src.parsing.dates import parse_date
from src.parsing.normalization import clean_text, compact_spaces


def parse_personnel_certificate(doc: dict[str, Any]) -> dict[str, Any] | None:
    text = clean_text(doc.get("text", ""))
    credential_id = find_field(text, ["Credential ID", "Certificate No."]) or regex_first(text, [r"\b([A-Z0-9]{2,6}-\d{5,})\b"])
    if credential_id:
        match = re.search(r"\b([A-Z0-9]{2,6}-\d{5,})\b", credential_id)
        credential_id = match.group(1) if match else credential_id
    credential_type = find_field(text, ["Credential Type"])
    if not credential_type:
        if re.search(r"\bPMP\b", text, re.I):
            credential_type = "PMP"
        elif re.search(r"Six Sigma Black Belt", text, re.I):
            credential_type = "Six Sigma Black Belt"
    issue_date = find_field(text, ["Date of Issue", "Issued"])
    expiry_date = find_field(text, ["Valid Through", "Expiry Date", "Expires"])
    employee_id = regex_first(text, [r"Employee ID:?\s*([A-Z]{2,5}-\d+)"])

    name = None
    match = re.search(r"This is to certify that\s+([A-Za-z ]+?)\s+Employee ID", text, re.I | re.S)
    if match:
        name = compact_spaces(match.group(1))
    if not name:
        match = re.search(r"This credential is conferred upon\s+([A-Za-z ]+?)\s+of National Infrastructure", text, re.I | re.S)
        if match:
            name = compact_spaces(match.group(1))
    if not name:
        lines = [compact_spaces(line) for line in text.splitlines() if compact_spaces(line)]
        for i, line in enumerate(lines):
            if re.search(r"this is to certify that", line, re.I) and i + 1 < len(lines):
                name = lines[i + 1]
                break
    if not name:
        return None
    return {
        "employee_name": name,
        "employee_id": employee_id,
        "credential_type": compact_spaces(credential_type),
        "credential_id": compact_spaces(credential_id),
        "issue_date": parse_date(issue_date),
        "expiry_date": parse_date(expiry_date),
        "role": find_field(text, ["Employment Status"]),
        "source_document_id": doc["doc_id"],
    }


def parse_cv(doc: dict[str, Any]) -> dict[str, Any] | None:
    text = clean_text(doc.get("text", ""))
    match = re.search(r"\bName\s+([A-Za-z ]+?)\s+Employee ID\s+([A-Z]{2,5}-\d+)", text, re.I)
    if not match:
        return None
    return {
        "employee_name": compact_spaces(match.group(1)),
        "employee_id": compact_spaces(match.group(2)),
        "designation": find_field(text, ["Designation"]),
        "source_document_id": doc["doc_id"],
    }
