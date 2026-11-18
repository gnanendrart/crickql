"""Classify an agent result for the API: answered, not answerable, unknown entity or no rows.

Two cases used to come back looking like a normal answer:
- The model refuses by returning SELECT 'not answerable: <reason>' (a valid SELECT), so the
  API returned it as a one-row table.
- A query that filters on a player or team that does not exist returns 0 rows, and an empty
  table reads as "the answer is nothing" (holdout h06: a player who never played IPL).

This module runs after the agent, so the prompt and the eval scorer are unchanged.
"""

from __future__ import annotations

from collections.abc import Callable

import psycopg2
import sqlglot
from sqlglot import exp

ANSWERED = "answered"
NOT_ANSWERABLE = "not_answerable"
UNKNOWN_ENTITY = "unknown_entity"
NO_ROWS = "no_rows"

PLAYER_COLUMNS = {"player", "batter", "bowler", "non_striker", "player_out", "player_of_match"}
TEAM_COLUMNS = {"team", "team1", "team2", "batting_team", "bowling_team", "winner", "toss_winner"}

# Each lookup takes (operator, value) and returns True if at least one row matches.
LOOKUP_SQL = {
    "player": "SELECT EXISTS (SELECT 1 FROM marts.dim_players WHERE player {op} %s)",
    "team": "SELECT EXISTS (SELECT 1 FROM marts.mart_team_season WHERE team {op} %s)",
}


def not_answerable_reason(columns: list[str], rows: list[list]) -> str | None:
    """The reason text if the result is the model's 'not answerable: ...' row, else None."""
    if len(rows) != 1 or len(rows[0]) != 1 or not isinstance(rows[0][0], str):
        return None
    text = rows[0][0].strip()
    if not text.lower().startswith("not answerable"):
        return None
    reason = text[len("not answerable"):].lstrip(" :-").strip()
    return reason or "The question cannot be answered from the CrickQL data."


def named_entities(sql: str) -> list[dict]:
    """Player and team literals the query filters on, e.g. player ILIKE '%Bradman%'.

    Returns [{"kind": "player"|"team", "op": "="|"ILIKE", "value": str}], de-duplicated.
    Only plain `column <op> 'literal'` and `column IN ('a', 'b')` filters count.
    """
    try:
        tree = sqlglot.parse_one(sql, read="postgres")
    except sqlglot.errors.ParseError:
        return []
    found: list[dict] = []

    def add(column: exp.Expression, literal: exp.Expression, op: str) -> None:
        if not isinstance(column, exp.Column) or not isinstance(literal, exp.Literal):
            return
        if not literal.is_string:
            return
        name = column.name.lower()
        kind = "player" if name in PLAYER_COLUMNS else "team" if name in TEAM_COLUMNS else None
        if kind:
            item = {"kind": kind, "op": op, "value": literal.this}
            if item not in found:
                found.append(item)

    for node in tree.find_all(exp.EQ, exp.Like, exp.ILike, exp.In):
        if isinstance(node, exp.In):
            for value in node.expressions:
                add(node.this, value, "=")
            continue
        op = "=" if isinstance(node, exp.EQ) else "ILIKE"
        add(node.this, node.expression, op)
        add(node.expression, node.this, op)  # 'V Kohli' = batter
    return found


def missing_entities(sql: str, conn_factory: Callable) -> list[dict]:
    """Entities in the query that match nothing in the warehouse. [] if the lookup fails."""
    entities = named_entities(sql)
    if not entities:
        return []
    try:
        conn = conn_factory()
    except psycopg2.Error:
        return []
    missing = []
    try:
        with conn.cursor() as cur:
            for e in entities:
                cur.execute(LOOKUP_SQL[e["kind"]].format(op=e["op"]), (e["value"],))
                if not cur.fetchone()[0]:
                    missing.append(e)
        conn.rollback()
    except psycopg2.Error:
        return []
    finally:
        conn.close()
    return missing


def classify(result: dict, conn_factory: Callable) -> dict:
    """Add status, message and missing_entities to a successful agent result."""
    out = {**result, "status": ANSWERED, "message": None, "missing_entities": []}
    reason = not_answerable_reason(result["columns"], result["rows"])
    if reason is not None:
        return {**out, "status": NOT_ANSWERABLE, "message": reason,
                "columns": [], "rows": [], "row_count": 0}
    if result["row_count"] > 0:
        return out
    missing = missing_entities(result["sql"] or "", conn_factory)
    if missing:
        names = "; ".join(f"no {m['kind']} matching '{m['value']}'" for m in missing)
        return {**out, "status": UNKNOWN_ENTITY, "missing_entities": missing,
                "message": f"0 rows: {names} in IPL data (2008-2026). Players use Cricsheet "
                           "short names such as 'V Kohli'; teams use current franchise names."}
    return {**out, "status": NO_ROWS,
            "message": "The query ran and matched 0 rows."}
