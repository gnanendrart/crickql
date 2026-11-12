# CrickQL walkthrough: read this before any interview

You did not type this code, so this file is how you get to own it. For each module: what it does, the decision behind it, and the questions an interviewer will ask. Try each question out loud before you read the answer. If you can't answer one, open the file and trace it.

Rule of thumb: if you can't explain a line, change it until you can, or delete it.

---

## 1. download.py: getting the data

**What:** downloads `ipl_json.zip`, unzips it to `data/raw/ipl/`, writes `manifest.json`.

**Decisions**
- Two layers of "skip if unchanged". First a conditional GET: send `If-Modified-Since` and Cricsheet replies 304 with no body. Then, if the server sends the file anyway, compare its sha256 with the last run.
- Write to a temp `.part` file, then rename. A crash mid-download never leaves a half-written zip that looks real.
- `safe_extract` refuses any zip entry whose path escapes the folder (`../../etc/x`). Zip slip is a real attack on any pipeline that unzips files it didn't make.

**Q: Why two checks, not one?** The 304 saves bandwidth when the server cooperates. The hash catches a server that ignores the header, or the same bytes rebuilt with a new date.

## 2. parse.py: JSON to rows

**What:** one match file becomes one match row plus one row per ball.

**Decisions**
- The key is `(match_id, innings, over_no, ball_seq)`. `actual_delivery` ("3.6") repeats whenever a wide or no-ball is re-bowled: 1,240 of 1,243 files. `ball_seq` is the position in the list, so it is always unique.
- `legal_ball` counts only legal balls, and reaches 7 in the 8 matches where an umpire miscounted an over.
- Each extras type gets its own column, because one ball can carry two (`{penalty: 5, wides: 2}`).
- `season_year` is the year of the match date. Cricsheet labels 2008 as "2007/08" and 2020 as "2020/21". Taking the second year of the label would be wrong for 2020.
- `is_non_boundary`: a 4 that was run, or overthrows, is not a boundary four. 29 matches have one.
- `over` is renamed `over_no` because OVER is an SQL keyword. That matters later: the LLM writes SQL against these names.

**Q: How did you handle super overs and no-results?** Flagged, never dropped. Super overs are innings 3+ with `is_super_over`. The marts exclude them by default so season stats aren't inflated, but they stay in `fct_deliveries`. No-results keep their balls with `result_type = 'no result'`.

## 3. validate.py: nine checks, match-level quarantine

**What:** E1-E9 (nulls, duplicate keys, orphans, run arithmetic, the target check, legal balls per over).

**Decisions**
- If any check fails, **the whole match** is held back, not just the bad row. A match missing one ball looks complete and gives wrong totals. A missing match shows up in a count.
- E8 uses Cricsheet's own target as an independent check: first-innings runs + 1 = target. It needs no outside data.
- E9 allows a 5- or 7-ball over only if Cricsheet flagged `miscounted_overs`. It cross-checks the data against its own metadata.

**Q: Why not just drop bad rows?** "The failures I'm best at catching are the ones that don't announce themselves." A dropped ball is exactly that kind of failure.

## 4. guard.py + load_pg.py: loading safely

- Everything happens in one transaction. Either the whole batch lands or none of it does.
- Matches: upsert (`ON CONFLICT DO UPDATE`). `RETURNING (xmax = 0)` tells inserts apart from updates, which is how the audit row knows "new 0, updated 1,243".
- Deliveries: delete then insert per match, not a row upsert. If Cricsheet corrects a match down to fewer balls, an upsert would leave the stale extra rows behind.
- The guard compares the new batch with the last `raw.load_audit` row **before** writing. More than a 5% drop means stop. Cricsheet only ever adds matches, so shrinking means something upstream broke.

**Q: Where does the guard run, and why there?** Before the write, inside load_pg. A guard after the load would just report damage already done.

## 5. dbt: staging, marts, tests

