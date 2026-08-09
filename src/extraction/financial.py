from __future__ import annotations

from typing import Any


def workbook_records(doc: dict[str, Any]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for sheet in doc.get("sheets", []) or []:
        rows = sheet.get("values", []) or []
        if not rows:
            continue
        headers = [str(h).strip() if h is not None else "" for h in rows[0]]
        for idx, row in enumerate(rows[1:], start=2):
            if not any(cell is not None for cell in row):
                continue
            record = {headers[i] or f"col_{i+1}": row[i] if i < len(row) else None for i in range(len(headers))}
            records.append(
                {
                    "doc_id": doc["doc_id"],
                    "doc_type": doc["doc_type"],
                    "filename": doc["filename"],
                    "sheet_name": sheet["name"],
                    "row_number": idx,
                    "record": record,
                }
            )
    return records

