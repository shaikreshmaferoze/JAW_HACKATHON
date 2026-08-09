from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from src.ingestion.excel import extract_workbook
from src.ingestion.pdf import extract_pdf


def load_document_index(repo_root: str | Path = ".") -> list[dict[str, Any]]:
    root = Path(repo_root)
    with (root / "document_index.csv").open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def extract_document(repo_root: str | Path, row: dict[str, Any]) -> dict[str, Any]:
    root = Path(repo_root)
    rel = Path("documents") / row["filename"]
    path = root / rel
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        extracted = extract_pdf(path)
    elif suffix in {".xlsx", ".xlsm", ".xls"}:
        extracted = extract_workbook(path)
    else:
        raise ValueError(f"unsupported document type: {path}")
    return {
        "doc_id": row["doc_id"],
        "doc_type": row["doc_type"],
        "filename": row["filename"],
        "size_bytes": int(row["size_bytes"]),
        **extracted,
    }


def extract_all_documents(
    repo_root: str | Path = ".",
    cache_dir: str | Path = "artifacts/raw_documents",
    force: bool = False,
) -> list[dict[str, Any]]:
    root = Path(repo_root)
    cache = root / cache_dir
    cache.mkdir(parents=True, exist_ok=True)
    docs = []
    for row in load_document_index(root):
        out = cache / f"{row['doc_id']}.json"
        if out.exists() and not force:
            with out.open(encoding="utf-8") as f:
                doc = json.load(f)
        else:
            doc = extract_document(root, row)
            with out.open("w", encoding="utf-8") as f:
                json.dump(doc, f, ensure_ascii=False, indent=2)
        docs.append(doc)
    return docs

