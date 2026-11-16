from evals.run_sql_eval import results_match


def test_extra_generated_columns_allowed():
    assert results_match([["V Kohli"]], [["V Kohli", 973]])


def test_numbers_and_case_normalised():
    assert results_match([["v kohli", 973]], [["V Kohli", 973.004]])


def test_order_ignored_unless_ordered():
    gold = [["a", 1], ["b", 2]]
    gen = [["b", 2], ["a", 1]]
    assert results_match(gold, gen)
    assert not results_match(gold, gen, ordered=True)


def test_wrong_value_or_row_count_fails():
    assert not results_match([["V Kohli"]], [["RG Sharma"]])
    assert not results_match([["a"]], [["a"], ["b"]])


def test_rows_must_line_up_not_just_columns():
    gold = [["a", 1], ["b", 2]]
    gen = [["a", 2], ["b", 1]]  # same column values, wrong pairing
    assert not results_match(gold, gen)


def test_ordered_allows_extra_rows_after_the_gold_rows():
    gold = [["CH Gayle", 357]]
    gen = [["CH Gayle", 357], ["RG Sharma", 323], ["V Kohli", 316]]
    assert results_match(gold, gen, ordered=True)


def test_ordered_extra_rows_still_need_the_right_leader():
    gold = [["CH Gayle", 357]]
    gen = [["RG Sharma", 323], ["CH Gayle", 357]]
    assert not results_match(gold, gen, ordered=True)


def test_ordered_fewer_rows_than_gold_fails():
    gold = [[2020, "KL Rahul"], [2021, "RD Gaikwad"]]
    assert not results_match(gold, [[2020, "KL Rahul"]], ordered=True)


def test_unordered_still_needs_exact_row_count():
    assert not results_match([[287]], [[287], [286]])
