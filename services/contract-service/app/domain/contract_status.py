"""Contract lifecycle and at-risk rules (contracts/module.md; CON-002 design "Status rules").

Never stored: computed per request against today, as SQL (filtering, counting, sorting) and in
Python (anything built outside a query). Unit tests keep the two in step.
"""

from datetime import date, timedelta
from enum import StrEnum

from sqlalchemy import ColumnElement, and_, case, func, or_, select

from app.db.models import IN_PROGRESS, Contract, ContractRisk


class Lifecycle(StrEnum):
    IN_FORCE = "in_force"
    NOT_STARTED = "not_started"
    NO_END_DATE = "no_end_date"
    EXPIRED = "expired"
    PROCESSING = "processing"
    FAILED = "failed"


# Read contracts (dashboard partition), then unread ones.
READ_LIFECYCLES = (
    Lifecycle.IN_FORCE,
    Lifecycle.NOT_STARTED,
    Lifecycle.NO_END_DATE,
    Lifecycle.EXPIRED,
)
RANK = {
    lifecycle: index
    for index, lifecycle in enumerate([*READ_LIFECYCLES, Lifecycle.PROCESSING, Lifecycle.FAILED])
}


class View(StrEnum):
    """The contract list tabs (CON-002 AC2). ALL means every *read* contract."""

    ALL = "all"
    IN_FORCE = "in_force"
    AT_RISK = "at_risk"
    NOT_STARTED = "not_started"
    EXPIRED = "expired"
    NO_END_DATE = "no_end_date"
    PROCESSING = "processing"
    FAILED = "failed"


# --- Python -------------------------------------------------------------------------------


def lifecycle_of(
    processing_status: str, start: date | None, end: date | None, today: date
) -> Lifecycle:
    if processing_status in IN_PROGRESS:
        return Lifecycle.PROCESSING
    if processing_status == "failed":
        return Lifecycle.FAILED
    if start is not None and start > today:
        return Lifecycle.NOT_STARTED
    if end is None:
        return Lifecycle.NO_END_DATE
    if end < today:
        return Lifecycle.EXPIRED
    return Lifecycle.IN_FORCE


def expires_soon(end: date | None, today: date, at_risk_days: int) -> bool:
    return end is not None and today <= end <= today + timedelta(days=at_risk_days)


def at_risk_reasons(
    lifecycle: Lifecycle, end: date | None, high_risks: int, today: date, at_risk_days: int
) -> list[str]:
    """Why a read, non-expired contract is at risk; empty when it isn't (module.md)."""
    if lifecycle not in (Lifecycle.IN_FORCE, Lifecycle.NOT_STARTED, Lifecycle.NO_END_DATE):
        return []
    reasons = []
    if expires_soon(end, today, at_risk_days):
        assert end is not None
        days = (end - today).days
        reasons.append(
            "Expires today" if days == 0 else f"Expires in {days} day{'s' if days != 1 else ''}"
        )
    if high_risks:
        reasons.append(f"{high_risks} high risk{'s' if high_risks != 1 else ''}")
    return reasons


# --- SQL ----------------------------------------------------------------------------------


def lifecycle_expr(today: date) -> ColumnElement[str]:
    return case(
        (Contract.processing_status.in_(IN_PROGRESS), Lifecycle.PROCESSING.value),
        (Contract.processing_status == "failed", Lifecycle.FAILED.value),
        (
            and_(Contract.start_date.is_not(None), Contract.start_date > today),
            Lifecycle.NOT_STARTED.value,
        ),
        (Contract.end_date.is_(None), Lifecycle.NO_END_DATE.value),
        (Contract.end_date < today, Lifecycle.EXPIRED.value),
        else_=Lifecycle.IN_FORCE.value,
    )


def lifecycle_rank_expr(today: date) -> ColumnElement[int]:
    return case(
        *[(lifecycle_expr(today) == lifecycle.value, rank) for lifecycle, rank in RANK.items()],
        else_=len(RANK),
    )


def high_risk_count_expr() -> ColumnElement[int]:
    return (
        select(func.count(ContractRisk.id))
        .where(ContractRisk.contract_id == Contract.id, ContractRisk.severity == "high")
        .correlate(Contract)
        .scalar_subquery()
    )


def _read_and_current(today: date) -> ColumnElement[bool]:
    return and_(
        Contract.processing_status == "completed",
        or_(Contract.end_date.is_(None), Contract.end_date >= today),
    )


def expiring_soon_expr(today: date, at_risk_days: int) -> ColumnElement[bool]:
    return and_(
        Contract.processing_status == "completed",
        Contract.end_date.is_not(None),
        Contract.end_date >= today,
        Contract.end_date <= today + timedelta(days=at_risk_days),
    )


def high_risk_expr(today: date) -> ColumnElement[bool]:
    return and_(_read_and_current(today), high_risk_count_expr() > 0)


def at_risk_expr(today: date, at_risk_days: int) -> ColumnElement[bool]:
    return or_(expiring_soon_expr(today, at_risk_days), high_risk_expr(today))
