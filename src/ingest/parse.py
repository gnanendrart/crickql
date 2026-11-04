"""Parse one Cricsheet match JSON into a match row and a list of delivery rows.

Design notes (see notes/cricsheet_schema.md):
- Delivery key is (match_id, innings, over, ball_seq). `actual_delivery` repeats on
  wides and no-balls, so it is kept as an attribute, never as a key.
- Every edge case is flagged, never silently dropped: super overs, ties, D/L, no-results,
  miscounted overs, multi-type extras.
- Malformed files raise ParseError. parse_dir() logs them to data/rejects.log and moves on.

Run: python -m src.ingest.parse [--limit N] [--files a.json b.json]
"""

from __future__ import annotations

import argparse
import json
import logging
from collections import Counter
from datetime import date
from pathlib import Path

from src.config import DATA_DIR, RAW_DIR

log = logging.getLogger("crickql.parse")

MATCH_DIR = RAW_DIR / "ipl"
REJECTS_LOG = DATA_DIR / "rejects.log"
EXTRA_TYPES = ("wides", "noballs", "byes", "legbyes", "penalty")
ILLEGAL = ("wides", "noballs")


class ParseError(ValueError):
    """Raised when a match file is missing data the pipeline cannot do without."""


def _require(d: dict, key: str, where: str):
    if key not in d or d[key] in (None, "", []):
        raise ParseError(f"missing '{key}' in {where}")
    return d[key]


def _result_type(outcome: dict) -> str:
    if outcome.get("result") == "no result":
        return "no result"
    if outcome.get("result") == "tie":
        return "tie"
    if "method" in outcome:
        return "dl"
    if "winner" in outcome:
        return "normal"
    raise ParseError(f"unrecognised outcome {outcome}")


