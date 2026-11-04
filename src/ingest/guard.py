"""Silent-failure guard: refuse to load a batch that is much smaller than the last good load.

Cricsheet only ever adds matches. If a new pull parses to noticeably fewer matches or
deliveries than are already loaded, something upstream broke (truncated archive, schema
change, parser regression) and the pipeline should stop loudly instead of loading it.
"""

from __future__ import annotations

import logging

log = logging.getLogger("crickql.guard")

MAX_DROP = 0.05  # fail if counts fall more than 5% against the last load


class RowCountDropError(RuntimeError):
    pass


def last_loaded_counts(cur) -> tuple[int, int] | None:
    cur.execute("SELECT to_regclass('raw.load_audit') IS NOT NULL")
    if not cur.fetchone()[0]:
        return None
    cur.execute("SELECT matches_total, deliveries_total FROM raw.load_audit "
                "ORDER BY run_id DESC LIMIT 1")
    return cur.fetchone()


def check_row_counts(new_matches: int, new_deliveries: int,
                     previous: tuple[int, int] | None, max_drop: float = MAX_DROP) -> None:
    if not previous:
        log.info("guard: no previous load, nothing to compare")
        return
    for name, new, old in (("matches", new_matches, previous[0]),
                           ("deliveries", new_deliveries, previous[1])):
        if old and new < old * (1 - max_drop):
            raise RowCountDropError(
                f"{name} dropped from {old} to {new} ({(old - new) / old:.1%}), "
                f"more than the {max_drop:.0%} limit. Load aborted, nothing was written."
            )
    log.info("guard: ok (%d matches, %d deliveries vs %s)", new_matches, new_deliveries, previous)
