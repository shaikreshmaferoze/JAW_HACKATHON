from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from src.parsing.normalization import extract_package_id, normalize_category, normalize_key, package_number


class KnowledgeBase:
    def __init__(self, db_path: str | Path = "artifacts/bid_intelligence.db"):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row

    def close(self) -> None:
        self.conn.close()

    def clients(self) -> list[sqlite3.Row]:
        return self.conn.execute("SELECT * FROM clients").fetchall()

    def people(self) -> list[sqlite3.Row]:
        return self.conn.execute("SELECT * FROM people").fetchall()

    def projects(self) -> list[sqlite3.Row]:
        return self.conn.execute(
            """
            SELECT p.*, c.client_name, c.normalized_client_name
            FROM projects p LEFT JOIN clients c ON c.client_id=p.client_id
            """
        ).fetchall()

    def find_client(self, text: str) -> sqlite3.Row | None:
        nq = normalize_key(text)
        candidates = []
        for client in self.clients():
            nc = client["normalized_client_name"]
            if nc and nc in nq:
                candidates.append((len(nc), client))
        candidates.sort(reverse=True, key=lambda item: item[0])
        return candidates[0][1] if candidates else None

    def find_person(self, text: str) -> sqlite3.Row | None:
        nq = normalize_key(text)
        candidates = []
        for person in self.people():
            np = person["normalized_person_name"]
            if np and np in nq:
                candidates.append((len(np), person))
        candidates.sort(reverse=True, key=lambda item: item[0])
        return candidates[0][1] if candidates else None

    def find_project(self, text: str) -> sqlite3.Row | None:
        package = package_number(extract_package_id(text))
        if package is not None:
            row = self.conn.execute(
                """
                SELECT p.*, c.client_name, c.normalized_client_name
                FROM projects p LEFT JOIN clients c ON c.client_id=p.client_id
                WHERE p.project_number=?
                """,
                (package,),
            ).fetchone()
            if row:
                return row
        nq = normalize_key(text)
        candidates = []
        for project in self.projects():
            np = project["normalized_project_name"]
            if np and np in nq:
                candidates.append((len(np), project))
        candidates.sort(reverse=True, key=lambda item: item[0])
        return candidates[0][1] if candidates else None

    def projects_for_client(self, client_id: str) -> list[sqlite3.Row]:
        return self.conn.execute(
            """
            SELECT p.*, c.client_name
            FROM projects p JOIN clients c ON c.client_id=p.client_id
            WHERE p.client_id=?
            ORDER BY p.project_number
            """,
            (client_id,),
        ).fetchall()

    def projects_for_person(self, person_id: str) -> list[sqlite3.Row]:
        return self.conn.execute(
            """
            SELECT p.*, c.client_name, pp.role
            FROM project_people pp
            JOIN projects p ON p.project_id=pp.project_id
            LEFT JOIN clients c ON c.client_id=p.client_id
            WHERE pp.person_id=?
            ORDER BY p.project_number
            """,
            (person_id,),
        ).fetchall()

    def certification_for_person(self, person_id: str, credential_type: str | None = None, credential_id: str | None = None) -> sqlite3.Row | None:
        if credential_id:
            return self.conn.execute(
                "SELECT * FROM certifications WHERE person_id=? AND credential_id=?",
                (person_id, credential_id),
            ).fetchone()
        if credential_type:
            return self.conn.execute(
                "SELECT * FROM certifications WHERE person_id=? AND LOWER(credential_type)=LOWER(?) ORDER BY issue_date LIMIT 1",
                (person_id, credential_type),
            ).fetchone()
        return self.conn.execute("SELECT * FROM certifications WHERE person_id=? ORDER BY issue_date LIMIT 1", (person_id,)).fetchone()

    def source_documents_for_project(self, project_id: str) -> list[sqlite3.Row]:
        return self.conn.execute(
            """
            SELECT pd.*, d.filename, d.doc_type
            FROM project_documents pd JOIN documents d ON d.doc_id=pd.doc_id
            WHERE project_id=?
            """,
            (project_id,),
        ).fetchall()

    def workbook_records(self, doc_type: str | None = None) -> list[sqlite3.Row]:
        if doc_type:
            return self.conn.execute("SELECT * FROM workbook_records WHERE doc_type=?", (doc_type,)).fetchall()
        return self.conn.execute("SELECT * FROM workbook_records").fetchall()

