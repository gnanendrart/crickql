"""CrickQL API.

GET  /health   database reachable, marts built, agent configured
GET  /schema   the schema card the agent sees (generated from dbt docs)
POST /query    {"question": "..."} -> {status, message, sql, columns, rows, attempts, latency_ms}

status is one of:
  answered        rows answer the question
  not_answerable  the model declined; message has the reason, rows are empty
  unknown_entity  0 rows because a named player or team is not in the data; message says which
  no_rows         the query ran and matched nothing

Run: uvicorn api.main:app --reload    then open http://localhost:8000/docs
"""

from __future__ import annotations

import logging
import os
import time
import uuid

import psycopg2
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from api.outcome import classify
from src.agent.schema_context import schema_card
from src.agent.text_to_sql import SQL_MODEL, ask, reader_conn

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("crickql.api")

app = FastAPI(
    title="CrickQL",
    version="0.5.0",
    description="Ask IPL cricket questions in plain English. Answers come from SQL over a dbt "
    "warehouse built from Cricsheet ball-by-ball data. The SQL runs read-only.",
)


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=500,
                          examples=["Who scored the most runs in the 2016 season?"])


class Attempt(BaseModel):
    attempt: int
    sql: str
    reasoning: str | None = None
    error: str | None = None
    executed_sql: str | None = None


class MissingEntity(BaseModel):
    kind: str
    op: str
    value: str


class QueryResponse(BaseModel):
    question: str
    status: str = Field(..., examples=["answered"],
                        description="answered | not_answerable | unknown_entity | no_rows")
    message: str | None = None
    missing_entities: list[MissingEntity] = []
    sql: str | None
    columns: list[str]
    rows: list[list]
    row_count: int
    attempts: list[Attempt]
    latency_ms: int


class ErrorResponse(BaseModel):
    error: str
    detail: str
    request_id: str


def error(status: int, code: str, detail: str, request: Request) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content=ErrorResponse(error=code, detail=detail,
                              request_id=request.state.request_id).model_dump(),
    )


@app.middleware("http")
async def log_requests(request: Request, call_next):
    request.state.request_id = uuid.uuid4().hex[:12]
    started = time.perf_counter()
    response = await call_next(request)
    response.headers["X-Request-ID"] = request.state.request_id
    log.info("%s %s %s %dms id=%s", request.method, request.url.path, response.status_code,
             (time.perf_counter() - started) * 1000, request.state.request_id)
    return response


@app.get("/health")
def health():
    checks = {"database": False, "marts": False, "anthropic_key": bool(
        os.getenv("ANTHROPIC_API_KEY")), "model": SQL_MODEL}
    try:
        conn = reader_conn()
        checks["database"] = True
        with conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM marts.fct_matches")
            checks["matches"] = cur.fetchone()[0]
            checks["marts"] = True
        conn.close()
    except psycopg2.Error as e:
        checks["error"] = str(e).splitlines()[0]
    ok = checks["database"] and checks["marts"]
    return JSONResponse(status_code=200 if ok else 503,
                        content={"status": "ok" if ok else "degraded", **checks})


@app.get("/schema", response_model=dict)
def schema():
    return {"schema_card": schema_card()}


@app.post("/query", response_model=QueryResponse,
          responses={422: {"model": ErrorResponse}, 502: {"model": ErrorResponse},
                     503: {"model": ErrorResponse}})
def query(body: QueryRequest, request: Request):
    if not os.getenv("ANTHROPIC_API_KEY"):
        return error(503, "not_configured", "ANTHROPIC_API_KEY is not set.", request)
    try:
        result = ask(body.question)
    except psycopg2.OperationalError as e:
        return error(503, "database_unavailable", str(e).splitlines()[0], request)
    except Exception as e:  # Anthropic API errors, network failures
        log.exception("query failed id=%s", request.state.request_id)
        return error(502, "upstream_error", f"{type(e).__name__}: {e}", request)
    if not result["ok"]:
        return error(422, "sql_failed",
                     f"No valid SQL after {len(result['attempts'])} attempts: {result['error']}",
                     request)
    result = classify(result, reader_conn)
    return QueryResponse(**{k: result[k] for k in QueryResponse.model_fields})
