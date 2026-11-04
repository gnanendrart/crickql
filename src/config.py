"""Central settings, loaded once from .env."""

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"

CRICSHEET_URL = os.getenv("CRICSHEET_URL", "https://cricsheet.org/downloads/ipl_json.zip")
WAREHOUSE = os.getenv("WAREHOUSE", "pg")

PG_URL = (
    f"postgresql+psycopg2://{os.getenv('PG_USER', '')}:{os.getenv('PG_PASSWORD', '')}"
    f"@{os.getenv('PG_HOST', 'localhost')}:{os.getenv('PG_PORT', '5432')}"
    f"/{os.getenv('PG_DB', 'crickql')}"
)

PG_CONN = {
    "host": os.getenv("PG_HOST", "localhost"),
    "port": int(os.getenv("PG_PORT", "5432")),
    "dbname": os.getenv("PG_DB", "crickql"),
    "user": os.getenv("PG_USER") or None,
    "password": os.getenv("PG_PASSWORD") or None,
}
