# Eval results

Every row below was written by an eval script. Never by hand.

## Text-to-SQL (execution accuracy)

| Run | Label | Model | Correct | Accuracy | Recovered by retry | Unverified gold | Failed |
|---|---|---|---|---|---|---|---|
| 2026-11-16 15:52 UTC | baseline | claude-sonnet-5-5 | 14/30 | 46.7% | 0 | 0 | q01, q04, q06, q07, q08, q09, q13, q16, q17, q18, q19, q21, q25, q27, q28, q29 |
| 2026-11-16 15:57 UTC | scorer-v2 | claude-sonnet-5-5 | 29/30 | 96.7% | 0 | 0 | q27 |
| 2026-11-16 15:58 UTC | scorer-v2 + wide_balls | claude-sonnet-5-5 | 30/30 | 100.0% | 0 | 0 | none |
| 2026-11-16 18:00 UTC | [sql_eval_holdout] holdout v1 | claude-sonnet-5-5 | 11/12 | 91.7% | 0 | 0 | h06 |
