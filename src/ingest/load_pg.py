"""Load parsed, validated rows into the Postgres raw schema.

- matches: upsert on match_id (INSERT ... ON CONFLICT DO UPDATE).
- deliveries: replaced per match inside the same transaction (DELETE for the incoming
  match_ids, then INSERT). A plain upsert would leave stale rows behind if Cricsheet
  ever corrects a match and it ends up with fewer deliveries.
- One audit row per run in raw.load_audit.
Everything happens in one transaction: either the whole batch lands or none of it does.

Run: python -m src.ingest.load_pg   (parses, validates and loads everything in data/raw/ipl)
"""

from __future__ import annotations

import json
import logging

import psycopg2
from psycopg2.extras import execute_values

from src.config import PG_CONN, RAW_DIR, ROOT
from src.ingest.guard import check_row_counts, last_loaded_counts
from src.ingest.parse import parse_dir
from src.ingest.validate import validate

log = logging.getLogger("crickql.load_pg")

DDL_PATH = ROOT / "sql" / "postgres" / "raw_schema.sql"

MATCH_COLS = (
    "match_id", "season_raw", "season_year", "match_date", "event_name", "match_number",
    "stage", "team1", "team2", "toss_winner", "toss_decision", "venue", "city", "result_type",
    "winner", "win_by_runs", "win_by_wickets", "method", "decided_by_super_over",
    "target_runs", "target_overs", "player_of_match", "scheduled_overs", "balls_per_over",
    "innings_count", "has_super_over", "has_miscounted_over", "data_version", "source_file",
)
DELIVERY_COLS = (
    "match_id", "innings", "over_no", "ball_seq", "legal_ball", "actual_delivery",
    "batting_team", "bowling_team", "is_super_over", "batter", "bowler", "non_striker",
    "runs_batter", "runs_extras", "runs_total", "is_non_boundary", "extras_wides", "extras_noballs",
    "extras_byes", "extras_legbyes", "extras_penalty", "is_legal", "wicket_count",
    "wicket_kind", "player_out", "fielders",
)


def connect():
    return psycopg2.connect(**{k: v for k, v in PG_CONN.items() if v is not None})


def ensure_schema(conn) -> None:
    with conn.cursor() as cur:
        cur.execute(DDL_PATH.read_text())


def load(matches: list[dict], deliveries: list[dict], rejected: int = 0,
         parsed: int | None = None, guard: bool = True) -> dict:
    manifest = RAW_DIR / "manifest.json"
    sha = json.loads(manifest.read_text()).get("sha256") if manifest.exists() else None
    updates = ", ".join(f"{c} = EXCLUDED.{c}" for c in MATCH_COLS[1:])

    with connect() as conn, conn.cursor() as cur:
        if guard:  # before ensure_schema, so a first run on an empty database still works
            check_row_counts(len(matches), len(deliveries), last_loaded_counts(cur))
        ensure_schema(conn)
        flags = execute_values(
            cur,
            f"INSERT INTO raw.matches ({', '.join(MATCH_COLS)}) VALUES %s "
            f"ON CONFLICT (match_id) DO UPDATE SET {updates}, _loaded_at = now() "
            "RETURNING (xmax = 0)",
            [tuple(m[c] for c in MATCH_COLS) for m in matches],
            page_size=1000,
            fetch=True,
        )
        inserted = sum(1 for (is_new,) in flags if is_new)

        cur.execute("DELETE FROM raw.deliveries WHERE match_id = ANY(%s)",
                    ([m["match_id"] for m in matches],))
        execute_values(
            cur,
            f"INSERT INTO raw.deliveries ({', '.join(DELIVERY_COLS)}) VALUES %s",
            [tuple(d[c] for c in DELIVERY_COLS) for d in deliveries],
            page_size=5000,
        )

        cur.execute("SELECT (SELECT count(*) FROM raw.matches), "
                    "(SELECT count(*) FROM raw.deliveries)")
        n_matches, n_deliveries = cur.fetchone()
        stats = {
            "source_sha256": sha,
            "matches_parsed": parsed if parsed is not None else len(matches) + rejected,
            "matches_rejected": rejected,
            "matches_inserted": inserted,
            "matches_updated": len(matches) - inserted,
            "deliveries_loaded": len(deliveries),
            "matches_total": n_matches,
            "deliveries_total": n_deliveries,
        }
        cur.execute(
            f"INSERT INTO raw.load_audit ({', '.join(stats)}) "
            f"VALUES ({', '.join(['%s'] * len(stats))})",
            tuple(stats.values()),
        )
    conn.close()
    log.info("loaded: %s", stats)
    return stats


def run(limit: int | None = None) -> dict:
    matches, deliveries, parse_rejects = parse_dir(limit=limit)
    result = validate(matches, deliveries)
    log.info("validation: %s", result.summary())
    return load(
        result.good_matches,
        result.good_deliveries,
        rejected=parse_rejects + len(result.rejected_match_ids),
        parsed=len(matches) + parse_rejects,
    )


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    run()


if __name__ == "__main__":
    main()
