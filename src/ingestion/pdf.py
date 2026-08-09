from __future__ import annotations

from pathlib import Path
from typing import Any

import pdfplumber
from pypdf import PdfReader

from src.parsing.normalization import clean_text


def _char_quality(text: str) -> float:
    if not text:
        return 0.0
    good = sum(1 for ch in text if ch.isalnum() or ch.isspace() or ch in ".,:/()-&'\"#%")
    return good / max(1, len(text))


def _extract_pdfplumber(path: Path) -> tuple[list[str], list[list[list[str]]]]:
    pages: list[str] = []
    page_tables: list[list[list[str]]] = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            plain = page.extract_text(layout=False) or ""
            layout = page.extract_text(layout=True) or ""
            text = plain if len(plain) >= len(layout) * 0.55 else layout
            tables_text: list[str] = []
            raw_tables = page.extract_tables() or []
            for table in raw_tables:
                for row in table:
                    cells = [clean_text(cell) for cell in row if clean_text(cell)]
                    if cells:
                        tables_text.append(" | ".join(cells))
            combined = clean_text(text)
            if tables_text:
                combined = clean_text(combined + "\n\n[TABLE]\n" + "\n".join(tables_text))
            pages.append(combined)
            page_tables.append(raw_tables)
    return pages, page_tables


def _extract_pypdf(path: Path) -> list[str]:
    reader = PdfReader(str(path))
    return [clean_text(page.extract_text() or "") for page in reader.pages]


def extract_pdf(path: str | Path) -> dict[str, Any]:
    path = Path(path)
    method = "pdfplumber"
    pages, tables = _extract_pdfplumber(path)
    text = "\n\n=== Page Break ===\n\n".join(pages)

    suspicious = len(clean_text(text)) < 120 or _char_quality(text) < 0.85
    try:
        fallback_pages = _extract_pypdf(path)
        fallback_text = "\n\n=== Page Break ===\n\n".join(fallback_pages)
        if suspicious or len(fallback_text) > len(text) * 1.25:
            pages = fallback_pages
            text = fallback_text
            method = "pypdf_fallback"
        else:
            method = "pdfplumber_with_pypdf_check"
    except Exception:
        if suspicious:
            method = "pdfplumber_fallback_failed"

    quality = round(min(1.0, _char_quality(text) * (1.0 if len(text) >= 120 else len(text) / 120)), 4)
    return {
        "pages": len(pages),
        "page_texts": pages,
        "text": clean_text(text),
        "tables_detected": sum(len(t or []) for t in tables),
        "extraction_method": method,
        "extraction_quality": quality,
        "char_count": len(clean_text(text)),
    }
