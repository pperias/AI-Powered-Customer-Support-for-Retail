from datetime import date

from support_agent.tools.warranty import _add_months, is_in_warranty


def test_recent_order_is_in_warranty():
    assert is_in_warranty("2026-06-15", today=date(2026, 11, 17))


def test_old_order_is_out_of_warranty():
    assert not is_in_warranty("2025-09-01", today=date(2026, 11, 17))


def test_boundary_is_inclusive():
    assert is_in_warranty("2025-11-17", today=date(2026, 11, 17))
    assert not is_in_warranty("2025-11-17", today=date(2026, 11, 18))


def test_month_end_does_not_overflow():
    assert _add_months(date(2024, 2, 29), 12) == date(2025, 2, 28)
