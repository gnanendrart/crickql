# CrickQL Build Log

One line per day: what shipped, what blocked.

| Date | Week/Day | Shipped | Blocked / Notes |
|---|---|---|---|
| 2026-11-02 | W1 D1 | Scaffold: folders, .gitignore, .env.example, pyproject (ruff), requirements, config, README stub | Git init + GitHub repo done on Mac (VM cannot run git here) |
| 2026-11-03 | W1 D2 | download.py: conditional GET (304) + sha256 idempotency, safe unzip, manifest. 1,243 matches, 5.2 MB. Schema notes written | actual_delivery not unique (1,240 files), so PK uses ball_seq. Season labels like 2007/08 need normalizing. Commit on Mac |
