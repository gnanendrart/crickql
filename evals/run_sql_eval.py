"""Execution-accuracy eval for the text-to-SQL agent.

For each question in evals/sql_eval.yaml: run the gold SQL, ask the agent, run its SQL, and
compare the two result sets.

Matching rule (stated so the number means something):
- Values are normalised: numbers rounded to 2 decimals, text lower-cased and trimmed.
- Every gold column must appear in the generated result (same values, same row count). Extra
  generated columns are allowed, because "Who scored most?" answered with name + runs is right.
- Row order matters only when the question is marked `ordered: true`.
- For `ordered: true` questions (rankings, "who has the most", "highest", "lowest") the gold
  rows must be the FIRST rows of the generated result. Extra rows after them are allowed,
  because "Who scored most?" answered with the top 5 is still right, and it shows ties the gold
  LIMIT 1 hides. Unordered questions still need the exact row count.
  (Scorer v2, 2026-11-16. The baseline row in results.md was scored before this rule.)

Results: a summary row appended to evals/results.md and full detail in evals/runs/<ts>.json.
Never edit results.md by hand: every number in it must come from a run.

Run: python -m evals.run_sql_eval [--only q01 q02] [--label "baseline"]
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import time
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import yaml

from src.agent.guardrails import check_sql
from src.agent.schema_context import table_names
from src.agent.text_to_sql import SQL_MODEL, ask, execute, reader_conn

EVAL_DIR = Path(__file__).parent
EVAL_FILE = EVAL_DIR / "sql_eval.yaml"
RESULTS_MD = EVAL_DIR / "results.md"
RUNS_DIR = EVAL_DIR / "runs"

log = logging.getLogger("crickql.eval")


def norm(v):
    if isinstance(v, bool) or v is None:
        return v
    if isinstance(v, int | float | Decimal):
        return round(float(v), 2)
    if isinstance(v, str):
        try:
            return round(float(v), 2)
        except ValueError:
            return v.strip().lower()
    return str(v).strip().lower()


def columns_of(rows: list[list]) -> list[tuple]:
    return [tuple(norm(r[i]) for r in rows) for i in range(len(rows[0]))] if rows else []


def results_match(gold_rows: list[list], gen_rows: list[list], ordered: bool = False) -> bool:
    """True if every gold column is present in the generated result with the same values."""
    if ordered and len(gen_rows) > len(gold_rows):
        gen_rows = gen_rows[:len(gold_rows)]  # top-N answer: only the leading rows are scored
    if len(gold_rows) != len(gen_rows):
        return False
    if not gold_rows:
        return True
    gold_cols, gen_cols = columns_of(gold_rows), columns_of(gen_rows)
    if ordered:
        remaining = list(gen_cols)
        for col in gold_cols:
            if col not in remaining:
                return False
            remaining.remove(col)
        return True
    # Order-insensitive: find gen columns covering every gold column, then check that the
    # rows line up as a multiset when projected onto those columns.
    used: list[int] = []
    for col in gold_cols:
        match = next((j for j, g in enumerate(gen_cols)
                      if j not in used and Counter(g) == Counter(col)), None)
        if match is None:
            return False
        used.append(match)
    gold_set = Counter(tuple(norm(v) for v in row) for row in gold_rows)
    gen_set = Counter(tuple(norm(row[j]) for j in used) for row in gen_rows)
    return gold_set == gen_set


def run(only: list[str] | None = None, label: str = "", agent=ask, conn_factory=reader_conn,
        write: bool = True) -> dict:
    questions = yaml.safe_load(EVAL_FILE.read_text())["questions"]
    if only:
        questions = [q for q in questions if q["id"] in only]
    allowed = table_names()
    details = []
    for q in questions:
        _, gold_rows = execute(check_sql(q["gold_sql"], allowed), conn_factory)
        started = time.perf_counter()
        try:
            out = agent(q["question"], conn_factory=conn_factory)
        except Exception as e:  # an API error counts as a miss, not a crash of the whole run
            out = {"ok": False, "rows": [], "attempts": [], "error": f"{type(e).__name__}: {e}"}
        correct = bool(out["ok"]) and results_match(gold_rows, out["rows"], q.get("ordered", False))
        details.append({
            "id": q["id"], "category": q.get("category"), "question": q["question"],
            "verified": q.get("verified", False), "correct": correct,
            "attempts": len(out.get("attempts", [])), "error": out.get("error"),
            "sql": out.get("sql"), "gold_rows": gold_rows[:5], "rows": out.get("rows", [])[:5],
            "latency_ms": round((time.perf_counter() - started) * 1000),
        })
        log.info("%s %s %s", q["id"], "PASS" if correct else "FAIL", q["question"])

    n = len(details)
    n_correct = sum(d["correct"] for d in details)
    summary = {
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "label": label, "model": os.getenv("SQL_MODEL", SQL_MODEL), "questions": n,
        "correct": n_correct, "accuracy_pct": round(100 * n_correct / n, 1) if n else 0.0,
        "unverified_gold": sum(not d["verified"] for d in details),
        "recovered_by_retry": sum(d["correct"] and d["attempts"] > 1 for d in details),
        "failed_ids": [d["id"] for d in details if not d["correct"]],
    }
    if write:
        RUNS_DIR.mkdir(exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        (RUNS_DIR / f"{stamp}.json").write_text(
            json.dumps({"summary": summary, "details": details}, indent=2, default=str))
        if not RESULTS_MD.exists() or "| Run |" not in RESULTS_MD.read_text():
            RESULTS_MD.write_text(
                "# Eval results\n\nEvery row below was written by an eval script. "
                "Never by hand.\n\n## Text-to-SQL (execution accuracy)\n\n"
                "| Run | Label | Model | Correct | Accuracy | Recovered by retry "
                "| Unverified gold | Failed |\n|---|---|---|---|---|---|---|---|\n")
        with RESULTS_MD.open("a") as f:
            f.write(f"| {summary['timestamp']} | {label} | {summary['model']} | "
                    f"{n_correct}/{n} | {summary['accuracy_pct']}% | "
                    f"{summary['recovered_by_retry']} | {summary['unverified_gold']} | "
                    f"{', '.join(summary['failed_ids']) or 'none'} |\n")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--only", nargs="+", help="question ids to run")
    parser.add_argument("--label", default="", help="short note for this run, e.g. 'baseline'")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    s = run(args.only, args.label)
    print(json.dumps(s, indent=2))
    if s["unverified_gold"]:
        print(f"\nWARNING: {s['unverified_gold']} gold queries are not verified yet. "
              "Do not quote this accuracy until they are.")


if __name__ == "__main__":
    main()
