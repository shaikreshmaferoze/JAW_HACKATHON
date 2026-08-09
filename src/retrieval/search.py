from __future__ import annotations

import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from src.ingestion.pipeline import extract_all_documents
from src.parsing.normalization import normalize_key


def _tokens(text: str) -> list[str]:
    return [t for t in normalize_key(text).split() if len(t) > 1]


class LexicalIndex:
    def __init__(self, documents: list[dict[str, Any]]):
        self.documents = documents
        self.doc_tokens = {d["doc_id"]: Counter(_tokens(d.get("text", ""))) for d in documents}
        self.df: Counter[str] = Counter()
        for counts in self.doc_tokens.values():
            self.df.update(counts.keys())
        self.n = max(1, len(documents))
        self.by_id = {d["doc_id"]: d for d in documents}

    def search(self, query: str, filters: dict[str, Any] | None = None, limit: int = 20) -> list[dict[str, Any]]:
        q_tokens = Counter(_tokens(query))
        results = []
        for doc in self.documents:
            if filters:
                skip = False
                for key, value in filters.items():
                    if value is not None and doc.get(key) != value:
                        skip = True
                        break
                if skip:
                    continue
            counts = self.doc_tokens[doc["doc_id"]]
            score = 0.0
            for token, qtf in q_tokens.items():
                tf = counts.get(token, 0)
                if not tf:
                    continue
                idf = math.log((self.n + 1) / (self.df[token] + 1)) + 1
                score += (1 + math.log(tf)) * idf * qtf
            if score:
                results.append(
                    {
                        "doc_id": doc["doc_id"],
                        "doc_type": doc["doc_type"],
                        "filename": doc["filename"],
                        "score": round(score, 4),
                        "matched_text": _snippet(doc.get("text", ""), query),
                        "page": None,
                    }
                )
        return sorted(results, key=lambda r: r["score"], reverse=True)[:limit]


def _snippet(text: str, query: str, width: int = 260) -> str:
    terms = _tokens(query)
    lo = normalize_key(text)
    best = 0
    for term in terms:
        idx = lo.find(term)
        if idx >= 0:
            best = idx
            break
    raw = re.sub(r"\s+", " ", text)
    return raw[max(0, best - width // 2) : best + width // 2]


_INDEX: LexicalIndex | None = None


def search_documents(query: str, filters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    global _INDEX
    if _INDEX is None:
        docs = extract_all_documents(".")
        _INDEX = LexicalIndex(docs)
    return _INDEX.search(query, filters)


def build_index(repo_root: str | Path = ".", output: str | Path = "artifacts/search_index.json") -> dict[str, Any]:
    docs = extract_all_documents(repo_root)
    index = LexicalIndex(docs)
    payload = {
        "documents": [
            {"doc_id": d["doc_id"], "doc_type": d["doc_type"], "filename": d["filename"], "char_count": d.get("char_count")}
            for d in docs
        ],
        "terms": len(index.df),
    }
    out = Path(repo_root) / output
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload

