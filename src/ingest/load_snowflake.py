"""Load Cricsheet match files into Snowflake RAW.MATCHES_JSON.

--mode external  COPY from the S3 external stage, partition dt=<date> (needs setup_stage.sql A)
--mode internal  PUT local files to an internal stage, then COPY (the documented fallback)

Run: python -m src.ingest.load_snowflake --mode internal
"""

from __future__ import annotations

import argparse
import logging
import os

from src.config import RAW_DIR, ROOT
from src.ingest.upload_s3 import partition_date

log = logging.getLogger("crickql.load_snowflake")


def connect():
    import snowflake.connector
    from cryptography.hazmat.primitives import serialization

    key_path = os.environ["SNOWFLAKE_PRIVATE_KEY_PATH"]
    with open(os.path.expanduser(key_path), "rb") as f:
        passphrase = os.getenv("SNOWFLAKE_PRIVATE_KEY_PASSPHRASE")
        key = serialization.load_pem_private_key(
            f.read(), password=passphrase.encode() if passphrase else None
        )
    return snowflake.connector.connect(
        account=os.environ["SNOWFLAKE_ACCOUNT"],
        user=os.environ["SNOWFLAKE_USER"],
        private_key=key.private_bytes(
            serialization.Encoding.DER, serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        ),
        role=os.getenv("SNOWFLAKE_ROLE") or None,
        warehouse=os.getenv("SNOWFLAKE_WAREHOUSE", "DEV_WH"),
        database=os.getenv("SNOWFLAKE_DATABASE", "CRICKQL"),
        schema="RAW",
    )


def split_sql(text: str, stage: str) -> list[str]:
    """Drop comment lines, fill in the stage, split into single statements."""
    body = "\n".join(line for line in text.splitlines() if not line.strip().startswith("--"))
    return [s.strip() for s in body.replace("{stage}", stage).split(";") if s.strip()]


def load(mode: str = "internal", dt: str | None = None) -> int:
    stage = (f"CRICSHEET_S3/dt={dt or partition_date()}/" if mode == "external"
             else "CRICSHEET_INTERNAL")
    statements = split_sql((ROOT / "sql" / "snowflake" / "load_raw.sql").read_text(), stage)
    conn = connect()
    try:
        cur = conn.cursor()
        if mode == "internal":
            src = (RAW_DIR / "ipl").resolve()
            cur.execute(f"PUT 'file://{src}/*.json' @CRICKQL.RAW.CRICSHEET_INTERNAL "
                        "AUTO_COMPRESS = TRUE OVERWRITE = TRUE PARALLEL = 8")
            log.info("PUT %d files", len(cur.fetchall()))
        for sql in statements:
            cur.execute(sql)
        (rows,) = cur.fetchone()
        log.info("RAW.MATCHES_JSON now has %d rows", rows)
        return rows
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--mode", choices=["external", "internal"], default="external")
    parser.add_argument("--dt")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    load(args.mode, args.dt)


if __name__ == "__main__":
    main()
