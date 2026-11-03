"""Download the Cricsheet IPL archive and unzip it into data/raw/ipl/.

Idempotent in two layers:
1. A conditional GET (ETag / Last-Modified). If Cricsheet answers 304, nothing is downloaded.
2. A SHA-256 of the archive. If the bytes match the last run, nothing is re-extracted.

Run: python -m src.ingest.download [--force]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import requests

from src.config import CRICSHEET_URL, RAW_DIR

log = logging.getLogger("crickql.download")

ARCHIVE_PATH = RAW_DIR / "ipl_json.zip"
EXTRACT_DIR = RAW_DIR / "ipl"
MANIFEST_PATH = RAW_DIR / "manifest.json"
CHUNK = 1 << 16


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(CHUNK), b""):
            h.update(block)
    return h.hexdigest()


def load_manifest() -> dict:
    if MANIFEST_PATH.exists():
        return json.loads(MANIFEST_PATH.read_text())
    return {}


def save_manifest(manifest: dict) -> None:
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + "\n")


def safe_extract(archive: Path, dest: Path) -> int:
    """Extract only .json/.txt members, refusing any path that escapes dest. Returns match count."""
    dest.mkdir(parents=True, exist_ok=True)
    root = dest.resolve()
    with zipfile.ZipFile(archive) as zf:
        for member in zf.infolist():
            if member.is_dir():
                continue
            target = (dest / member.filename).resolve()
            if root not in target.parents:
                raise ValueError(f"Unsafe path in archive: {member.filename}")
            if target.suffix not in {".json", ".txt"}:
                log.warning("Skipping unexpected member %s", member.filename)
                continue
            zf.extract(member, dest)
    return count_matches(dest)


def count_matches(dest: Path) -> int:
    return sum(1 for _ in dest.glob("*.json"))


def download(force: bool = False) -> dict:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    manifest = load_manifest()
    have_files = ARCHIVE_PATH.exists() and EXTRACT_DIR.exists() and count_matches(EXTRACT_DIR) > 0

    headers = {}
    if have_files and not force:
        if manifest.get("etag"):
            headers["If-None-Match"] = manifest["etag"]
        if manifest.get("last_modified"):
            headers["If-Modified-Since"] = manifest["last_modified"]

    resp = requests.get(CRICSHEET_URL, headers=headers, stream=True, timeout=60)
    if resp.status_code == 304:
        log.info("unchanged, skipped (server returned 304). %s matches on disk",
                 manifest.get("match_count"))
        return {**manifest, "status": "skipped"}
    resp.raise_for_status()

    with tempfile.NamedTemporaryFile(dir=RAW_DIR, suffix=".zip.part", delete=False) as tmp:
        tmp_path = Path(tmp.name)
        for block in resp.iter_content(CHUNK):
            tmp.write(block)

    digest = sha256_of(tmp_path)
    if have_files and not force and digest == manifest.get("sha256"):
        tmp_path.unlink()
        log.info("unchanged, skipped (same sha256). %s matches on disk",
                 manifest.get("match_count"))
        return {**manifest, "status": "skipped"}

    if not zipfile.is_zipfile(tmp_path):
        tmp_path.unlink()
        raise ValueError("Downloaded file is not a valid zip archive")

    tmp_path.replace(ARCHIVE_PATH)
    match_count = safe_extract(ARCHIVE_PATH, EXTRACT_DIR)

    manifest = {
        "source_url": CRICSHEET_URL,
        "sha256": digest,
        "etag": resp.headers.get("ETag"),
        "last_modified": resp.headers.get("Last-Modified"),
        "archive_bytes": ARCHIVE_PATH.stat().st_size,
        "match_count": match_count,
        "downloaded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    save_manifest(manifest)
    log.info("downloaded %.1f MB, %d match files in %s",
             manifest["archive_bytes"] / 1e6, match_count, EXTRACT_DIR)
    return {**manifest, "status": "downloaded"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--force", action="store_true", help="re-download even if unchanged")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    download(force=args.force)


if __name__ == "__main__":
    main()
