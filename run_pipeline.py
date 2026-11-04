"""Local pipeline without Airflow: download -> parse -> validate -> load Postgres -> dbt build.

Run: python run_pipeline.py [--skip-download] [--skip-dbt]
"""

import argparse
import logging
import subprocess
import sys

from src.config import ROOT
from src.ingest.download import download
from src.ingest.load_pg import run as load_pg


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--skip-download", action="store_true")
    parser.add_argument("--skip-dbt", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    if not args.skip_download:
        download()
    load_pg()
    if not args.skip_dbt:
        cmd = ["dbt", "build", "--target", "pg", "--project-dir", "dbt", "--profiles-dir", "dbt"]
        return subprocess.call(cmd, cwd=ROOT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