def parse_match(path: Path) -> tuple[dict, list[dict]]:
    path = Path(path)
    try:
        doc = json.loads(path.read_text())
    except json.JSONDecodeError as e:
        raise ParseError(f"invalid JSON: {e}") from e

    info = _require(doc, "info", "top level")
    match_id = int(path.stem) if path.stem.isdigit() else path.stem
    teams = _require(info, "teams", "info")
    if len(teams) != 2:
        raise ParseError(f"expected 2 teams, got {teams}")
    match_date = date.fromisoformat(_require(info, "dates", "info")[0])
    outcome = info.get("outcome", {})
    result_type = _result_type(outcome)
    by = outcome.get("by", {})
    event = info.get("event", {})
    toss = info.get("toss", {})
    innings_list = doc.get("innings", [])

    target = next((i["target"] for i in innings_list if "target" in i), {})

    match = {
        "match_id": match_id,
        "season_raw": str(_require(info, "season", "info")),
        # Cricsheet labels some seasons '2007/08', '2009/10', '2020/21'. The IPL never
        # crosses a new year, so the year of the match date is the season.
        "season_year": match_date.year,
        "match_date": match_date,
        "event_name": event.get("name"),
        "match_number": event.get("match_number"),
        "stage": event.get("stage"),
        "team1": teams[0],
        "team2": teams[1],
        "toss_winner": toss.get("winner"),
        "toss_decision": toss.get("decision"),
        "venue": info.get("venue"),
        "city": info.get("city"),
        "result_type": result_type,
        "winner": outcome.get("winner") or outcome.get("eliminator"),
        "win_by_runs": by.get("runs"),
        "win_by_wickets": by.get("wickets"),
        "method": outcome.get("method"),
        "decided_by_super_over": "eliminator" in outcome,
        "target_runs": target.get("runs"),
        "target_overs": target.get("overs"),
        "player_of_match": ", ".join(info.get("player_of_match", [])) or None,
        "scheduled_overs": info.get("overs"),
        "balls_per_over": info.get("balls_per_over", 6),
        "innings_count": len(innings_list),
        "has_super_over": any(i.get("super_over") for i in innings_list),
        "has_miscounted_over": any("miscounted_overs" in i for i in innings_list),
        "data_version": doc.get("meta", {}).get("data_version"),
        "source_file": path.name,
    }

    deliveries: list[dict] = []
    for inn_no, inn in enumerate(innings_list, start=1):
        batting = _require(inn, "team", f"innings {inn_no}")
        if batting not in teams:
            raise ParseError(f"innings {inn_no} team '{batting}' not in {teams}")
        bowling = teams[1] if batting == teams[0] else teams[0]
        is_super = bool(inn.get("super_over"))

        for over in inn.get("overs", []):
            over_no = over["over"]
            legal = 0
            for seq, d in enumerate(over.get("deliveries", []), start=1):
                extras = d.get("extras", {})
                unknown = set(extras) - set(EXTRA_TYPES)
                if unknown:
                    raise ParseError(f"unknown extras {unknown} at {inn_no}/{over_no}/{seq}")
                is_legal = not any(k in extras for k in ILLEGAL)
                legal += is_legal
                wickets = d.get("wickets", [])
                if len(wickets) > 1:
                    log.warning("%s: %d wickets on one ball, keeping first in row, all in count",
                                path.name, len(wickets))
                w = wickets[0] if wickets else {}
                runs = _require(d, "runs", f"delivery {inn_no}/{over_no}/{seq}")
                deliveries.append({
                    "match_id": match_id,
                    "innings": inn_no,
                    "over": over_no,  # 0-based, as Cricsheet stores it
                    "ball_seq": seq,  # every delivery, including wides and no-balls
                    "legal_ball": legal if is_legal else None,
                    "actual_delivery": d.get("actual_delivery"),
                    "batting_team": batting,
                    "bowling_team": bowling,
                    "is_super_over": is_super,
                    "batter": d["batter"],
                    "bowler": d["bowler"],
                    "non_striker": d["non_striker"],
                    "runs_batter": runs["batter"],
                    "runs_extras": runs["extras"],
                    "runs_total": runs["total"],
                    **{f"extras_{k}": extras.get(k, 0) for k in EXTRA_TYPES},
                    "is_legal": is_legal,
                    "wicket_count": len(wickets),
                    "wicket_kind": w.get("kind"),
                    "player_out": w.get("player_out"),
                    "fielders": ", ".join(f.get("name", "?") for f in w.get("fielders", []))
                    or None,
                })
    return match, deliveries


def parse_dir(directory: Path = MATCH_DIR, files: list[Path] | None = None,
              limit: int | None = None) -> tuple[list[dict], list[dict], int]:
    """Parse many files. Returns (matches, deliveries, reject_count)."""
    paths = files or sorted(directory.glob("*.json"))
    if limit:
        paths = paths[:limit]
    matches, deliveries, rejects = [], [], 0
    for p in paths:
        try:
            m, ds = parse_match(p)
        except (ParseError, KeyError, TypeError, ValueError) as e:
            rejects += 1
            REJECTS_LOG.parent.mkdir(parents=True, exist_ok=True)
            with REJECTS_LOG.open("a") as f:
                f.write(f"{Path(p).name}\t{type(e).__name__}: {e}\n")
            log.warning("rejected %s: %s", Path(p).name, e)
            continue
        matches.append(m)
        deliveries.extend(ds)
    return matches, deliveries, rejects


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--limit", type=int, help="parse only the first N files")
    parser.add_argument("--files", nargs="+", help="match file names inside data/raw/ipl")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    files = [MATCH_DIR / f for f in args.files] if args.files else None
    matches, deliveries, rejects = parse_dir(files=files, limit=args.limit)
    log.info("parsed %d matches, %d deliveries, %d rejected",
             len(matches), len(deliveries), rejects)
    log.info("result types: %s", dict(Counter(m["result_type"] for m in matches)))


if __name__ == "__main__":
    main()
