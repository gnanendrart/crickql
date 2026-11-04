from src.ingest.parse import parse_match
from src.ingest.validate import validate
from tests.conftest import NO_RESULT, NORMAL, SUPER_OVER


def load_all():
    matches, deliveries = [], []
    for p in (NORMAL, SUPER_OVER, NO_RESULT):
        m, ds = parse_match(p)
        matches.append(m)
        deliveries.extend(ds)
    return matches, deliveries


def test_clean_fixtures_pass():
    result = validate(*load_all())
    assert result.passed
    assert len(result.good_matches) == 3


def test_bad_delivery_quarantines_whole_match(isolated_rejects):
    matches, deliveries = load_all()
    deliveries[10]["runs_total"] += 1  # break one ball in the normal match
    result = validate(matches, deliveries)
    assert "E6" in result.failures
    assert result.rejected_match_ids == {1082591}
    assert all(d["match_id"] != 1082591 for d in result.good_deliveries)
    assert len(result.good_matches) == 2
    assert "1082591" in isolated_rejects.read_text()


def test_duplicate_delivery_key_caught():
    matches, deliveries = load_all()
    deliveries.append(dict(deliveries[0]))
    assert "E4" in validate(matches, deliveries).failures


def test_target_mismatch_caught():
    matches, deliveries = load_all()
    matches[0]["target_runs"] = 999
    assert "E8" in validate(matches, deliveries).failures


def test_orphan_delivery_caught():
    matches, deliveries = load_all()
    assert "E5" in validate(matches[1:], deliveries).failures
