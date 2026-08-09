from __future__ import annotations

from collections import defaultdict
from typing import Any

from src.parsing.normalization import normalize_project, package_number


def match_project(record: dict[str, Any], projects: list[dict[str, Any]]) -> tuple[str | None, float, list[str]]:
    package = package_number(record.get("package_id")) or record.get("project_number_hint")
    norm = normalize_project(record.get("project_name"))
    value = record.get("contract_value_inr")

    candidates = []
    for project in projects:
        evidence = []
        score = 0.0
        if package is not None and package == project.get("project_number"):
            score += 0.70
            evidence.append("matching package/document number")
        if norm and norm == project.get("normalized_project_name"):
            score += 0.60
            evidence.append("exact normalized project name")
        elif norm and project.get("normalized_project_name") and (
            norm in project["normalized_project_name"] or project["normalized_project_name"] in norm
        ):
            score += 0.35
            evidence.append("partial normalized project name")
        if value is not None and project.get("contract_value_inr") == value:
            score += 0.20
            evidence.append("matching contract value")
        if record.get("client_name") and project.get("client_name") == record.get("client_name"):
            score += 0.15
            evidence.append("matching client")
        if score:
            candidates.append((score, project["project_id"], evidence))
    if not candidates:
        return None, 0.0, []
    candidates.sort(reverse=True, key=lambda item: item[0])
    score, project_id, evidence = candidates[0]
    return project_id, min(score, 0.99), evidence


def duplicate_project_groups(projects: list[dict[str, Any]]) -> list[list[str]]:
    groups: dict[str, list[str]] = defaultdict(list)
    for project in projects:
        key = project.get("normalized_project_name") or str(project.get("project_number"))
        groups[key].append(project["project_id"])
    return [ids for ids in groups.values() if len(ids) > 1]
