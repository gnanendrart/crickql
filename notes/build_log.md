# CrickQL Build Log

One line per day: what shipped, what blocked.

| Date | Week/Day | Shipped | Blocked / Notes |
|---|---|---|---|
| 2026-11-02 | W1 D1 | Scaffold: folders, .gitignore, .env.example, pyproject (ruff), requirements, config, README stub | Git init + GitHub repo done on Mac (VM cannot run git here) |
| 2026-11-03 | W1 D2 | download.py: conditional GET (304) + sha256 idempotency, safe unzip, manifest. 1,243 matches, 5.2 MB. Schema notes written | actual_delivery not unique (1,240 files), so PK uses ball_seq. Season labels like 2007/08 need normalizing. Commit on Mac |
| 2026-11-04 | W1 D3 | parse.py: match + delivery rows, PK (match_id, innings, over, ball_seq), per-type extras cols, flags for SO/tie/D/L/no-result/miscounted. Full archive: 1,243 matches, 295,732 deliveries, 0 rejects, 0 dup PKs, 2.1s. Inn-1 total + 1 = target on every non-D/L match | Reject path tested on 3 broken files. 6 no-results have 1 innings, no target. Commit on Mac |
| 2026-11-04 | W1 D4 - W4 D4 (code) | Claude wrote and sandbox-tested Weeks 1-4: validate/load_pg (1,243 matches, 295,732 deliveries), tests, reconcile notebook, S3 + Snowflake loaders, dbt (12 models, 49 tests, PASS=63), Airflow DAG (green dags test), agent + guardrails + 30-q eval harness, FastAPI, Docker compose (seed + api healthy), CI. 63 pytest passing | NOT a checkpoint yet. Each step is ticked only when run on the Mac, see notes/mac_runbook.md. Snowflake SQL syntax-checked only. Eval gold SQL unverified, no accuracy measured |
