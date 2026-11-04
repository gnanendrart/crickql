import json

from src.ingest.parse import parse_dir, parse_match
from tests.conftest import NO_RESULT, NORMAL, SUPER_OVER


def innings_totals(deliveries):
    out = {}
    for d in deliveries:
        runs, wkts, legal = out.get(d["innings"], (0, 0, 0))
        out[d["innings"]] = (
            runs + d["runs_total"], wkts + d["wicket_count"], legal + d["is_legal"]
        )
    return out


def test_normal_match_matches_scorecard():
    match, deliveries = parse_match(NORMAL)
    assert match["result_type"] == "normal"
    assert match["winner"] == "Sunrisers Hyderabad" and match["win_by_runs"] == 35
    totals = innings_totals(deliveries)
    assert totals[1] == (207, 4, 120)  # 207/4 in 20 overs
    assert totals[2] == (172, 10, 118)  # 172 all out in 19.4 overs
    assert match["target_runs"] == totals[1][0] + 1


def test_super_over_flagged_not_dropped():
    match, deliveries = parse_match(SUPER_OVER)
    assert match["result_type"] == "tie"
    assert match["has_super_over"] and match["decided_by_super_over"]
    assert match["winner"] == "Mumbai Indians"
    so = [d for d in deliveries if d["is_super_over"]]
    assert {d["innings"] for d in so} == {3, 4}
    assert not any(d["is_super_over"] for d in deliveries if d["innings"] <= 2)


def test_no_result_kept_with_flag():
    match, deliveries = parse_match(NO_RESULT)
    assert match["result_type"] == "no result"
    assert match["winner"] is None
    assert len(deliveries) > 0


def test_delivery_key_unique_even_though_actual_delivery_repeats():
    for path in (NORMAL, SUPER_OVER, NO_RESULT):
        _, deliveries = parse_match(path)
        keys = [(d["innings"], d["over_no"], d["ball_seq"]) for d in deliveries]
        assert len(keys) == len(set(keys))


def test_wides_do_not_advance_legal_ball():
    _, deliveries = parse_match(NORMAL)
    wides = [d for d in deliveries if d["extras_wides"]]
    assert wides and all(d["legal_ball"] is None and not d["is_legal"] for d in wides)


def test_season_label_normalised_to_play_year(tmp_path):
    doc = json.loads(NORMAL.read_text())
    doc["info"]["season"] = "2020/21"
    doc["info"]["dates"] = ["2020-09-19"]
    path = tmp_path / "999.json"
    path.write_text(json.dumps(doc))
    match, _ = parse_match(path)
    assert match["season_raw"] == "2020/21" and match["season_year"] == 2020


def test_malformed_file_is_rejected_and_logged(tmp_path, isolated_rejects):
    (tmp_path / "1.json").write_text("{broken")
    (tmp_path / "2.json").write_text(NORMAL.read_text())
    matches, _, rejects = parse_dir(tmp_path)
    assert rejects == 1 and len(matches) == 1
    assert "1.json" in isolated_rejects.read_text()
