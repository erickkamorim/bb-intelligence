from datetime import date

import pytest

from etl.periods import PeriodType, classify_window, derive_q4, parse_period_code, period_code


def test_period_code_roundtrip():
    assert period_code(date(2026, 9, 30)) == "2026Q3"
    assert parse_period_code("2026Q3") == (date(2026, 7, 1), date(2026, 9, 30))
    assert parse_period_code("2025q4") == (date(2025, 10, 1), date(2025, 12, 31))


@pytest.mark.parametrize("bad", ["2026", "2026Q5", "26Q1", "2026-Q1"])
def test_parse_period_code_rejects(bad):
    with pytest.raises(ValueError):
        parse_period_code(bad)


@pytest.mark.parametrize("start,end,expected", [
    (None, date(2026, 6, 30), PeriodType.INSTANT),
    (date(2026, 4, 1), date(2026, 6, 30), PeriodType.QUARTER),
    (date(2026, 1, 1), date(2026, 6, 30), PeriodType.YTD),
    (date(2026, 1, 1), date(2026, 3, 31), PeriodType.QUARTER),   # 1T: YTD == trimestre
    (date(2025, 1, 1), date(2025, 12, 31), PeriodType.FY),
])
def test_classify_window(start, end, expected):
    assert classify_window(start, end) is expected


def test_classify_window_rejects_odd_window():
    with pytest.raises(ValueError):
        classify_window(date(2026, 2, 1), date(2026, 6, 30))


def test_derive_q4_is_flagged():
    d = derive_q4(400.0, 290.0)
    assert d.value == 110.0
    assert d.method.startswith("derived:")
