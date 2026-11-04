"""Data quality checks on parsed matches and deliveries, run before anything is loaded.

Quarantine happens at the match grain: if any check fails for a match, the whole match
(its row and all its deliveries) is held back and written to data/rejects.log. A partial
match in the warehouse is worse than a missing one, because it looks complete.

Checks:
  E1  required match fields not null
  E2  required delivery fields not null
  E3  no duplicate match_id
  E4  no duplicate (match_id, innings, over_no, ball_seq)
  E5  every delivery belongs to a parsed match (orphans)
  E6  runs_total = runs_batter + runs_extras on every delivery
  E7  runs_extras = sum of the five extras columns on every delivery
  E8  innings-1 total + 1 = target runs (normal and tie results; D/L targets are revised)
  E9  an over other than the last of an innings has 6 legal balls, unless Cricsheet
      flagged the match with miscounted_overs (an umpire error the data records)
"""

from __future__ import annotations

import logging
from collections import Counter, defaultdict
from dataclasses import dataclass, field

from src.ingest.parse import EXTRA_TYPES, REJECTS_LOG

log = logging.getLogger("crickql.validate")

MATCH_REQUIRED = ("match_id", "match_date", "season_year", "team1", "team2", "result_type")
DELIVERY_REQUIRED = (
    "match_id", "innings", "over_no", "ball_seq", "batting_team", "bowling_team",
    "batter", "bowler", "non_striker", "runs_batter", "runs_extras", "runs_total",
)


@dataclass
class ValidationResult:
    good_matches: list[dict]
    good_deliveries: list[dict]
    failures: dict[str, list[str]] = field(default_factory=dict)  # check -> sample messages
    rejected_match_ids: set = field(default_factory=set)

    @property
    def passed(self) -> bool:
        return not self.rejected_match_ids

    def summary(self) -> str:
        if self.passed:
            return "all 9 checks passed"
        parts = [f"{k}: {len(v)} failures" for k, v in sorted(self.failures.items())]
        return f"{len(self.rejected_match_ids)} matches quarantined ({'; '.join(parts)})"


def validate(matches: list[dict], deliveries: list[dict]) -> ValidationResult:
    bad: dict[object, list[str]] = defaultdict(list)  # match_id -> reasons
    failures: dict[str, list[str]] = defaultdict(list)

    def fail(check: str, match_id, msg: str) -> None:
        bad[match_id].append(f"{check} {msg}")
        failures[check].append(f"{match_id}: {msg}")

    # E1 / E3
    seen = Counter(m.get("match_id") for m in matches)
    for m in matches:
        for col in MATCH_REQUIRED:
            if m.get(col) is None:
                fail("E1", m.get("match_id"), f"match.{col} is null")
        if seen[m.get("match_id")] > 1:
            fail("E3", m.get("match_id"), "duplicate match_id")
    by_id = {m["match_id"]: m for m in matches}

    # E2 / E4 / E5 / E6 / E7, plus aggregates for E8 / E9
    keys = Counter()
    inn1_runs: dict = defaultdict(int)
    legal_per_over: dict = defaultdict(int)
    last_over: dict = defaultdict(int)
    for d in deliveries:
        mid = d.get("match_id")
        for col in DELIVERY_REQUIRED:
            if d.get(col) is None:
                fail("E2", mid, f"delivery.{col} is null at {d.get('innings')}/{d.get('over_no')}")
        key = (mid, d["innings"], d["over_no"], d["ball_seq"])
        keys[key] += 1
        if keys[key] == 2:
            fail("E4", mid, f"duplicate delivery key {key[1:]}")
        if mid not in by_id:
            fail("E5", mid, "delivery has no parent match")
        if d["runs_total"] != d["runs_batter"] + d["runs_extras"]:
            fail("E6", mid, f"runs_total mismatch at {key[1:]}")
        if d["runs_extras"] != sum(d[f"extras_{t}"] for t in EXTRA_TYPES):
            fail("E7", mid, f"extras columns do not sum at {key[1:]}")
        if d["innings"] == 1:
            inn1_runs[mid] += d["runs_total"]
        legal_per_over[(mid, d["innings"], d["over_no"])] += bool(d["is_legal"])
        last_over[(mid, d["innings"])] = max(last_over[(mid, d["innings"])], d["over_no"])

    # E8
    for mid, m in by_id.items():
        target = m.get("target_runs")
        if target and m["result_type"] in ("normal", "tie") and inn1_runs[mid] + 1 != target:
            fail("E8", mid, f"innings 1 = {inn1_runs[mid]} but target = {target}")

    # E9
    for (mid, inn, over_no), n in legal_per_over.items():
        flagged = by_id.get(mid, {}).get("has_miscounted_over")
        if n != 6 and over_no != last_over[(mid, inn)] and not flagged:
            fail("E9", mid, f"over {over_no} of innings {inn} has {n} legal balls, not flagged")

    rejected = set(bad)
    if rejected:
        REJECTS_LOG.parent.mkdir(parents=True, exist_ok=True)
        with REJECTS_LOG.open("a") as f:
            for mid in sorted(rejected, key=str):
                f.write(f"{mid}\tVALIDATION: {'; '.join(bad[mid][:5])}\n")
    for check, msgs in sorted(failures.items()):
        log.warning("%s failed %d times, e.g. %s", check, len(msgs), msgs[0])

    return ValidationResult(
        good_matches=[m for m in matches if m["match_id"] not in rejected],
        good_deliveries=[d for d in deliveries if d["match_id"] not in rejected],
        failures=dict(failures),
        rejected_match_ids=rejected,
    )
