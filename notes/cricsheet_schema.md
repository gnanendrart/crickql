# Cricsheet JSON Schema Notes

Source: `ipl_json.zip`, pulled 2026-11-03 (Last-Modified 2026-10-07). 1,243 match files, all `data_version` 1.2.0.
Each file is one match, named `<match_id>.json`. The archive also has `README.txt` and `LICENSE.txt`.

## Top level

`{ "meta": {...}, "info": {...}, "innings": [...] }`

- **meta:** `data_version`, `created`, `revision`

## info block (one row in `raw.matches`)

| Field | Shape | Notes |
|---|---|---|
| `dates` | list of `YYYY-MM-DD` | Use `dates[0]` as match date |
| `season` | string or int | **Not always a year.** `2007/08`, `2009/10`, `2020/21` appear alongside `2017`. Normalize to a `season_year` int, keep the raw label |
| `event` | `{name, match_number}` or `{name, stage}` | Playoff matches carry a stage instead of a number |
| `teams` | list of 2 | |
| `toss` | `{winner, decision}` | decision is `bat` or `field` |
| `outcome` | see below | Four shapes in this archive |
| `venue`, `city` | string | City can be missing on older files |
| `overs`, `balls_per_over` | int | 20 and 6 |
| `player_of_match` | list | Missing on no-results |
| `players` | `{team: [names]}` | Playing XI |
| `registry.people` | `{name: cricsheet_id}` | Stable person IDs. Use these as player keys later, names are not unique |
| `officials` | `{umpires, tv_umpires, reserve_umpires, match_referees}` | |

### Outcome shapes (counts from the full archive)

| Keys | Count | Meaning |
|---|---|---|
| `winner`, `by` | 1,195 | Normal result. `by` is `{runs: n}` or `{wickets: n}` |
| `winner`, `by`, `method` | 23 | Rain-affected. `method` is `D/L` |
| `result`, `eliminator` | 16 | Tie decided by super over. `result` = `tie`, `eliminator` = super over winner |
| `result` | 9 | `no result` |

## innings / overs / deliveries (rows in `raw.deliveries`)

`innings[]` keys: `team`, `overs`, `powerplays`, `target`, plus optional `super_over`, `miscounted_overs`, `absent_hurt`

- `overs[]` is `{over: 0-based int, deliveries: [...]}`
- Each delivery: `batter`, `bowler`, `non_striker`, `runs {batter, extras, total}`, `actual_delivery`, plus optional `extras`, `wickets`, `review`, `replacements`
- `target` on the chasing innings: `{overs, runs}`. On D/L matches the overs are reduced (e.g. `{overs: 6, runs: 48}`)
- `powerplays`: `[{from: 0.1, to: 5.6, type: "mandatory"}]`

### Key finding for Day 4: `actual_delivery` is not unique

`actual_delivery` (e.g. `"3.6"`) repeats inside an innings whenever a wide or no-ball is re-bowled. **1,240 of 1,243 files** have a duplicate. The delivery key must be a sequence number from list position:

- `ball_seq`: 1-based index of the delivery within the over, counting every delivery including wides and no-balls
- `legal_ball`: count of legal deliveries so far in the over (wides and no-balls do not advance it)
- Primary key: `(match_id, innings, over, ball_seq)`

## extras

`extras` dict on the delivery, keys seen: `wides` 9,876 · `legbyes` 4,406 · `noballs` 1,226 · `byes` 745 · `penalty` 2.
A delivery can have more than one key (`{"penalty": 5, "wides": 2}` in match 729309). Store each type as its own column, not a single `extras_type`.

## wickets

`wickets` is a **list** `[{kind, player_out, fielders: [{name}]}]`. Never more than one per ball in this archive, but the schema allows it, so the parser should iterate, not take `[0]`.

Kinds: caught 9,321 · bowled 2,460 · run out 1,194 · lbw 883 · caught and bowled 410 · stumped 388 · hit wicket 20 · retired hurt 19 · retired out 6 · obstructing the field 4.
`retired hurt` is not a dismissal for bowling or batting averages. Flag it, do not count it.

## super overs

16 matches (same 16 as the tie outcomes). Innings 3 and 4 carry `"super_over": true` and 1 over each. Flag them with `is_super_over` so match totals and player stats exclude them by default.

## other edge cases

- **No-results (9):** innings can be very short (e.g. 5 and 4 overs). Keep them, flag with `result_type = 'no result'`
- **miscounted_overs (8 files):** umpire bowled 5 or 7 legal balls in an over, e.g. `{"11": {"balls": 7, "umpire": "NJ Llong"}}`. Validation must not assume 6 legal balls per over. Good interview story: the data records an umpire error
- **review (492 files):** DRS reviews `{by, umpire, batter, decision, type}`. Out of scope for Week 1, worth a stretch table later
- **replacements (331 files):** includes `impact_player` substitutions from 2023 on. Means a team can field 12 players. Matters for player-level stats
