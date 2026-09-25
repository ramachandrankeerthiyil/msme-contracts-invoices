"""Payment status rules (invoices/module.md "Payment status"; INV-002 AC2).

Status is never stored. It is computed per request against today's date, as SQL for filtering,
counting and sorting, and in Python for anything built outside a query. Both implement the same
rule; a unit test keeps them in step.
"""

from datetime import date, timedelta
from enum import StrEnum

from sqlalchemy import ColumnElement, case

from app.db.models import Invoice


class Status(StrEnum):
    OUTSTANDING = "outstanding"
    AT_RISK = "at_risk"
    OPEN = "open"
    PAID = "paid"


# Outstanding first, then at risk, open, paid (INV-002 AC4).
STATUS_ORDER = (Status.OUTSTANDING, Status.AT_RISK, Status.OPEN, Status.PAID)
RANK = {status: index for index, status in enumerate(STATUS_ORDER)}

STATUS_LABELS = {
    Status.OUTSTANDING: "Outstanding",
    Status.AT_RISK: "At risk",
    Status.OPEN: "Open",
    Status.PAID: "Paid",
}


class View(StrEnum):
    """The quick-filter tabs (INV-002 AC3)."""

    FOLLOW_UP = "follow_up"
    OUTSTANDING = "outstanding"
    AT_RISK = "at_risk"
    OPEN = "open"
    PAID = "paid"
    ALL = "all"


VIEW_STATUSES: dict[View, tuple[Status, ...]] = {
    View.FOLLOW_UP: (Status.OUTSTANDING, Status.AT_RISK),
    View.OUTSTANDING: (Status.OUTSTANDING,),
    View.AT_RISK: (Status.AT_RISK,),
    View.OPEN: (Status.OPEN,),
    View.PAID: (Status.PAID,),
    View.ALL: STATUS_ORDER,
}


def status_of(due_date: date, paid_date: date | None, today: date, at_risk_days: int) -> Status:
    if paid_date is not None:
        return Status.PAID
    if due_date < today:
        return Status.OUTSTANDING
    if due_date <= today + timedelta(days=at_risk_days):
        return Status.AT_RISK
    return Status.OPEN


def status_expr(today: date, at_risk_days: int) -> ColumnElement[str]:
    return case(
        (Invoice.paid_date.is_not(None), Status.PAID.value),
        (Invoice.due_date < today, Status.OUTSTANDING.value),
        (Invoice.due_date <= today + timedelta(days=at_risk_days), Status.AT_RISK.value),
        else_=Status.OPEN.value,
    )


def rank_expr(today: date, at_risk_days: int) -> ColumnElement[int]:
    return case(
        (Invoice.paid_date.is_not(None), RANK[Status.PAID]),
        (Invoice.due_date < today, RANK[Status.OUTSTANDING]),
        (Invoice.due_date <= today + timedelta(days=at_risk_days), RANK[Status.AT_RISK]),
        else_=RANK[Status.OPEN],
    )


def days_until_due(due_date: date, paid_date: date | None, today: date) -> int | None:
    """Negative when overdue; None once paid."""
    return None if paid_date is not None else (due_date - today).days


def due_hint(due_date: date, paid_date: date | None, today: date) -> str:
    """Same wording as the UI: 'due in 3 days', 'due today', '12 days overdue', 'paid on …'."""
    if paid_date is not None:
        return f"paid on {paid_date.day} {paid_date:%b %Y}"
    days = (due_date - today).days
    if days == 0:
        return "due today"
    if days > 0:
        return f"due in {days} day{'s' if days != 1 else ''}"
    return f"{-days} day{'s' if days != -1 else ''} overdue"
