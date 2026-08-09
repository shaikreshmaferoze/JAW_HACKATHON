from __future__ import annotations

import re
from typing import Any

from src.parsing.money import parse_money_threshold
from src.parsing.normalization import normalize_category


def _credential_type(question: str) -> str | None:
    if re.search(r"\bPMP\b", question, re.I):
        return "PMP"
    match = re.search(r"\bSix Sigma(?:\s+[A-Za-z]+(?:\s+[A-Za-z]+)?)?", question, re.I)
    if match:
        return match.group(0)
    return None


def plan_question(question: str) -> dict[str, Any]:
    q = question.strip()
    lo = q.lower()
    plan: dict[str, Any] = {"question": q}
    cert_id = re.search(r"\b[A-Z]{2,6}-\d{5,}\b", q)
    if cert_id:
        plan["credential_id"] = cert_id.group(0)
    credential = _credential_type(q)
    if credential:
        plan["credential_type"] = credential

    if "no client reference" in lo or "lack" in lo and "reference" in lo or "no reference" in lo or "unreferenced" in lo:
        plan.update({"operation": "count_missing_reference", "scope": "client_portfolio"})
    elif any(word in lo for word in ["days passed", "interval", "number of days", "days between"]):
        plan.update({"operation": "days_between_cert_and_completion"})
    elif any(word in lo for word in ["distinct", "different"]) and any(word in lo for word in ["categories", "classifications"]):
        plan.update({"operation": "distinct_count_categories_for_person"})
    elif any(word in lo for word in ["average", "mean"]) and "size" in lo:
        plan.update({"operation": "average_client_project_value"})
    elif "excluding" in lo or "exclude" in lo:
        plan.update({"operation": "sum_client_excluding_category"})
        m = re.search(r"excluding\s+([a-zA-Z ]+?)(?:,|\?| what|$)", q, re.I)
        if m:
            plan["excluded_category"] = normalize_category(m.group(1))
    elif "additional work" in lo or "reach our credential target" in lo or "target of" in lo:
        plan.update({"operation": "gap_to_threshold"})
        plan["threshold_inr"] = parse_money_threshold(q)
    elif "largest" in lo and ("second largest" in lo or "second-largest" in lo or "exceed" in lo):
        plan.update({"operation": "largest_minus_second"})
    elif ("share" in lo or "divided by the total" in lo or "out of one hundred" in lo) and (
        "reference" in lo or "verification" in lo
    ):
        plan.update({"operation": "reference_share"})
    elif re.search(r"\bas prime\b", lo):
        plan.update({"operation": "sum_client_role", "role": "Prime"})
    elif any(word in lo for word in ["crossing", "hitting", "above", "over"]) and any(
        unit in lo for unit in ["crore", "cr", "lakh", "line", "mark"]
    ):
        plan.update({"operation": "sum_client_above_threshold"})
        plan["threshold_inr"] = parse_money_threshold(q)
    elif "after" in lo and any(word in lo for word in ["certification", "issued", "issuance", "pmp"]):
        plan.update({"operation": "sum_person_projects_after_cert"})
    elif any(word in lo for word in ["combined value", "total value", "aggregate value", "total"]):
        plan.update({"operation": "sum_anchor_client_portfolio"})
    else:
        plan.update({"operation": "unknown"})
    return plan
