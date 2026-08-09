from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.knowledge_base.queries import KnowledgeBase
from src.query.executor import solve_question


def main() -> None:
    parser = argparse.ArgumentParser(description="Answer BITS bid-intelligence questions.")
    parser.add_argument("--questions", help="JSON file containing a questions array")
    parser.add_argument("--output", help="JSONL output path")
    parser.add_argument("--question", help="Single natural-language question")
    parser.add_argument("--db", default="artifacts/bid_intelligence.db")
    args = parser.parse_args()

    kb = KnowledgeBase(args.db)
    try:
        if args.question:
            result = solve_question(args.question, kb)
            print(json.dumps({"answer": result["answer"]}, ensure_ascii=False))
            return

        if not args.questions or not args.output:
            parser.error("batch mode requires --questions and --output, or use --question")

        payload = json.loads(Path(args.questions).read_text(encoding="utf-8"))
        questions = payload.get("questions", payload if isinstance(payload, list) else [])
        out_rows = []
        evidence_rows = []
        for item in questions:
            qid = item.get("qid", "QUESTION")
            result = solve_question(item["question"], kb)
            out_rows.append({"qid": qid, "answer": result["answer"]})
            evidence_rows.append({"qid": qid, **result})

        output = Path(args.output)
        output.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in out_rows) + "\n", encoding="utf-8")
        evidence_path = output.with_suffix(output.suffix + ".evidence.json")
        evidence_path.write_text(json.dumps(evidence_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    finally:
        kb.close()


if __name__ == "__main__":
    main()

