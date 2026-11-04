from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"
NORMAL = FIXTURES / "1082591.json"  # SRH 207/4 beat RCB 172 all out, IPL 2017 opener
SUPER_OVER = FIXTURES / "1082625.json"  # GL v MI 2017, tie, MI won the super over
NO_RESULT = FIXTURES / "1178424.json"  # RCB v RR 2019, 5-over match, washed out


@pytest.fixture(autouse=True)
def isolated_rejects(tmp_path, monkeypatch):
    """Never let a test write to the real data/rejects.log."""
    log = tmp_path / "rejects.log"
    monkeypatch.setattr("src.ingest.parse.REJECTS_LOG", log)
    monkeypatch.setattr("src.ingest.validate.REJECTS_LOG", log)
    return log


MANIFEST = Path(__file__).parent.parent / "dbt" / "target" / "manifest.json"
needs_manifest = pytest.mark.skipif(
    not MANIFEST.exists(),
    reason="dbt manifest missing: run `dbt parse --project-dir dbt --profiles-dir dbt`",
)
