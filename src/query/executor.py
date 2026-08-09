from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from src.knowledge_base.queries import KnowledgeBase
from src.parsing.dates import days_between
from src.parsing.normalization import normalize_category
from src.query.planner import plan_question


def _money_values(projects: list[Any]) -> list[int]:
    return [int(p["contract_value_inr"]) for p in projects if p["contract_value_inr"] is not None]


def _round_int(value: Decimal) -> int:
    return int(value.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _round_pct(value: Decimal) -> float:
    return float(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def solve_question(question: str, kb: KnowledgeBase | None = None) -> dict[str, Any]:
    own_kb = kb is None
    kb = kb or KnowledgeBase()
    try:
        plan = plan_question(question)
        result = _execute(plan, kb)
        return result
    finally:
        if own_kb:
            kb.close()


def _execute(plan: dict[str, Any], kb: KnowledgeBase) -> dict[str, Any]:
    question = plan["question"]
    operation = plan["operation"]
    client = kb.find_client(question)
    person = kb.find_person(question)
    project = kb.find_project(question)

    evidence: dict[str, Any] = {"plan": plan, "entities": {}, "values": [], "documents": []}
    if client:
        evidence["entities"]["client"] = client["client_name"]
    if person:
        evidence["entities"]["person"] = person["person_name"]
    if project:
        evidence["entities"]["project"] = project["project_name"]

    if operation == "count_missing_reference":
        require(client, "client")
        projects = kb.projects_for_client(client["client_id"])
        answer = sum(1 for p in projects if not p["has_reference_letter"])
        return _answer(answer, operation, projects, kb, evidence)

    if operation == "days_between_cert_and_completion":
        require(person, "person")
        require(project, "project")
        cert = kb.certification_for_person(person["person_id"], plan.get("credential_type"), plan.get("credential_id"))
        require(cert, "certification")
        answer = days_between(cert["issue_date"], project["completion_date"])
        evidence["calculation"] = f"{project['completion_date']} - {cert['issue_date']}"
        return _answer(answer, operation, [project], kb, evidence)

    if operation == "distinct_count_categories_for_person":
        require(person, "person")
        projects = kb.projects_for_person(person["person_id"])
        cats = {normalize_category(p["category"]) for p in projects if p["category"]}
        evidence["categories"] = sorted(cats)
        return _answer(len(cats), operation, projects, kb, evidence)

    if operation == "average_client_project_value":
        if not client and project:
            client = {"client_id": project["client_id"], "client_name": project["client_name"]}
        require(client, "client")
        projects = kb.projects_for_client(client["client_id"])
        values = _money_values(projects)
        require(values, "values")
        answer = _round_int(Decimal(sum(values)) / Decimal(len(values)))
        evidence["calculation"] = f"sum(values) / {len(values)}"
        return _answer(answer, operation, projects, kb, evidence)

    if operation == "sum_client_excluding_category":
        require(client, "client")
        excluded = plan.get("excluded_category")
        projects = [p for p in kb.projects_for_client(client["client_id"]) if normalize_category(p["category"]) != excluded]
        return _answer(sum(_money_values(projects)), operation, projects, kb, evidence)

    if operation == "gap_to_threshold":
        require(client, "client")
        threshold = plan.get("threshold_inr")
        require(threshold, "threshold")
        projects = kb.projects_for_client(client["client_id"])
        answer = max(0, int(threshold) - sum(_money_values(projects)))
        evidence["calculation"] = f"{threshold} - sum(values)"
        return _answer(answer, operation, projects, kb, evidence)

    if operation == "largest_minus_second":
        require(client, "client")
        projects = kb.projects_for_client(client["client_id"])
        values = sorted(_money_values(projects), reverse=True)
        require(len(values) >= 2, "at least two values")
        answer = values[0] - values[1]
        evidence["calculation"] = "largest(values) - second_largest(values)"
        return _answer(answer, operation, projects, kb, evidence)

    if operation == "reference_share":
        require(client, "client")
        projects = kb.projects_for_client(client["client_id"])
        require(projects, "projects")
        referenced = sum(1 for p in projects if p["has_reference_letter"])
        answer = _round_pct(Decimal(referenced) * Decimal(100) / Decimal(len(projects)))
        evidence["calculation"] = f"{referenced} / {len(projects)} * 100"
        return _answer(answer, operation, projects, kb, evidence)

    if operation == "sum_client_role":
        require(client, "client")
        role = plan.get("role", "Prime").lower()
        projects = []
        for p in kb.projects_for_client(client["client_id"]):
            p_role = (p["contractor_role"] or "Prime").lower()
            if p_role == role.lower():
                projects.append(p)
        return _answer(sum(_money_values(projects)), operation, projects, kb, evidence)

    if operation == "sum_client_above_threshold":
        require(client, "client")
        threshold = plan.get("threshold_inr")
        require(threshold, "threshold")
        projects = [p for p in kb.projects_for_client(client["client_id"]) if p["contract_value_inr"] is not None and p["contract_value_inr"] >= threshold]
        return _answer(sum(_money_values(projects)), operation, projects, kb, evidence)

    if operation == "sum_person_projects_after_cert":
        require(person, "person")
        cert = kb.certification_for_person(person["person_id"], plan.get("credential_type"), plan.get("credential_id"))
        require(cert, "certification")
        projects = [p for p in kb.projects_for_person(person["person_id"]) if p["completion_date"] and p["completion_date"] > cert["issue_date"]]
        evidence["calculation"] = f"completion_date > {cert['issue_date']}"
        return _answer(sum(_money_values(projects)), operation, projects, kb, evidence)

    if operation == "sum_anchor_client_portfolio":
        if not client and project:
            client = {"client_id": project["client_id"], "client_name": project["client_name"]}
        require(client, "client")
        projects = kb.projects_for_client(client["client_id"])
        return _answer(sum(_money_values(projects)), operation, projects, kb, evidence)

    raise ValueError(f"unsupported or unparsed question operation: {operation}")


def _answer(answer: int | float, operation: str, projects: list[Any], kb: KnowledgeBase, evidence: dict[str, Any]) -> dict[str, Any]:
    contributing = []
    docs = []
    for p in projects:
        row = {
            "project_id": p["project_id"],
            "project": p["project_name"],
            "client": p["client_name"] if "client_name" in p.keys() else None,
            "value_inr": p["contract_value_inr"],
            "completion_date": p["completion_date"],
            "category": p["category"],
            "has_reference_letter": bool(p["has_reference_letter"]),
            "contractor_role": p["contractor_role"],
        }
        contributing.append(row)
        docs.extend([dict(d) for d in kb.source_documents_for_project(p["project_id"])])
    evidence["values"] = contributing
    evidence["documents"] = docs
    return {"answer": answer, "operation": operation, "evidence": evidence}


def require(value: Any, label: str) -> None:
    if not value:
        raise ValueError(f"missing required {label}")
