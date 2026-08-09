from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.knowledge_base.queries import KnowledgeBase
from src.query.executor import solve_question


def main() -> None:
    questions = json.loads(Path("sample_questions.json").read_text(encoding="utf-8"))["questions"]
    out_path = Path("sample_answers.jsonl")
    report_path = Path("artifacts/reports/sample_debug.json")
    report_path.parent.mkdir(parents=True, exist_ok=True)

    kb = KnowledgeBase("artifacts/bid_intelligence.db")
    answers = []
    debug = []
    for q in questions:
        try:
            result = solve_question(q["question"], kb)
            answer = result["answer"]
            error = None
        except Exception as exc:
            result = {"answer": None, "operation": "error", "evidence": {}}
            answer = None
            error = str(exc)
        answers.append({"qid": q["qid"], "answer": answer})
        if answer != q["answer"]:
            debug.append(
                {
                    "qid": q["qid"],
                    "question": q["question"],
                    "expected": q["answer"],
                    "predicted": answer,
                    "reasoning_plan": result.get("evidence", {}).get("plan"),
                    "resolved_entities": result.get("evidence", {}).get("entities"),
                    "retrieved_documents": result.get("evidence", {}).get("documents"),
                    "values_used": result.get("evidence", {}).get("values"),
                    "calculation": result.get("evidence", {}).get("calculation"),
                    "likely_failure_reason": error or "value mismatch; inspect entity resolution or query logic",
                }
            )
    kb.close()

    out_path.write_text("\n".join(json.dumps(a, ensure_ascii=False) for a in answers) + "\n", encoding="utf-8")
    report_path.write_text(json.dumps(debug, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {out_path}")
    if debug:
        print(f"Wrong answers: {len(debug)}; debug written to {report_path}")
    else:
        print("Wrong answers: 0")

    completed = subprocess.run(
        [sys.executable, "evaluate.py", "--submission", str(out_path), "--per-question"],
        text=True,
        capture_output=True,
        check=False,
    )
    print(completed.stdout)
    if completed.stderr:
        print(completed.stderr, file=sys.stderr)
    if completed.returncode != 0:
        raise SystemExit(completed.returncode)


if __name__ == "__main__":
    main()
