#!/usr/bin/env bash
# Seed the Docker database so a fresh clone works with no cloud account.
#
#   SEED_MODE=full      download the real Cricsheet IPL archive (public, ~5 MB)  [default]
#   SEED_MODE=fixtures  3 committed sample matches, fully offline (used by CI)
#   SEED_FORCE=1        reseed even if data is already loaded
#
# Steps: load raw -> dbt build (models + tests) -> read-only role for the agent.
set -euo pipefail
cd "$(dirname "$0")/.."

MODE="${SEED_MODE:-full}"
DBT="dbt --no-use-colors"

echo "[seed] waiting for Postgres at ${PG_HOST:-localhost}:${PG_PORT:-5432}"
python - <<'EOF'
import time, psycopg2
from src.config import PG_CONN
for _ in range(60):
    try:
        psycopg2.connect(**{k: v for k, v in PG_CONN.items() if v is not None}).close()
        break
    except psycopg2.OperationalError:
        time.sleep(1)
else:
    raise SystemExit("Postgres never came up")
EOF

already_loaded=$(python - <<'EOF'
import psycopg2
from src.config import PG_CONN
with psycopg2.connect(**{k: v for k, v in PG_CONN.items() if v is not None}) as c, c.cursor() as cur:
    cur.execute("SELECT to_regclass('marts.fct_matches') IS NOT NULL")
    print("yes" if cur.fetchone()[0] else "no")
EOF
)
if [[ "$already_loaded" == "yes" && "${SEED_FORCE:-0}" != "1" ]]; then
    echo "[seed] marts already built, skipping (set SEED_FORCE=1 to reseed)"
    exit 0
fi

mkdir -p data/raw/ipl
if [[ "$MODE" == "fixtures" ]]; then
    echo "[seed] fixtures mode: 3 sample matches"
    cp tests/fixtures/*.json data/raw/ipl/
else
    echo "[seed] full mode: downloading Cricsheet IPL archive"
    python -m src.ingest.download
fi

python -m src.ingest.load_pg
$DBT build --project-dir dbt --profiles-dir dbt --target pg

echo "[seed] creating read-only role crickql_reader"
python - <<'EOF'
import psycopg2
from src.config import PG_CONN, ROOT
with psycopg2.connect(**{k: v for k, v in PG_CONN.items() if v is not None}) as c, c.cursor() as cur:
    cur.execute((ROOT / "sql" / "postgres" / "roles.sql").read_text())
EOF
echo "[seed] done"
