# CrickQL

Ask a cricket question in plain English. Get the answer, the SQL behind it, and the rule that applies.

> Work in progress. Week 1 of 6: ingest and local load.

## What it will do

- **Pipeline:** Cricsheet IPL ball-by-ball data lands in S3, loads into Postgres and Snowflake, gets modeled with dbt, runs on Airflow.
- **Text-to-SQL:** a Claude agent answers number questions against the marts, with read-only guardrails.
- **RAG:** rule and context questions are answered from the Laws of Cricket and IPL playing conditions, with citations.
- **Router:** decides whether a question needs SQL, documents, or both.
- **Serving:** FastAPI in Docker. One `docker compose up`, no cloud account needed.

## Data source

[Cricsheet](https://cricsheet.org) publishes ball-by-ball match data for exactly this kind of reuse. No scraping.

## Status

| Week | Focus | Status |
|---|---|---|
| 1 | Ingest + local load | In progress |
| 2 | S3, Snowflake, dbt, Airflow | |
| 3 | Text-to-SQL agent + evals | |
| 4 | API, Docker, CI (ship) | |
| 5 | RAG layer | |
| 6 | Router + launch | |
