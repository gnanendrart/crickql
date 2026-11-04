import pytest

from src.agent.guardrails import GuardrailError, check_sql

TABLES = {"fct_matches", "mart_batting_season", "fct_deliveries"}


def ok(sql):
    return check_sql(sql, TABLES)


@pytest.mark.parametrize("sql", [
    "SELECT * FROM mart_batting_season",
    "select batter, sum(runs) from marts.mart_batting_season group by 1 order by 2 desc",
    "WITH t AS (SELECT * FROM fct_matches) SELECT count(*) FROM t",
    "SELECT a.match_id FROM fct_matches a JOIN fct_deliveries d ON d.match_id = a.match_id",
    "SELECT season_year FROM fct_matches UNION SELECT season_year FROM mart_batting_season",
    "SELECT * FROM fct_matches WHERE match_id IN (SELECT match_id FROM fct_deliveries)",
])
def test_valid_selects_pass(sql):
    assert "marts." in ok(sql)


def test_limit_added_when_missing():
    assert ok("SELECT * FROM fct_matches").endswith("LIMIT 200")


def test_existing_small_limit_kept_and_large_limit_capped():
    assert ok("SELECT * FROM fct_matches LIMIT 5").endswith("LIMIT 5")
    assert ok("SELECT * FROM fct_matches LIMIT 999999").endswith("LIMIT 1000")


def test_trailing_semicolon_is_fine():
    ok("SELECT 1 FROM fct_matches;")


@pytest.mark.parametrize("sql, reason", [
    ("DROP TABLE marts.fct_matches", "Only SELECT"),
    ("DELETE FROM fct_matches", "Only SELECT"),
    ("UPDATE fct_matches SET winner = 'x'", "Only SELECT"),
    ("INSERT INTO fct_matches SELECT * FROM fct_matches", "Only SELECT"),
    ("SELECT 1 FROM fct_matches; DROP TABLE fct_matches", "Exactly one statement"),
    ("SELECT * INTO new_t FROM fct_matches", "not allowed"),
    ("SELECT * FROM raw.matches", "Schema 'raw'"),
    ("SELECT * FROM pg_catalog.pg_user", "Schema 'pg_catalog'"),
    ("SELECT * FROM pg_user", "Unknown table"),
    ("SELECT * FROM information_schema.tables", "Schema 'information_schema'"),
    ("SELECT pg_sleep(30) FROM fct_matches", "pg_sleep"),
    ("SELECT pg_read_file('/etc/passwd')", "pg_read_file"),
    ("SELECT current_setting('data_directory')", "current_setting"),
    ("SELECT * FROM dblink('host=x', 'select 1') AS t(a int)", "dblink"),
    ("WITH x AS (DELETE FROM fct_matches RETURNING *) SELECT * FROM x", "not allowed"),
    ("COPY fct_matches TO '/tmp/x'", "Only SELECT"),
    ("", "Empty"),
    ("SELEC * FRM", "does not parse|Only SELECT"),
])
def test_dangerous_or_invalid_sql_refused(sql, reason):
    with pytest.raises(GuardrailError, match=reason):
        ok(sql)
