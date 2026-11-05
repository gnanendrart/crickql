import shutil

import boto3
import pytest

moto = pytest.importorskip("moto")

from src.ingest.upload_s3 import upload  # noqa: E402
from tests.conftest import NO_RESULT, NORMAL  # noqa: E402


@pytest.fixture(autouse=True)
def fake_aws(monkeypatch):
    """Isolate from the real ~/.aws and .env: moto needs credentials, not a real profile."""
    monkeypatch.delenv("AWS_PROFILE", raising=False)
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "ca-central-1")


@moto.mock_aws
def test_upload_is_partitioned_and_idempotent(tmp_path):
    for f in (NORMAL, NO_RESULT):
        shutil.copy(f, tmp_path)
    s3 = boto3.client("s3", region_name="ca-central-1")
    s3.create_bucket(Bucket="crickql-test",
                     CreateBucketConfiguration={"LocationConstraint": "ca-central-1"})

    first = upload("crickql-test", "2026-11-04", tmp_path, client=s3)
    second = upload("crickql-test", "2026-11-04", tmp_path, client=s3)

    keys = [o["Key"] for o in s3.list_objects_v2(Bucket="crickql-test")["Contents"]]
    assert sorted(keys) == [
        "cricsheet/ipl/dt=2026-11-04/1082591.json",
        "cricsheet/ipl/dt=2026-11-04/1178424.json",
    ]
    assert first["uploaded"] == 2 and second == {**second, "uploaded": 0, "skipped": 2}


def test_snowflake_load_sql_splits_into_three_statements():
    from src.config import ROOT
    from src.ingest.load_snowflake import split_sql

    stmts = split_sql((ROOT / "sql/snowflake/load_raw.sql").read_text(), "CRICSHEET_INTERNAL")
    assert [s.split()[0] for s in stmts] == ["DELETE", "COPY", "SELECT"]
    assert all("{stage}" not in s and "@CRICKQL.RAW.CRICSHEET_INTERNAL" in s for s in stmts[:2])
