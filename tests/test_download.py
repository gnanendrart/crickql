import zipfile

import pytest

from src.ingest.download import safe_extract


def test_safe_extract_counts_matches(tmp_path):
    archive = tmp_path / "a.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("1.json", "{}")
        zf.writestr("2.json", "{}")
        zf.writestr("README.txt", "x")
    assert safe_extract(archive, tmp_path / "out") == 2


def test_safe_extract_blocks_path_traversal(tmp_path):
    archive = tmp_path / "evil.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("../../escape.json", "{}")
    with pytest.raises(ValueError, match="Unsafe path"):
        safe_extract(archive, tmp_path / "out")
