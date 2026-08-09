from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.entity_resolution.projects import duplicate_project_groups


def main() -> None:
    db_path = Path("artifacts/bid_intelligence.db")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    projects = [dict(r) for r in conn.execute("SELECT * FROM projects").fetchall()]
    report = {
        "project_count": len(projects),
        "client_count": conn.execute("SELECT COUNT(*) FROM clients").fetchone()[0],
        "people_count": conn.execute("SELECT COUNT(*) FROM people").fetchone()[0],
        "project_people_count": conn.execute("SELECT COUNT(*) FROM project_people").fetchone()[0],
        "company_completion_certificates_unmapped": conn.execute(
            """
            SELECT d.doc_id, d.filename
            FROM documents d
            LEFT JOIN project_documents pd ON pd.doc_id=d.doc_id AND pd.relationship='COMPANY_COMPLETION_CERTIFICATE'
            WHERE d.doc_type='company_completion_certificate' AND pd.doc_id IS NULL
            """
        ).fetchall(),
        "completion_certificates_unmapped": conn.execute(
            """
            SELECT d.doc_id, d.filename
            FROM documents d
            LEFT JOIN project_documents pd ON pd.doc_id=d.doc_id AND pd.relationship='COMPLETION_CERTIFICATE'
            WHERE d.doc_type='completion_certificate' AND pd.doc_id IS NULL
            """
        ).fetchall(),
        "reference_letters_unmapped": conn.execute(
            """
            SELECT d.doc_id, d.filename
            FROM documents d
            LEFT JOIN reference_letters rl ON rl.doc_id=d.doc_id
            WHERE d.doc_type='reference_letter' AND rl.doc_id IS NULL
            """
        ).fetchall(),
        "personnel_certificates_unmapped": conn.execute(
            """
            SELECT d.doc_id, d.filename
            FROM documents d
            LEFT JOIN certifications c ON c.source_document_id=d.doc_id
            WHERE d.doc_type='personnel_certificate' AND c.source_document_id IS NULL
            """
        ).fetchall(),
        "projects_without_client": [p for p in projects if not p.get("client_id")],
        "projects_without_value": [p for p in projects if p.get("contract_value_inr") is None],
        "projects_without_completion_date": [p for p in projects if not p.get("completion_date")],
        "duplicate_project_groups": duplicate_project_groups(projects),
        "reference_letter_count": conn.execute("SELECT COUNT(*) FROM reference_letters").fetchone()[0],
        "performance_bond_count": conn.execute("SELECT COUNT(*) FROM performance_bonds").fetchone()[0],
        "workbook_record_count": conn.execute("SELECT COUNT(*) FROM workbook_records").fetchone()[0],
    }

    for key in [
        "company_completion_certificates_unmapped",
        "completion_certificates_unmapped",
        "reference_letters_unmapped",
        "personnel_certificates_unmapped",
    ]:
        report[key] = [dict(r) for r in report[key]]

    out = Path("artifacts/kb_validation_report.json")
    out.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print(json.dumps({k: (len(v) if isinstance(v, list) else v) for k, v in report.items()}, indent=2))
    conn.close()


if __name__ == "__main__":
    main()
