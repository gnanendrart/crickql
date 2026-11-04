"""End-of-run data quality summary: last load, rejects, mart row counts. Written to
data/dq_summary.md and printed, so every DAG run leaves a human-readable receipt.

Run: python -m src.ingest.dq_summary
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from src.config import DATA_DIR
from src.ingest.load_pg import connect

log = logging.getLogger("crickql.dq")

MARTS = ("fct_matches", "fct_deliveries", "fct_batting_innings", "mart_batting_season",
         "mart_bowling_phase", "mart_team_season", "dim_players", "dim_venues")


def summary() -> str:
    with connect() as conn, conn.cursor() as cur:
        cur.execute("SELECT run_id, loaded_at, matches_parsed, matches_rejected, matches_inserted, "
                    "matches_updated, matches_total, deliveries_total "
                    "FROM raw.load_audit ORDER BY run_id DESC LIMIT 1")
        run = cur.fetchone()
        cur.execute("SELECT max(season_year), count(*) FROM marts.fct_matches")
        latest_season, n_matches = cur.fetchone()
        counts = {}
        for t in MARTS:
            cur.execute(f"SELECT count(*) FROM marts.{t}")
            counts[t] = cur.fetchone()[0]
    lines = [
        f"# CrickQL DQ summary, {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC",
        "",
        f"- Load run {run[0]} at {run[1]:%Y-%m-%d %H:%M}: parsed {run[2]}, rejected {run[3]}, "
        f"new {run[4]}, updated {run[5]}",
        f"- Raw totals: {run[6]} matches, {run[7]} deliveries",
        f"- Marts: {n_matches} matches through season {latest_season}",
        "",
        "| table | rows |",
        "|---|---|",
        *[f"| {t} | {n:,} |" for t, n in counts.items()],
    ]
    if run[6] != n_matches:
        lines.append(f"\n**WARNING:** raw has {run[6]} matches but marts have {n_matches}.")
    return "\n".join(lines) + "\n"


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    text = summary()
    (DATA_DIR / "dq_summary.md").write_text(text)
    print(text)


if __name__ == "__main__":
    main()
