from datetime import date, timedelta

import pytest

from app.domain.invoice_status import Status, days_until_due, due_hint, status_of

TODAY = date(2026, 9, 25)


@pytest.mark.parametrize(
    ("due_offset", "paid", "expected"),
    [
        (-30, None, Status.OUTSTANDING),
        (-1, None, Status.OUTSTANDING),
        (0, None, Status.AT_RISK),  # due today
        (5, None, Status.AT_RISK),  # last at-risk day
        (6, None, Status.OPEN),
        (40, None, Status.OPEN),
        (-30, date(2026, 9, 1), Status.PAID),  # paid late is still paid
        (3, date(2026, 9, 20), Status.PAID),
    ],
)
def test_INV_002_AC2_status_rule_boundaries(due_offset, paid, expected):
    assert status_of(TODAY + timedelta(days=due_offset), paid, TODAY, 5) == expected


@pytest.mark.parametrize(
    ("due_offset", "paid", "hint"),
    [
        (0, None, "due today"),
        (1, None, "due in 1 day"),
        (3, None, "due in 3 days"),
        (-1, None, "1 day overdue"),
        (-41, None, "41 days overdue"),
        (-5, date(2026, 9, 20), "paid on 20 Sep 2026"),
    ],
)
def test_INV_002_AC1_due_hints(due_offset, paid, hint):
    assert due_hint(TODAY + timedelta(days=due_offset), paid, TODAY) == hint


def test_INV_002_days_until_due_is_none_once_paid():
    assert days_until_due(TODAY - timedelta(days=3), None, TODAY) == -3
    assert days_until_due(TODAY, date(2026, 9, 1), TODAY) is None
