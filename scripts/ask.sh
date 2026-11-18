#!/usr/bin/env bash
# Ask CrickQL one question and print the parts that matter.
#   ./scripts/ask.sh "Who scored the most runs in the 2016 season?"
# Needs the API running (uvicorn or docker compose) plus curl and jq.
set -euo pipefail
API="${CRICKQL_API:-http://localhost:8000}"
curl -s "$API/query" -H 'Content-Type: application/json' \
  -d "$(jq -n --arg q "$1" '{question: $q}')" \
  | jq '{status, message, sql, columns, rows}'
