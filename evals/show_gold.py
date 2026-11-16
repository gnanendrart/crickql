"""Run every gold query (no API calls) and print question, SQL and result for manual review.

Use this on W3 D4 to verify the gold set before the baseline. Read each result as a cricket
fan: is this the answer you'd expect? If yes, flip `verified: true` in sql_eval.yaml.

Run: python -m evals.show_gold [--only q07 q12] > notes/gold_review.md
     python -m evals.show_gold --file evals/sql_eval_holdout.yaml > notes/holdout_review.md
"""

from __future__ import annotations

import argparse
from pathlib import Path

import yaml

from evals.run_sql_eval import EVAL_FILE
from src.agent.guardrails import check_sql
from src.agent.schema_context import table_names
from src.agent.text_to_sql import execute, reader_conn


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", nargs="+", help="question ids to show")
    parser.add_argument("--file", default=str(EVAL_FILE), help="question file")
    args = parser.parse_args()

    questions = yaml.safe_load(Path(args.file).read_text())["questions"]
    if args.only:
        questions = [q for q in questions if q["id"] in args.only]
    allowed = table_names()

    print("# Gold query review\n")
    for q in questions:
        print(f"## {q['id']} ({q['category']}) verified={q.get('verified')}\n")
        print(f"**Q:** {q['question']}\n")
        if q.get("expect") == "not_answerable":
            print("Expect: not answerable (no gold SQL)\n")
            continue
        print("```sql\n" + q["gold_sql"].strip() + "\n```\n")
        try:
            _, rows = execute(check_sql(q["gold_sql"], allowed), reader_conn)
            shown = rows[:10]
            print("Result" + (f" (first 10 of {len(rows)})" if len(rows) > 10 else "") + ":\n")
            for r in shown:
                print(f"- {list(r)}")
        except Exception as e:  # show the failure, keep going
            print(f"**ERROR:** {type(e).__name__}: {e}")
        print("\nVerdict: [ ] correct  [ ] fix: ___\n")


if __name__ == "__main__":
    main()
