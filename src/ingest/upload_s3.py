"""Upload the extracted Cricsheet match files to the S3 raw landing zone.

Layout: s3://<S3_BUCKET>/cricsheet/ipl/dt=YYYY-MM-DD/<match_id>.json
One partition per download date, so every weekly pull is kept as-is (raw is immutable,
reprocessing means re-reading a partition, not re-downloading). Re-running on the same day
skips objects that already exist with the same size.

Run: python -m src.ingest.upload_s3 [--dt YYYY-MM-DD]
"""

from __future__ import annotations

import argparse
import json
import logging
import os
from datetime import date
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

from src.config import RAW_DIR

log = logging.getLogger("crickql.upload_s3")

PREFIX = "cricsheet/ipl"


def partition_date() -> str:
    manifest = RAW_DIR / "manifest.json"
    if manifest.exists():
        return json.loads(manifest.read_text())["downloaded_at"][:10]
    return date.today().isoformat()


def upload(bucket: str, dt: str | None = None, src_dir: Path = RAW_DIR / "ipl",
           client=None) -> dict:
    s3 = client or boto3.client("s3", region_name=os.getenv("AWS_REGION", "ca-central-1"))
    dt = dt or partition_date()
    prefix = f"{PREFIX}/dt={dt}"
    existing = {}
    for page in s3.get_paginator("list_objects_v2").paginate(Bucket=bucket, Prefix=prefix):
        existing.update({o["Key"]: o["Size"] for o in page.get("Contents", [])})

    uploaded = skipped = 0
    for path in sorted(src_dir.glob("*.json")):
        key = f"{prefix}/{path.name}"
        if existing.get(key) == path.stat().st_size:
            skipped += 1
            continue
        s3.upload_file(str(path), bucket, key, ExtraArgs={"ContentType": "application/json"})
        uploaded += 1
    stats = {"bucket": bucket, "prefix": prefix, "uploaded": uploaded, "skipped": skipped,
             "total": uploaded + skipped}
    log.info("s3 upload: %s", stats)
    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dt", help="partition date, default = manifest download date")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    bucket = os.getenv("S3_BUCKET")
    if not bucket:
        raise SystemExit("S3_BUCKET is not set in .env")
    try:
        upload(bucket, args.dt)
    except ClientError as e:
        raise SystemExit(f"S3 error: {e}") from e


if __name__ == "__main__":
    main()
