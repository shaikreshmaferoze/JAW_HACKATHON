from __future__ import annotations

import re
from typing import Any

from src.extraction.common import find_field, regex_first
from src.parsing.dates import parse_date
from src.parsing.money import parse_money
from src.parsing.normalization import clean_text, compact_spaces, normalize_category


def parse_performance_bond(doc: dict[str, Any]) -> dict[str, Any]:
    text = clean_text(doc.get("text", ""))
    doc_number = None
    match = re.search(r"(\d+)$", doc["doc_id"])
    if match:
        doc_number = int(match.group(1))
    bond_amount = regex_first(text, [r"amount not exceeding\s+(.+?)\s*\(", r"Bond Amount\s+(.+)"])
    pct_match = re.search(r"for\s+(\d+(?:\.\d+)?)%\s*\(", text, re.I)
    pct = float(pct_match.group(1)) if pct_match else None
    value = None
    amount = parse_money(bond_amount)
    if amount is not None and pct:
        value = int(round(amount * 100 / pct))
    return {
        "project_number_hint": doc_number,
        "bond_number": find_field(text, ["Bond No"]) or regex_first(text, [r"Bond No:?\s*([A-Z0-9-]+)"]),
        "issue_date": parse_date(find_field(text, ["Issue Date"])),
        "tender_ref": regex_first(text, [r"Tender Ref:?\s*([A-Z0-9-]+)", r"Tender Reference\s+([A-Z0-9-]+)"]),
        "category": compact_spaces(regex_first(text, [r"work of\s+([A-Za-z ]+?),\s+and", r"for the work of\s+([A-Za-z ]+?),"])),
        "normalized_category": normalize_category(regex_first(text, [r"work of\s+([A-Za-z ]+?),\s+and", r"for the work of\s+([A-Za-z ]+?),"])),
        "bond_amount_inr": amount,
        "contract_value_inr_hint": value,
        "source_document_id": doc["doc_id"],
    }

