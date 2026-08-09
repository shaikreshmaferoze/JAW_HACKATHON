from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from src.entity_resolution.projects import match_project
from src.extraction.bonds import parse_performance_bond
from src.extraction.completion import parse_client_completion, parse_company_completion
from src.extraction.financial import workbook_records
from src.extraction.personnel import parse_cv, parse_personnel_certificate
from src.extraction.reference import parse_reference_letter
from src.ingestion.pipeline import extract_all_documents
from src.knowledge_base.schema import init_db
from src.parsing.normalization import normalize_client, normalize_key, package_number


def _client_id(name: str) -> str:
    return "CLI-" + normalize_key(name).replace(" ", "-")[:80]


def _person_id(name: str) -> str:
    return "PER-" + normalize_key(name).replace(" ", "-")[:80]


def build_kb(
    repo_root: str | Path = ".",
    db_path: str | Path = "artifacts/bid_intelligence.db",
    force_extract: bool = False,
) -> dict[str, Any]:
    root = Path(repo_root)
    docs = extract_all_documents(root, force=force_extract)
    db_file = root / db_path
    db_file.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_file)
    init_db(conn)

    for doc in docs:
        conn.execute(
            """
            INSERT INTO documents(doc_id, doc_type, filename, size_bytes, pages, char_count, extraction_method, extraction_quality)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                doc["doc_id"],
                doc["doc_type"],
                doc["filename"],
                doc.get("size_bytes"),
                doc.get("pages"),
                doc.get("char_count"),
                doc.get("extraction_method"),
                doc.get("extraction_quality"),
            ),
        )

    projects: list[dict[str, Any]] = []
    client_kinds: dict[str, str | None] = {}
    for doc in docs:
        if doc["doc_type"] != "company_completion_certificate":
            continue
        record = parse_company_completion(doc)
        if not record or not record.get("project_id"):
            continue
        projects.append(record)
        if record.get("client_name"):
            client_kinds[record["client_name"]] = record.get("client_kind")

    for client_name in sorted({p["client_name"] for p in projects if p.get("client_name")}):
        conn.execute(
            "INSERT OR IGNORE INTO clients(client_id, client_name, normalized_client_name, client_kind) VALUES (?, ?, ?, ?)",
            (_client_id(client_name), client_name, normalize_key(client_name), client_kinds.get(client_name)),
        )

    for project in projects:
        cid = _client_id(project["client_name"]) if project.get("client_name") else None
        conn.execute(
            """
            INSERT INTO projects(project_id, project_number, project_name, normalized_project_name, package_id, client_id,
                contract_value_inr, completion_date, grading, category, normalized_category, project_lead,
                contractor_role, has_company_completion_certificate)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
            """,
            (
                project["project_id"],
                project.get("project_number"),
                project.get("project_name"),
                project.get("normalized_project_name"),
                project.get("package_id"),
                cid,
                project.get("contract_value_inr"),
                project.get("completion_date"),
                project.get("grading"),
                project.get("category"),
                project.get("normalized_category"),
                project.get("project_lead"),
                "Prime",
            ),
        )
        _link(conn, project["project_id"], project["source_document_id"], "COMPANY_COMPLETION_CERTIFICATE", 0.99, project["evidence"])

    by_id = {p["project_id"]: p for p in projects}

    # Client completion certificates.
    for doc in docs:
        if doc["doc_type"] != "completion_certificate":
            continue
        rec = parse_client_completion(doc)
        project_id, confidence, evidence = match_project(rec, projects)
        if project_id:
            _link(conn, project_id, doc["doc_id"], "COMPLETION_CERTIFICATE", confidence, evidence)
            _update_project_value_if_better(conn, project_id, rec.get("contract_value_inr"))
            conn.execute(
                "UPDATE projects SET has_completion_certificate=1, grading=COALESCE(NULLIF(?, ''), grading) WHERE project_id=?",
                (rec.get("grading"), project_id),
            )

    # People and certifications.
    people: dict[str, dict[str, Any]] = {}
    for project in projects:
        lead = project.get("project_lead")
        if lead:
            people.setdefault(lead, {"person_name": lead, "employee_id": None})

    cert_count = 0
    for doc in docs:
        rec = None
        if doc["doc_type"] == "personnel_certificate":
            rec = parse_personnel_certificate(doc)
        elif doc["doc_type"] == "cv":
            rec = parse_cv(doc)
        if not rec:
            continue
        people.setdefault(rec["employee_name"], {"person_name": rec["employee_name"], "employee_id": rec.get("employee_id")})
        if rec.get("employee_id"):
            people[rec["employee_name"]]["employee_id"] = rec.get("employee_id")
        if doc["doc_type"] == "personnel_certificate":
            cert_count += 1
            pid = _person_id(rec["employee_name"])
            conn.execute(
                """
                INSERT OR REPLACE INTO certifications(certification_id, person_id, credential_type, credential_id, issue_date, expiry_date, source_document_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    rec.get("credential_id") or f"CERT-{cert_count:04d}",
                    pid,
                    rec.get("credential_type"),
                    rec.get("credential_id"),
                    rec.get("issue_date"),
                    rec.get("expiry_date"),
                    rec.get("source_document_id"),
                ),
            )

    for person in people.values():
        conn.execute(
            "INSERT OR IGNORE INTO people(person_id, person_name, normalized_person_name, employee_id) VALUES (?, ?, ?, ?)",
            (_person_id(person["person_name"]), person["person_name"], normalize_key(person["person_name"]), person.get("employee_id")),
        )
    for project in projects:
        lead = project.get("project_lead")
        if lead:
            conn.execute(
                "INSERT OR IGNORE INTO project_people(project_id, person_id, role, source_document_id, confidence) VALUES (?, ?, ?, ?, ?)",
                (project["project_id"], _person_id(lead), "Project Lead", project["source_document_id"], 0.99),
            )
            conn.execute(
                "INSERT INTO relationships(source, target, relationship, confidence, evidence_json) VALUES (?, ?, ?, ?, ?)",
                (project["source_document_id"], _person_id(lead), "PROJECT_LED_BY", 0.99, json.dumps(["project lead field"])),
            )

    # Reference letters.
    ref_matches = 0
    for doc in docs:
        if doc["doc_type"] != "reference_letter":
            continue
        rec = parse_reference_letter(doc)
        project_id, confidence, evidence = match_project(rec, projects)
        if project_id:
            ref_matches += 1
            _link(conn, project_id, doc["doc_id"], "REFERENCE_LETTER", confidence, evidence)
            role = rec.get("contractor_role") or "Prime"
            conn.execute(
                """
                INSERT OR REPLACE INTO reference_letters(doc_id, project_id, contractor_role, value_inr, completion_date)
                VALUES (?, ?, ?, ?, ?)
                """,
                (doc["doc_id"], project_id, role, rec.get("contract_value_inr"), rec.get("completion_date")),
            )
            if role:
                conn.execute("UPDATE projects SET contractor_role=? WHERE project_id=?", (role, project_id))
            conn.execute("UPDATE projects SET has_reference_letter=1 WHERE project_id=?", (project_id,))

    # Performance bonds; numeric suffix normally points to the project number.
    bond_matches = 0
    for doc in docs:
        if doc["doc_type"] != "performance_bond":
            continue
        rec = parse_performance_bond(doc)
        project_id = None
        hint = rec.get("project_number_hint")
        if hint is not None:
            project_id = f"PRJ-{hint:03d}"
        if project_id not in by_id:
            project_id, _, _ = match_project(rec, projects)
        if project_id and project_id in by_id:
            bond_matches += 1
            _link(conn, project_id, doc["doc_id"], "PERFORMANCE_BOND", 0.80, ["document numeric suffix", rec.get("bond_number")])
            conn.execute(
                """
                INSERT OR REPLACE INTO performance_bonds(doc_id, project_id, bond_number, bond_amount_inr, issue_date)
                VALUES (?, ?, ?, ?, ?)
                """,
                (doc["doc_id"], project_id, rec.get("bond_number"), rec.get("bond_amount_inr"), rec.get("issue_date")),
            )
            conn.execute("UPDATE projects SET has_performance_bond=1 WHERE project_id=?", (project_id,))

    # Workbook records.
    workbook_rows = 0
    for doc in docs:
        if not doc["filename"].lower().endswith(".xlsx"):
            continue
        for rec in workbook_records(doc):
            workbook_rows += 1
            conn.execute(
                """
                INSERT INTO workbook_records(doc_id, doc_type, filename, sheet_name, row_number, record_json)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (rec["doc_id"], rec["doc_type"], rec["filename"], rec["sheet_name"], rec["row_number"], json.dumps(rec["record"], default=str)),
            )

    conn.commit()
    stats = {
        "documents": len(docs),
        "projects": len(projects),
        "clients": conn.execute("SELECT COUNT(*) FROM clients").fetchone()[0],
        "people": conn.execute("SELECT COUNT(*) FROM people").fetchone()[0],
        "certifications": conn.execute("SELECT COUNT(*) FROM certifications").fetchone()[0],
        "project_people": conn.execute("SELECT COUNT(*) FROM project_people").fetchone()[0],
        "reference_letters_matched": ref_matches,
        "performance_bonds_matched": bond_matches,
        "workbook_records": workbook_rows,
        "db_path": str(db_file),
    }
    conn.close()
    return stats


def _link(conn: sqlite3.Connection, project_id: str, doc_id: str, relationship: str, confidence: float, evidence: list[Any]) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO project_documents(project_id, doc_id, relationship, confidence, evidence_json) VALUES (?, ?, ?, ?, ?)",
        (project_id, doc_id, relationship, confidence, json.dumps(evidence, default=str)),
    )
    conn.execute(
        "INSERT INTO relationships(source, target, relationship, confidence, evidence_json) VALUES (?, ?, ?, ?, ?)",
        (doc_id, project_id, relationship, confidence, json.dumps(evidence, default=str)),
    )


def _update_project_value_if_better(conn: sqlite3.Connection, project_id: str, candidate: int | None) -> None:
    if candidate is None:
        return
    row = conn.execute("SELECT contract_value_inr FROM projects WHERE project_id=?", (project_id,)).fetchone()
    current = row[0] if row else None
    if current is None:
        conn.execute("UPDATE projects SET contract_value_inr=? WHERE project_id=?", (candidate, project_id))
        return
    # Prefer an exact rupee rendering from client/reference evidence over a rounded Cr/Lakh rendering.
    if current != candidate and (current % 100000 == 0 or abs(current - candidate) <= max(100000, int(current * 0.001))):
        conn.execute("UPDATE projects SET contract_value_inr=? WHERE project_id=?", (candidate, project_id))
