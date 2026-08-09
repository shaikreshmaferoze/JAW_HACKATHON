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
    package_number,
)


def parse_company_completion(doc: dict[str, Any]) -> dict[str, Any] | None:
    text = clean_text(doc.get("text", ""))
    project = find_field(text, ["Project Name", "Name of Work", "Work"])
    client = find_field(text, ["Client"])
    category = find_field(text, ["Work Category", "Nature / Category", "Category"])
    value_text = find_field(text, ["Executed Value", "Contract Value", "Contract Value (Original)"])
    completion_text = find_field(text, ["Completion Date", "Completion"])
    lead = find_field(text, ["Project Manager", "Project Lead", "Contractor's Project Manager"])
    cert_ref = find_field(text, ["Client Certificate Ref"])
    grading = regex_first(text, [r"assessed the\s+completed work as\s+([A-Za-z ]+?)(?:\.|\n)"])

    if not project:
        return None
    package_id = extract_package_id(project) or extract_package_id(text)
    project_number = None
    match = re.search(r"(?i)(?:CCC/|NICL/CC/)(\d+)", text)
    if match:
        project_number = int(match.group(1))
    if project_number is None:
        project_number = package_number(package_id)

    return {
        "project_id": f"PRJ-{project_number:03d}" if project_number is not None else None,
        "project_number": project_number,
        "project_name": compact_spaces(project),
        "normalized_project_name": normalize_project(project),
        "package_id": package_id,
        "client_name": normalize_client(client),
        "client_kind": _client_kind(client),
        "category": compact_spaces(category),
        "normalized_category": normalize_category(category),
        "contract_value_inr": parse_money(value_text),
        "completion_date": parse_date(completion_text),
        "project_lead": compact_spaces(lead),
        "client_certificate_ref": compact_spaces(cert_ref),
        "grading": compact_spaces(grading),
        "source_document_id": doc["doc_id"],
        "evidence": [doc["doc_id"], value_text, completion_text, cert_ref],
    }


def parse_client_completion(doc: dict[str, Any]) -> dict[str, Any]:
    text = clean_text(doc.get("text", ""))
    project = (
        find_field(text, ["Project Name", "Name of Work", "Work"])
        or regex_first(text, [r"work of [\"']?(.+?Pkg-\d+)[\"']?\s*\("])
    )
    client = None
    lines = [line for line in text.splitlines() if compact_spaces(line)]
    for line in lines[:8]:
        if not re.search(r"(?i)(national infrastructure|completion|certificate|office of|ref:|dated:|government)", line):
            client = compact_spaces(line)
            break
    category = find_field(text, ["Nature / Category", "Work Category", "Category"])
    if not category:
        category = regex_first(text, [r"Pkg-\d+[\"']?\s*\(([^)]+)\)"])
    value_text = find_field(text, ["Contract Value (Original)", "Contract Value", "Executed Value"])
    if not value_text:
        value_text = regex_first(
            text,
            [
                r"gross\s+executed\s+value\s+of\s+((?:INR|Rs\.?|₹)\s*[\d,]+(?:\.\d+)?\s*(?:/-)?\s*(?:Cr|Crore|Lakh|Lakhs|Lac|Lacs)?)",
                r"contract\s+value\s*(?:\(original\))?\s+((?:INR|Rs\.?|₹)\s*[\d,]+(?:\.\d+)?\s*(?:/-)?\s*(?:Cr|Crore|Lakh|Lakhs|Lac|Lacs)?)",
            ],
        )
    completion_text = find_field(text, ["Completion Date", "Date of Completion", "Completion"])
    if not completion_text:
        completion_text = regex_first(text, [r"completed(?:\s+in\s+all\s+respects)?\s+on\s+(.+?)\s+at\s+a\s+gross"])
    lead = find_field(text, ["Contractor's Project Manager", "Project Manager", "Project Lead"])
    if not lead:
        lead = regex_first(text, [r"supervised on the contractor's side by\s+([A-Za-z ]+?)\."])
    grading = (
        regex_first(text, [r"assessed the\s+completed work as\s+([A-Za-z ]+?)(?:\.|\n)"])
        or regex_first(text, [r"Quality Assessment\s+([A-Za-z ]+?)\s+Parameter"], flags=re.I | re.S)
    )
    cert_no = regex_first(text, [r"(CC/\d+/\d+/\d+)"], flags=re.I)
    project_number_hint = None
    match = re.search(r"(\d+)$", doc["doc_id"])
    if match:
        project_number_hint = int(match.group(1))
    return {
        "project_number_hint": project_number_hint,
        "project_name": compact_spaces(project),
        "normalized_project_name": normalize_project(project),
        "package_id": extract_package_id(project) or extract_package_id(text),
        "client_name": normalize_client(client),
        "category": compact_spaces(category),
        "normalized_category": normalize_category(category),
        "contract_value_inr": parse_money(value_text),
        "completion_date": parse_date(completion_text),
        "project_lead": compact_spaces(lead),
        "certificate_number": compact_spaces(cert_no),
        "grading": compact_spaces(grading),
        "source_document_id": doc["doc_id"],
    }


def _client_kind(client: str | None) -> str | None:
    if not client:
        return None
    match = re.search(r"\((government|private|psu)\)", client, re.I)
    return match.group(1).lower() if match else None
