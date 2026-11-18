from fastapi.testclient import TestClient

import api.main as main
from tests.conftest import needs_manifest
from tests.test_agent import needs_db

client = TestClient(main.app)

FAKE_RESULT = {
    "question": "Who won in 2014?", "ok": True,
    "sql": "SELECT team FROM marts.mart_team_season WHERE season_year = 2014 LIMIT 200",
    "columns": ["team"], "rows": [["Kolkata Knight Riders"]], "row_count": 1,
    "attempts": [{"attempt": 1, "sql": "SELECT ...", "executed_sql": "SELECT ..."}],
    "latency_ms": 12,
}


def test_query_returns_sql_rows_and_attempts(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")
    monkeypatch.setattr(main, "ask", lambda q: {**FAKE_RESULT, "question": q})
    r = client.post("/query", json={"question": "Who won in 2014?"})
    assert r.status_code == 200
    body = r.json()
    assert body["rows"] == [["Kolkata Knight Riders"]] and body["attempts"][0]["attempt"] == 1
    assert "X-Request-ID" in r.headers


def test_answered_has_status(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")
    monkeypatch.setattr(main, "ask", lambda q: {**FAKE_RESULT, "question": q})
    body = client.post("/query", json={"question": "Who won in 2014?"}).json()
    assert body["status"] == "answered" and body["message"] is None


def test_not_answerable_is_flagged(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")
    monkeypatch.setattr(main, "ask", lambda q: {
        **FAKE_RESULT, "sql": "SELECT 'not answerable: writes are not allowed' AS answer LIMIT 200",
        "columns": ["answer"], "rows": [["not answerable: writes are not allowed"]]})
    r = client.post("/query", json={"question": "Drop the fct_matches table"})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "not_answerable" and body["message"] == "writes are not allowed"
    assert body["rows"] == [] and body["row_count"] == 0


def test_unknown_player_is_flagged(monkeypatch):
    from tests.test_outcome import H06_SQL, FakeConn

    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")
    monkeypatch.setattr(main, "reader_conn", lambda: FakeConn(set()))
    monkeypatch.setattr(main, "ask", lambda q: {
        **FAKE_RESULT, "sql": H06_SQL, "columns": ["player"], "rows": [], "row_count": 0})
    body = client.post("/query", json={"question": "Bradman debut wickets?"}).json()
    assert body["status"] == "unknown_entity"
    assert body["missing_entities"][0]["value"] == "%Bradman%"


def test_failed_sql_is_a_structured_422(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")
    monkeypatch.setattr(main, "ask", lambda q: {**FAKE_RESULT, "ok": False,
                                                "error": "Only SELECT queries are allowed"})
    r = client.post("/query", json={"question": "drop everything"})
    assert r.status_code == 422 and r.json()["error"] == "sql_failed"
    assert r.json()["request_id"]


def test_missing_api_key_is_503(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    r = client.post("/query", json={"question": "Who won in 2014?"})
    assert r.status_code == 503 and r.json()["error"] == "not_configured"


def test_question_validation():
    assert client.post("/query", json={"question": ""}).status_code == 422
    assert client.post("/query", json={}).status_code == 422


@needs_manifest
def test_schema_endpoint():
    r = client.get("/schema")
    assert r.status_code == 200 and "marts.fct_matches" in r.json()["schema_card"]


@needs_db
def test_health_ok_with_database():
    r = client.get("/health")
    assert r.status_code == 200 and r.json()["marts"] and r.json()["matches"] > 0