- `base_matches` / `base_deliveries` are the only target-specific SQL. Postgres reads the parsed tables. Snowflake flattens the raw JSON with `LATERAL FLATTEN` (and rebuilds `legal_ball` with a window function). Everything above them is shared.
- Seeds fix naming: 19 team names become 15 franchises (Delhi Daredevils is Delhi Capitals), and 41 venue strings become 37 grounds (Feroz Shah Kotla is Arun Jaitley Stadium).
- Cricket rules live in macros (`is_bowler_wicket`: run outs don't count for the bowler; `is_dismissal`: retired hurt is not out), so every mart counts the same way.
- `bowler_runs_conceded` = bat runs + wides + no-balls. Byes and leg byes are not the bowler's fault.
- `fct_batting_innings` unions batters who faced balls with batters who were run out at the non-striker's end without facing one. Miss that and you lose dismissals.
- Tests: 49 in total, including three singular ones: the innings totals reconcile with the target, raw and fact row counts match, and each season with a final has exactly one champion.

**Q: How do dbt tests catch silent failures?** Show the deleted-ball demo from the runbook: one ball removed, one test fails, the 8 downstream nodes are skipped.

## 6. Airflow DAG

- Airflow only orchestrates. Every task is a CLI command run in a separate venv (`/opt/crickql-venv`). The project's dependencies can't break Airflow's, and any failed task can be re-run by hand with the same command.
- Two real bugs found while testing: dbt hit a file permission error in the mounted folder (fix: dbt logs and build output go to `/tmp` in the container), and Airflow's PYTHONPATH leaked its own protobuf into dbt, which crashed after a successful build (fix: `env -u PYTHONPATH PYTHONNOUSERSITE=1`). Good "tell me about a bug" material.
- Cloud tasks exit 99 (meaning skipped) unless `crickql_cloud=true`, and downstream tasks use `none_failed`, so the Postgres path runs on its own.
- Single-container `airflow standalone`, not the official 7-container compose. One weekly DAG doesn't need Celery.

## 7. The agent

**Flow:** question → Claude (schema card + rules + 15 examples, forced to call the `run_sql` tool) → guardrails → run as `crickql_reader` → rows. On an error, Claude sees the error once and retries (max 2 attempts).

- **Schema card** = the dbt descriptions, read from `manifest.json`. One source of truth. To improve the SQL, improve the docs.
- **Forced tool use** means the output is always a structured `{sql, reasoning}`, never prose with SQL buried in it.
- **Guardrails, layer 1 (sqlglot):** one statement, must be a query, no write nodes anywhere in the tree (that catches a DELETE hidden in a CTE), only `marts` tables, no `pg_sleep` / `pg_read_file` / `dblink`, LIMIT 200 added or capped at 1,000.
- **Guardrails, layer 2 (Postgres):** a read-only role, SELECT on marts only, `default_transaction_read_only`, 10s `statement_timeout`. Tested by hand: blocked from raw, can't CREATE, pg_sleep(11) cancelled.
- **Examples teach patterns, not answers**, and are disjoint from the eval set. Otherwise the eval measures memory.

**Q: How do you stop an LLM writing dangerous SQL?** Two independent layers: a parser that refuses before execution, and a database role that physically can't write. Either one alone should be enough. Both exist because each can have a gap.

## 8. Eval

- Execution accuracy: run the gold and generated SQL and compare the results, not the SQL text.
- Matching: numbers rounded to 2 places, text compared case-insensitively. Every gold column must appear in the generated result (extra columns are fine). Row order counts only for `ordered: true`.
- Tested with an oracle: an agent that returns the gold rows must score 30/30, which proves the harness itself isn't broken.
- `results.md` is written only by the script. **You verify the gold SQL first.** I drafted it, so an accuracy number against unverified gold measures agreement with me, not correctness.

## 9. API and Docker

- `/health` returns 503 when the database or marts are missing, and Docker's healthcheck uses it.
- Errors are structured `{error, detail, request_id}`, and the same request ID is in the logs and the `X-Request-ID` header.
- Compose order: db healthy → seed (exits 0) → api. Seed skips if the marts already exist, so restarts are fast.
- `SEED_MODE=fixtures` works fully offline. CI uses it, which is why the agent tests are written not to depend on any one season.

---

## Known gaps (say these before an interviewer finds them)

1. Snowflake raw load uses the internal stage; the S3 external stage is pending AWS account activation.
2. Players are keyed by printed name, not Cricsheet person ID. Two players with the same short name would merge. The registry IDs are in the raw JSON; that's a good "what I'd do next".
3. Loads are full reloads every run (fast at 1,243 matches). Incremental loads by match_id are the next step at scale.
4. The read-only role has a fixed local password. Fine for Docker on a laptop, not for a hosted deploy.
