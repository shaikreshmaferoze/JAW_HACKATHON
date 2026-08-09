from __future__ import annotations

import sqlite3


SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS documents;
DROP TABLE IF EXISTS clients;
DROP TABLE IF EXISTS projects;
DROP TABLE IF EXISTS people;
DROP TABLE IF EXISTS certifications;
DROP TABLE IF EXISTS project_documents;
DROP TABLE IF EXISTS project_people;
DROP TABLE IF EXISTS reference_letters;
DROP TABLE IF EXISTS performance_bonds;
DROP TABLE IF EXISTS financial_records;
DROP TABLE IF EXISTS workbook_records;
DROP TABLE IF EXISTS relationships;

CREATE TABLE documents (
    doc_id TEXT PRIMARY KEY,
    doc_type TEXT,
    filename TEXT,
    size_bytes INTEGER,
    pages INTEGER,
    char_count INTEGER,
    extraction_method TEXT,
    extraction_quality REAL
);

CREATE TABLE clients (
    client_id TEXT PRIMARY KEY,
    client_name TEXT UNIQUE,
    normalized_client_name TEXT,
    client_kind TEXT
);

CREATE TABLE projects (
    project_id TEXT PRIMARY KEY,
    project_number INTEGER,
    project_name TEXT,
    normalized_project_name TEXT,
    package_id TEXT,
    client_id TEXT,
    contract_value_inr INTEGER,
    start_date TEXT,
    completion_date TEXT,
    grading TEXT,
    category TEXT,
    normalized_category TEXT,
    project_lead TEXT,
    contractor_role TEXT,
    has_reference_letter INTEGER DEFAULT 0,
    has_performance_bond INTEGER DEFAULT 0,
    has_company_completion_certificate INTEGER DEFAULT 0,
    has_completion_certificate INTEGER DEFAULT 0
);

CREATE TABLE people (
    person_id TEXT PRIMARY KEY,
    person_name TEXT UNIQUE,
    normalized_person_name TEXT,
    employee_id TEXT
);

CREATE TABLE certifications (
    certification_id TEXT PRIMARY KEY,
    person_id TEXT,
    credential_type TEXT,
    credential_id TEXT,
    issue_date TEXT,
    expiry_date TEXT,
    source_document_id TEXT
);

CREATE TABLE project_documents (
    project_id TEXT,
    doc_id TEXT,
    relationship TEXT,
    confidence REAL,
    evidence_json TEXT,
    PRIMARY KEY (project_id, doc_id, relationship)
);

CREATE TABLE project_people (
    project_id TEXT,
    person_id TEXT,
    role TEXT,
    source_document_id TEXT,
    confidence REAL,
    PRIMARY KEY (project_id, person_id, role)
);

CREATE TABLE reference_letters (
    doc_id TEXT PRIMARY KEY,
    project_id TEXT,
    contractor_role TEXT,
    value_inr INTEGER,
    completion_date TEXT
);

CREATE TABLE performance_bonds (
    doc_id TEXT PRIMARY KEY,
    project_id TEXT,
    bond_number TEXT,
    bond_amount_inr INTEGER,
    issue_date TEXT
);

CREATE TABLE financial_records (
    record_id INTEGER PRIMARY KEY AUTOINCREMENT,
    doc_id TEXT,
    record_type TEXT,
    key TEXT,
    value TEXT,
    amount_inr INTEGER,
    date TEXT
);

CREATE TABLE workbook_records (
    record_id INTEGER PRIMARY KEY AUTOINCREMENT,
    doc_id TEXT,
    doc_type TEXT,
    filename TEXT,
    sheet_name TEXT,
    row_number INTEGER,
    record_json TEXT
);

CREATE TABLE relationships (
    source TEXT,
    target TEXT,
    relationship TEXT,
    confidence REAL,
    evidence_json TEXT
);

CREATE INDEX idx_projects_name ON projects(normalized_project_name);
CREATE INDEX idx_projects_package ON projects(package_id);
CREATE INDEX idx_projects_client ON projects(client_id);
CREATE INDEX idx_people_name ON people(normalized_person_name);
CREATE INDEX idx_cert_credential ON certifications(credential_id);
CREATE INDEX idx_doc_type ON documents(doc_type);
"""


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA_SQL)
    conn.commit()

