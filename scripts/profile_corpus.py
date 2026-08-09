from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.ingestion.pipeline import extract_all_documents, load_document_index


def main() -> None:
    root = Path(".")
    rows = load_document_index(root)
    docs = extract_all_documents(root)

    by_type = Counter(row["doc_type"] for row in rows)
    by_ext = Counter(Path(row["filename"]).suffix.lower().lstrip(".") for row in rows)
    sizes = defaultdict(list)
    extraction = Counter()
    pdf_pages = {}
    char_counts = {}
    workbook_sheets = {}
    workbook_dimensions = {}
    failures = []

    for row in rows:
        sizes[row["doc_type"]].append(int(row["size_bytes"]))
    for doc in docs:
        extraction[doc.get("extraction_method", "unknown")] += 1
        if doc.get("extraction_quality", 0) < 0.25:
            failures.append({"doc_id": doc["doc_id"], "quality": doc.get("extraction_quality"), "filename": doc["filename"]})
        if doc["filename"].lower().endswith(".pdf"):
            pdf_pages[doc["doc_id"]] = doc.get("pages")
        else:
            workbook_sheets[doc["doc_id"]] = doc.get("sheet_names", [])
            workbook_dimensions[doc["doc_id"]] = {
                sheet["name"]: [sheet["max_row"], sheet["max_column"]] for sheet in doc.get("sheets", [])
            }
        char_counts[doc["doc_id"]] = doc.get("char_count")

    profile = {
        "document_count": len(rows),
        "documents_by_type": dict(sorted(by_type.items())),
        "documents_by_extension": dict(sorted(by_ext.items())),
        "size_bytes_by_type": {
            typ: {"count": len(vals), "min": min(vals), "max": max(vals), "total": sum(vals)}
            for typ, vals in sorted(sizes.items())
        },
        "extraction_methods": dict(extraction),
        "extraction_failures_or_low_quality": failures,
        "pdf_pages_by_doc_id": pdf_pages,
        "character_counts_by_doc_id": char_counts,
        "workbook_sheet_names": workbook_sheets,
        "workbook_dimensions": workbook_dimensions,
    }

    artifacts = root / "artifacts"
    artifacts.mkdir(exist_ok=True)
    (artifacts / "corpus_profile.json").write_text(json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        f"Documents: {len(rows)}",
        "By extension: " + ", ".join(f"{k}={v}" for k, v in sorted(by_ext.items())),
        "By type:",
    ]
    for typ, count in sorted(by_type.items()):
        vals = sizes[typ]
        lines.append(f"  {typ}: {count} docs, {sum(vals)} bytes total, min {min(vals)}, max {max(vals)}")
    lines.append("Extraction methods:")
    for method, count in sorted(extraction.items()):
        lines.append(f"  {method}: {count}")
    lines.append(f"Low-quality extraction count: {len(failures)}")
    lines.append("Workbook sheets:")
    for doc_id, sheets in sorted(workbook_sheets.items()):
        dims = workbook_dimensions[doc_id]
        dim_text = ", ".join(f"{name}={dims[name][0]}x{dims[name][1]}" for name in sheets)
        lines.append(f"  {doc_id}: {', '.join(sheets)} ({dim_text})")
    (artifacts / "corpus_profile.txt").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
