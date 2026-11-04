"""Agent loop tests against a real Postgres with built marts. Skipped when none is reachable."""

import psycopg2
import pytest

from src.agent import text_to_sql
from src.agent.text_to_sql import ask, reader_conn, system_prompt
from tests.conftest import MANIFEST, needs_manifest
from tests.fake_claude import FakeClaude


def _db_ready():
    try:
        conn = reader_conn()
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM marts.fct_matches LIMIT 1")
        conn.close()
        return True
    except (psycopg2.Error, FileNotFoundError):
        return False


needs_db = pytest.mark.skipif(
    not MANIFEST.exists() or not _db_ready(),
    reason="needs Postgres with marts and the dbt manifest (run seed.sh or dbt build)",
)


@needs_manifest
def test_system_prompt_contains_schema_rules_and_examples():
    prompt = system_prompt()
    assert "TABLE marts.mart_batting_season" in prompt
    assert "Rules:" in prompt and "<examples>" in prompt


def match_count():
    conn = reader_conn()
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM marts.fct_matches")
        n = cur.fetchone()[0]
    conn.close()
    return n


# These run on the full dataset or the 3-match CI fixtures, so they never assume a season.
@needs_db
def test_good_sql_first_try():
    fake = FakeClaude(["SELECT count(*) AS matches FROM fct_matches"])
    out = ask("How many matches are there?", client=fake)
    assert out["ok"] and out["rows"] == [[match_count()]]
    assert len(out["attempts"]) == 1 and out["sql"].endswith("LIMIT 200")
    assert "marts.fct_matches" in out["sql"]
    assert fake.calls[0]["tool_choice"] == {"type": "tool", "name": "run_sql"}


@needs_db
def test_db_error_is_fed_back_and_fixed():
    fake = FakeClaude([
        "SELECT count(champion) FROM marts.fct_matches",  # no such column
        "SELECT count(*) FROM marts.fct_matches",
    ])
    out = ask("How many matches are there?", client=fake)
    assert out["ok"] and len(out["attempts"]) == 2 and out["rows"] == [[match_count()]]
    assert "champion" in out["attempts"][0]["error"]
    retry_msg = fake.calls[1]["messages"][-1]["content"][0]
    assert retry_msg["type"] == "tool_result" and retry_msg["is_error"]


@needs_db
def test_guardrail_refusal_is_fed_back_and_never_executed():
    fake = FakeClaude(["DROP TABLE marts.fct_matches", "DELETE FROM marts.fct_matches"])
    out = ask("Delete everything", client=fake)
    assert not out["ok"] and len(out["attempts"]) == 2
    assert "Only SELECT" in out["error"]
    conn = reader_conn()
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM marts.fct_matches")
        assert cur.fetchone()[0] > 0
    conn.close()


def test_model_is_configurable():
    assert text_to_sql.SQL_MODEL


@needs_db
def test_eval_harness_scores_an_oracle_at_100_percent():
    """If the agent returned exactly the gold rows, the harness must report 30/30."""
    import yaml

    from evals.run_sql_eval import EVAL_FILE, run
    from src.agent.guardrails import check_sql
    from src.agent.schema_context import table_names
    from src.agent.text_to_sql import execute

    questions = yaml.safe_load(EVAL_FILE.read_text())["questions"]
    gold = {q["question"]: q["gold_sql"] for q in questions}

    def oracle(question, conn_factory):
        cols, rows = execute(check_sql(gold[question], table_names()), conn_factory)
        return {"ok": True, "rows": rows, "attempts": [{}], "sql": gold[question]}

    summary = run(agent=oracle, write=False)
    assert summary["correct"] == summary["questions"] == 30
