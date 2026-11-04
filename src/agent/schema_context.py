"""Build the text-to-SQL agent's schema card from the dbt manifest.

The card is the only thing the model knows about the data, and it comes straight from the
dbt model and column descriptions. Better docs in dbt/models/marts/_marts.yml mean better SQL;
there is no second copy of the schema to keep in sync.

Run: python -m src.agent.schema_context   (prints the card; needs `dbt parse` or `dbt build` first)
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from src.config import ROOT

MANIFEST = ROOT / "dbt" / "target" / "manifest.json"
SCHEMA = "marts"
# Order matters: the model reads top to bottom, so the tables most questions need come first.
TABLE_ORDER = (
    "mart_batting_season", "mart_bowling_phase", "mart_team_season", "fct_matches",
    "fct_batting_innings", "fct_deliveries", "dim_players", "dim_venues",
)


def load_models(manifest_path: Path = MANIFEST) -> dict[str, dict]:
    if not manifest_path.exists():
        raise FileNotFoundError(
            f"{manifest_path} not found. "
            "Run `dbt parse --project-dir dbt --profiles-dir dbt` first."
        )
    nodes = json.loads(manifest_path.read_text())["nodes"]
    return {
        n["name"]: n for n in nodes.values()
        if n["resource_type"] == "model" and n["config"].get("schema") == SCHEMA
    }


def table_card(node: dict) -> str:
    lines = [f"TABLE {SCHEMA}.{node['name']}", f"  {' '.join(node['description'].split())}"]
    for col in node["columns"].values():
        desc = " ".join(col.get("description", "").split())
        lines.append(f"  - {col['name']}: {desc}")
    return "\n".join(lines)


@lru_cache(maxsize=1)
def schema_card(manifest_path: Path = MANIFEST) -> str:
    models = load_models(manifest_path)
    ordered = [m for m in TABLE_ORDER if m in models] + sorted(set(models) - set(TABLE_ORDER))
    return "\n\n".join(table_card(models[name]) for name in ordered)


def table_names(manifest_path: Path = MANIFEST) -> set[str]:
    return set(load_models(manifest_path))


if __name__ == "__main__":
    card = schema_card()
    print(card)
    print(f"\n[{len(card):,} characters, ~{len(card) // 4:,} tokens]")
