import pytest

from api import outcome
from tests.test_agent import needs_db

H06_SQL = (
    "SELECT p.player, p.first_season, SUM(b.wickets) AS debut_season_wickets "
    "FROM marts.dim_players AS p LEFT JOIN marts.mart_bowling_phase AS b "
    "ON b.bowler = p.player AND b.season_year = p.first_season "
    "WHERE p.player ILIKE '%Bradman%' GROUP BY p.player, p.first_season LIMIT 200"
)


def result(columns, rows, sql="SELECT 1"):
    return {"question": "q", "sql": sql, "columns": columns, "rows": rows,
            "row_count": len(rows), "attempts": [], "latency_ms": 1, "ok": True}


class FakeConn:
    """Answers EXISTS lookups from a set of known (kind, value) pairs."""

    def __init__(self, known):
        self.known, self.last = known, None

    def cursor(self):
        return self

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def execute(self, sql, params):
        kind = "player" if "dim_players" in sql else "team"
        self.last = (kind, params[0]) in self.known

    def fetchone(self):
        return (self.last,)

    def rollback(self):
        pass

    def close(self):
        pass


def no_db():
    raise AssertionError("database should not be touched")


@pytest.mark.parametrize("text,reason", [
    ("not answerable: no captain field in Cricsheet", "no captain field in Cricsheet"),
    ("Not answerable - weather is not recorded", "weather is not recorded"),
    ("not answerable", "The question cannot be answered from the CrickQL data."),
])
def test_not_answerable_reason(text, reason):
    assert outcome.not_answerable_reason(["answer"], [[text]]) == reason


def test_normal_rows_are_not_a_refusal():
    assert outcome.not_answerable_reason(["team"], [["Kolkata Knight Riders"]]) is None
    assert outcome.not_answerable_reason(["a", "b"], [["not answerable", 1]]) is None
    assert outcome.not_answerable_reason(["n"], [[5]]) is None


def test_refusal_is_flagged_and_rows_cleared():
    r = outcome.classify(result(["answer"], [["not answerable: writes are not allowed"]]), no_db)
    assert r["status"] == "not_answerable" and r["message"] == "writes are not allowed"
    assert r["rows"] == [] and r["columns"] == [] and r["row_count"] == 0


def test_rows_are_answered_without_a_lookup():
    r = outcome.classify(result(["team"], [["Kolkata Knight Riders"]]), no_db)
    assert r["status"] == "answered" and r["message"] is None and r["missing_entities"] == []


def test_named_entities_from_h06():
    assert outcome.named_entities(H06_SQL) == [
        {"kind": "player", "op": "ILIKE", "value": "%Bradman%"}]


def test_named_entities_eq_in_and_reversed():
    sql = ("SELECT * FROM marts.fct_deliveries WHERE batter = 'V Kohli' "
           "AND bowling_team IN ('Mumbai Indians', 'Chennai Super Kings') "
           "AND 'JJ Bumrah' = bowler AND venue = 'Wankhede Stadium' AND season_year = 2016")
    found = outcome.named_entities(sql)
    assert len(found) == 4  # venue and season_year are not entities
    assert sorted((e["kind"], e["value"]) for e in found) == [
        ("player", "JJ Bumrah"), ("player", "V Kohli"),
        ("team", "Chennai Super Kings"), ("team", "Mumbai Indians")]
    assert all(e["op"] == "=" for e in found)


def test_named_entities_ignores_unparseable_sql():
    assert outcome.named_entities("SELECT FROM WHERE (((") == []


def test_unknown_player_with_zero_rows_says_so():
    r = outcome.classify(result(["player"], [], H06_SQL), lambda: FakeConn(set()))
    assert r["status"] == "unknown_entity"
    assert r["missing_entities"] == [{"kind": "player", "op": "ILIKE", "value": "%Bradman%"}]
    assert "no player matching '%Bradman%'" in r["message"]


def test_known_player_with_zero_rows_is_no_rows():
    sql = "SELECT * FROM marts.mart_batting_season WHERE batter = 'V Kohli' AND season_year = 2007"
    r = outcome.classify(result(["runs"], [], sql), lambda: FakeConn({("player", "V Kohli")}))
    assert r["status"] == "no_rows" and r["missing_entities"] == []


def test_lookup_failure_falls_back_to_no_rows():
    import psycopg2

    def broken():
        raise psycopg2.OperationalError("down")

    r = outcome.classify(result(["player"], [], H06_SQL), broken)
    assert r["status"] == "no_rows"


@needs_db
def test_real_lookup_bradman_missing_kohli_present():
    from src.agent.text_to_sql import reader_conn

    assert outcome.missing_entities(H06_SQL, reader_conn) == [
        {"kind": "player", "op": "ILIKE", "value": "%Bradman%"}]
    sql = "SELECT * FROM marts.fct_deliveries WHERE batter = 'V Kohli' LIMIT 1"
    assert outcome.missing_entities(sql, reader_conn) == []
