# Mac runbook: Weeks 1-4 checkpoints

Claude wrote the Weeks 1-4 code on Nov 4, 2026 and tested it in a cloud sandbox. **None of it counts until it runs on your Mac and you log it.** Work top to bottom. Each step ends in something you can see. If a step fails, stop and fix it (or ask Claude) before moving on.

Keep the daily drill. One build day of checkpoints per session is fine. The point is that you run, read and can explain each piece.

---

## 0. Setup (15 min)

```bash
cd ~/data-projects/projects/crickql
conda activate data-eng
pip install -r requirements.txt
createdb crickql                      # skip if it exists
cp .env.example .env                  # PG_USER = your Mac user, PG_PASSWORD blank for Homebrew
ruff check . && pytest -q             # DB tests skip until step 1
```

**Checkpoint:** ruff clean, pytest shows passes and skips, no failures.

## 1. W1 D4: Validate and load

```bash
python -m src.ingest.load_pg
psql crickql -c "select count(*) from raw.matches" -c "select count(*) from raw.deliveries"
python -m src.ingest.load_pg          # second run: matches_updated should equal the total, inserted 0
```

**Checkpoint:** counts in the build log. Sandbox numbers were 1,243 and 295,732. Yours may be higher if Cricsheet has added matches since.

**Break it on purpose:** in `validate.py`, find E6 and change one delivery's `runs_total` in a Python shell before calling `validate()`. Watch the whole match get quarantined. Read `data/rejects.log`.

## 2. W1 D5: Tests and reconciliation

```bash
pytest -q
jupyter notebook notebooks/01_reconcile_kaggle_vs_cricsheet.ipynb   # run all cells
```

**Checkpoint:** pytest green. **You write the Findings cell** from the numbers the notebook prints. Expectation from the sandbox: Cricsheet through 2024 has exactly 1,095 matches and 260,920 deliveries, the same as your Kaggle load, so the gap should be the 2025 and 2026 seasons only. Confirm or refute it with your real Kaggle tables. If anything else differs, that is your interview story.

## 3. W2 D1-D2: Cloud accounts, S3, Snowflake

Follow the brief's W2 D1 (Snowflake trial check, S3 bucket, $5 billing alarm, Anthropic spend limit). Then:

```bash
# .env: S3_BUCKET, AWS_PROFILE, SNOWFLAKE_*
python -m src.ingest.upload_s3                 # run twice: second run uploads 0, skips all
# Snowflake worksheet: run sql/snowflake/setup_stage.sql (option A, or B if IAM fights you)
python -m src.ingest.load_snowflake --mode external    # or --mode internal (fallback)
```

**Checkpoint:** `SELECT count(*) FROM CRICKQL.RAW.MATCHES_JSON` = file count. If Snowflake is gone, log "pg only" and skip to step 4. The brief allows it.

## 4. W2 D3-D4: dbt

```bash
set -a; source .env; set +a
dbt build --project-dir dbt --profiles-dir dbt --target pg
dbt build --project-dir dbt --profiles-dir dbt --target snowflake    # if Snowflake is on
```

**Checkpoint:** PASS=63 on pg.

**The Snowflake models are NOT run-tested.** The sandbox has no Snowflake account. `base_matches.sql` and `base_deliveries.sql` (the `LATERAL FLATTEN` part) only passed a Snowflake syntax parse. Expect to fix something the first time. Compare `select count(*) from MARTS.FCT_DELIVERIES` with Postgres; they must match.

**Break it on purpose:** delete one ball, rebuild, watch `assert_innings_totals_match_target` fail, then reload:
```bash
psql crickql -c "delete from raw.deliveries where match_id=1082591 and innings=1 and over_no=19 and ball_seq=6"
dbt build --project-dir dbt --profiles-dir dbt --target pg     # 1 FAIL, 8 SKIP
python -m src.ingest.load_pg && dbt build --project-dir dbt --profiles-dir dbt --target pg
```

## 5. W2 D5: Airflow

```bash
cd airflow && docker compose up --build        # first build ~5 min, image ~3 GB
# http://localhost:8080 -> crickql_weekly -> Trigger
```

**Checkpoint:** one green run, screenshot to `docs/img/airflow_dag.png`. upload_s3, load_snowflake and dbt_build_snowflake show as skipped (pink) until you set the Airflow Variable `crickql_cloud` = `true`. Then trigger again for the full run.

Note: the DAG reaches your Mac's Postgres through `host.docker.internal`. If Homebrew Postgres refuses the connection, add `host all all 0.0.0.0/0 trust` to `pg_hba.conf` (local dev only) and `listen_addresses = '*'` in `postgresql.conf`, then `brew services restart postgresql@15`.

## 6. W3: Agent and eval

```bash
psql crickql -f sql/postgres/roles.sql
python -m src.agent.schema_context | less      # read it: is this enough for a stranger?
python -m src.agent.text_to_sql "Who has the best death-over economy since 2020, min 120 balls?"
```

Then the part only you can do:

1. **Verify the 30 gold queries** in `evals/sql_eval.yaml`. For each one, ask: does this SQL answer the question the way a cricket fan means it? Fix any you disagree with, then set `verified: true`. (q12 Rashid vs Dhoni = 1 is worth a sanity check. So are q07 and q18.)
2. Run the baseline: `python -m evals.run_sql_eval --label baseline`
3. Read every failure in `evals/runs/<latest>.json`. Classify it (schema confusion, wrong grain, missing filter, ambiguous question).
4. Fix with column descriptions in `dbt/models/marts/_marts.yml` or `src/agent/examples.yaml`, **never by special-casing an eval question**. Rebuild dbt so the manifest updates, then re-run with `--label "after <fix>"`.

**Checkpoint:** before and after rows in `evals/results.md`. Real numbers only.

## 7. W4: API, Docker, CI, ship

```bash
uvicorn api.main:app --reload       # http://localhost:8000/docs, try 3 questions
docker compose up --build           # repo root; api on :8000, db on :5433
```

**Checkpoints:**
- Fresh clone in `/tmp`, `docker compose up --build`, one curl question answered
- Push to a branch, open a PR, CI green
- Record the 30-60s demo GIF (Swagger or curl)
- Fill the README Results table from `evals/results.md`. **Rewrite any README sentence that doesn't sound like you**
- W4 D5: repo public, pinned, resume line with real numbers

The ship gate is passed only when the public URL is in the build log. Week 5 does not start before that.
