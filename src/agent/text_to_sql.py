"""Text-to-SQL agent: question -> Claude -> guardrails -> read-only execution -> rows.

Flow for one question:
1. Claude gets the schema card (from dbt docs), the rules and 15 worked examples, and must
   answer by calling the `run_sql` tool (forced tool use, so the output is always one SQL string).
2. The SQL goes through src/agent/guardrails.py. A refusal is sent back to Claude as a tool error.
3. The SQL runs as crickql_reader (read-only, marts only, 10s timeout).
4. On a guardrail refusal or a database error, Claude sees the error and gets one more try
   (max 2 attempts). Every attempt is logged and returned.

Run: python -m src.agent.text_to_sql "Who scored the most runs in 2016?"
"""

from __future__ import annotations

import argparse
import datetime as dt
import decimal
import json
import logging
import os
import time
from functools import lru_cache
from typing import Any

import psycopg2
import yaml

from src.agent.guardrails import GuardrailError, check_sql
from src.agent.schema_context import schema_card, table_names
from src.config import PG_CONN, ROOT

log = logging.getLogger("crickql.agent")

SQL_MODEL = os.getenv("SQL_MODEL", "claude-sonnet-5-5")
MAX_ATTEMPTS = 2
EXAMPLES_PATH = ROOT / "src" / "agent" / "examples.yaml"

RULES = """\
Rules:
- Write one PostgreSQL SELECT. Use only the tables listed above, always as marts.<table>.
- Prefer the mart tables. Use fct_deliveries only when no mart has the grain you need.
- Seasons are season_year (e.g. 2016). Teams use current franchise names
  ('Delhi Capitals', 'Punjab Kings', 'Royal Challengers Bengaluru').
- Player names are Cricsheet short names: Virat Kohli = 'V Kohli', Rohit Sharma = 'RG Sharma',
  MS Dhoni = 'MS Dhoni', Jasprit Bumrah = 'JJ Bumrah', AB de Villiers = 'AB de Villiers'.
  If you are not sure of the short name, filter with ILIKE on the surname and return the name
  column so the answer shows who matched.
- For career numbers, SUM the counts across seasons, then recompute rates from the sums.
- For "best" rate stats (strike rate, economy, average) apply a sensible minimum (e.g. 500 balls
  for a career batting strike rate, 300 legal balls for a career economy) and return the
  volume column so the threshold is visible.
- Round rates to 2 decimals. Return only the columns needed to answer, with clear aliases.
- If the question cannot be answered from these tables, still call run_sql with
  SELECT 'not answerable: <reason>' AS answer.
"""

RUN_SQL_TOOL = {
    "name": "run_sql",
    "description": "Run one read-only PostgreSQL SELECT against the CrickQL marts and return rows.",
    "input_schema": {
        "type": "object",
        "properties": {
            "sql": {"type": "string", "description": "A single PostgreSQL SELECT statement."},
            "reasoning": {
                "type": "string",
                "description": "One sentence: which table(s) and filters answer the question.",
            },
        },
        "required": ["sql"],
    },
}


@lru_cache(maxsize=1)
def load_examples() -> list[dict]:
    return yaml.safe_load(EXAMPLES_PATH.read_text())["examples"]


def system_prompt() -> str:
    shots = "\n\n".join(f"Q: {e['question']}\nSQL:\n{e['sql'].strip()}" for e in load_examples())
    return (
        "You answer questions about IPL cricket (2008 onwards) by writing SQL for a "
        "PostgreSQL warehouse built from Cricsheet ball-by-ball data.\n\n"
        f"<schema>\n{schema_card()}\n</schema>\n\n{RULES}\n"
        f"<examples>\n{shots}\n</examples>"
    )


def reader_conn():
    conn = psycopg2.connect(**{
        **{k: v for k, v in PG_CONN.items() if v is not None},
        "user": os.getenv("PG_READER_USER", "crickql_reader"),
        "password": os.getenv("PG_READER_PASSWORD", "crickql_reader"),
    })
    conn.set_session(readonly=True, autocommit=False)
    return conn


def _jsonable(v: Any) -> Any:
    if isinstance(v, decimal.Decimal):
        return float(v)
    if isinstance(v, dt.date | dt.datetime):
        return v.isoformat()
    return v


def execute(sql: str, conn_factory=reader_conn) -> tuple[list[str], list[list]]:
    conn = conn_factory()
    try:
        with conn.cursor() as cur:
            cur.execute("SET LOCAL statement_timeout = '10s'")
            cur.execute(sql)
            columns = [c.name for c in cur.description]
            rows = [[_jsonable(v) for v in row] for row in cur.fetchall()]
        conn.rollback()  # read-only: never commit anything
        return columns, rows
    finally:
        conn.close()


def _client():
    import anthropic

    return anthropic.Anthropic()


def ask(question: str, client=None, conn_factory=reader_conn,
        max_attempts: int = MAX_ATTEMPTS) -> dict:
    """Answer a question with SQL. Returns sql, columns, rows, attempts and latency."""
    client = client or _client()
    allowed = table_names()
    messages: list[dict] = [{"role": "user", "content": question}]
    attempts: list[dict] = []
    started = time.perf_counter()

    for attempt in range(1, max_attempts + 1):
        response = client.messages.create(
            model=SQL_MODEL,
            max_tokens=1500,
            system=system_prompt(),
            tools=[RUN_SQL_TOOL],
            tool_choice={"type": "tool", "name": "run_sql"},
            messages=messages,
        )
        call = next(b for b in response.content if b.type == "tool_use")
        raw_sql = call.input.get("sql", "")
        record = {"attempt": attempt, "sql": raw_sql, "reasoning": call.input.get("reasoning")}
        try:
            safe_sql = check_sql(raw_sql, allowed)
            columns, rows = execute(safe_sql, conn_factory)
        except (GuardrailError, psycopg2.Error) as e:
            error = str(e).strip().splitlines()[0] if str(e).strip() else type(e).__name__
            record["error"] = error
            attempts.append(record)
            log.warning("attempt %d failed: %s", attempt, error)
            messages += [
                {"role": "assistant", "content": response.content},
                {"role": "user", "content": [{
                    "type": "tool_result", "tool_use_id": call.id, "is_error": True,
                    "content": f"The query failed: {error}\nFix the SQL and call run_sql again.",
                }]},
            ]
            continue
        record["executed_sql"] = safe_sql
        attempts.append(record)
        return {
            "question": question, "sql": safe_sql, "columns": columns, "rows": rows,
            "row_count": len(rows), "attempts": attempts, "ok": True,
            "latency_ms": round((time.perf_counter() - started) * 1000),
        }

    return {
        "question": question, "sql": attempts[-1]["sql"] if attempts else None,
        "columns": [], "rows": [], "row_count": 0, "attempts": attempts, "ok": False,
        "error": attempts[-1].get("error") if attempts else "no attempt made",
        "latency_ms": round((time.perf_counter() - started) * 1000),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("question")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    print(json.dumps(ask(args.question), indent=2)[:4000])


if __name__ == "__main__":
    main()
