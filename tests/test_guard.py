import pytest

from src.ingest.guard import RowCountDropError, check_row_counts


def test_first_load_passes():
    check_row_counts(10, 100, None)


def test_growth_and_small_drop_pass():
    check_row_counts(1300, 300_000, (1243, 295_732))
    check_row_counts(1200, 285_000, (1243, 295_732))  # 3.5% drop, within 5%


def test_big_drop_fails_loudly():
    with pytest.raises(RowCountDropError, match="deliveries dropped"):
        check_row_counts(1243, 200_000, (1243, 295_732))
