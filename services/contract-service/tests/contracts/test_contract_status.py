from datetime import date, timedelta

import pytest

from app.domain.contract_status import Lifecycle, at_risk_reasons, lifecycle_of

TODAY = date(2026, 9, 25)


def d(offset: int) -> date:
    return TODAY + timedelta(days=offset)


@pytest.mark.parametrize(
    ("status", "start", "end", "expected"),
    [
        ("uploaded", None, None, Lifecycle.PROCESSING),
        ("analysing", d(-10), d(10), Lifecycle.PROCESSING),
        ("failed", d(-10), d(10), Lifecycle.FAILED),
        ("completed", d(1), d(100), Lifecycle.NOT_STARTED),
        ("completed", d(1), None, Lifecycle.NOT_STARTED),  # start checked before end
        ("completed", d(-10), None, Lifecycle.NO_END_DATE),
        ("completed", None, None, Lifecycle.NO_END_DATE),
        ("completed", d(-400), d(-1), Lifecycle.EXPIRED),
        ("completed", d(-10), d(0), Lifecycle.IN_FORCE),  # ends today: still in force
        ("completed", None, d(30), Lifecycle.IN_FORCE),  # missing start counts as started
        ("completed", d(0), d(30), Lifecycle.IN_FORCE),
    ],
)
def test_CON_002_AC4_lifecycle_rules(status, start, end, expected):
    assert lifecycle_of(status, start, end, TODAY) == expected


@pytest.mark.parametrize(
    ("lifecycle", "end", "high", "reasons"),
    [
        (Lifecycle.IN_FORCE, d(0), 0, ["Expires today"]),
        (Lifecycle.IN_FORCE, d(1), 0, ["Expires in 1 day"]),
        (Lifecycle.IN_FORCE, d(3), 0, ["Expires in 3 days"]),  # last at-risk day
        (Lifecycle.IN_FORCE, d(4), 0, []),
        (Lifecycle.IN_FORCE, d(100), 1, ["1 high risk"]),
        (Lifecycle.IN_FORCE, d(2), 3, ["Expires in 2 days", "3 high risks"]),  # OR: both shown
        (Lifecycle.NO_END_DATE, None, 2, ["2 high risks"]),
        (Lifecycle.NOT_STARTED, d(200), 1, ["1 high risk"]),
        (Lifecycle.EXPIRED, d(-1), 5, []),  # expired is never "at risk"
        (Lifecycle.FAILED, None, 0, []),
    ],
)
def test_CON_002_AC4_at_risk_is_expiring_soon_or_high_risk(lifecycle, end, high, reasons):
    assert at_risk_reasons(lifecycle, end, high, TODAY, 3) == reasons
