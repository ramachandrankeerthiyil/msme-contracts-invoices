"""Invoice list queries (INV-002), shared with the dashboard (INV-003).

A dashboard number and the list it links to are produced by the same `InvoiceFilters`, so they
can never disagree (INV-003 AC6).
"""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from sqlalchemy import ColumnElement, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Invoice, InvoiceReminder
from app.domain.invoice_status import (
    STATUS_ORDER,
    VIEW_STATUSES,
    Status,
    View,
    rank_expr,
    status_expr,
)

SortKey = Literal[
    "status", "invoice_number", "customer_name", "date_raised", "due_date", "amount", "paid_date"
]
SortOrder = Literal["asc", "desc"]

_SORT_COLUMNS: dict[str, ColumnElement] = {
    "invoice_number": Invoice.invoice_number_key,
    "customer_name": func.lower(Invoice.customer_name),
    "date_raised": Invoice.date_raised,
    "due_date": Invoice.due_date,
    "amount": Invoice.amount,
    "paid_date": Invoice.paid_date,
}


@dataclass(frozen=True)
class InvoiceFilters:
    view: View = View.FOLLOW_UP
    q: str | None = None
    updated: bool = False
    due_from: date | None = None
    due_to: date | None = None


@dataclass(frozen=True)
class StatusTotals:
    count: int
    amount: Decimal


@dataclass(frozen=True)
class Summary:
    """Per-status totals for everything matching the filters *except* the view."""

    by_status: dict[Status, StatusTotals]
    view: View

    def count(self, view: View) -> int:
        return sum(self.by_status[s].count for s in VIEW_STATUSES[view])

    @property
    def total(self) -> int:
        return self.count(self.view)

    @property
    def total_amount(self) -> Decimal:
        return sum(
            (self.by_status[s].amount for s in VIEW_STATUSES[self.view]), start=Decimal("0.00")
        )


@dataclass(frozen=True)
class InvoiceRow:
    invoice: Invoice
    status: Status
    last_reminder_at: datetime | None = None  # INV-004


_LAST_REMINDER_AT = (
    select(func.max(InvoiceReminder.sent_at))
    .where(InvoiceReminder.invoice_id == Invoice.id)
    .correlate(Invoice)
    .scalar_subquery()
)


def _escape_like(text: str) -> str:
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _base_conditions(filters: InvoiceFilters) -> list[ColumnElement[bool]]:
    conditions: list[ColumnElement[bool]] = []
    if filters.q and filters.q.strip():
        pattern = f"%{_escape_like(filters.q.strip())}%"
        conditions.append(
            or_(
                Invoice.invoice_number.ilike(pattern, escape="\\"),
                Invoice.customer_name.ilike(pattern, escape="\\"),
            )
        )
    if filters.updated:
        conditions.append(Invoice.record_status == "updated")
    if filters.due_from:
        conditions.append(Invoice.due_date >= filters.due_from)
    if filters.due_to:
        conditions.append(Invoice.due_date <= filters.due_to)
    return conditions


async def summarize(
    session: AsyncSession, filters: InvoiceFilters, *, today: date, at_risk_days: int
) -> Summary:
    # Status is computed in a subquery: grouping directly by a CASE with bound parameters fails
    # in Postgres (the GROUP BY copy gets different placeholders from the SELECT copy).
    rows = (
        select(status_expr(today, at_risk_days).label("status"), Invoice.amount)
        .where(*_base_conditions(filters))
        .subquery()
    )
    statement = select(
        rows.c.status, func.count(), func.coalesce(func.sum(rows.c.amount), 0)
    ).group_by(rows.c.status)
    found = {
        Status(name): StatusTotals(count, Decimal(amount))
        for name, count, amount in await session.execute(statement)
    }
    by_status = {s: found.get(s, StatusTotals(0, Decimal("0.00"))) for s in STATUS_ORDER}
    return Summary(by_status=by_status, view=filters.view)


async def search(
    session: AsyncSession,
    filters: InvoiceFilters,
    *,
    today: date,
    at_risk_days: int,
    sort: SortKey = "status",
    order: SortOrder = "asc",
    offset: int = 0,
    limit: int | None = 25,
) -> list[InvoiceRow]:
    status = status_expr(today, at_risk_days)
    statement = select(
        Invoice, status.label("status"), _LAST_REMINDER_AT.label("last_reminder_at")
    ).where(*_base_conditions(filters), status.in_([s.value for s in VIEW_STATUSES[filters.view]]))

    if sort == "status":
        rank = rank_expr(today, at_risk_days)
        # Within a status, soonest due first: most overdue at the top for outstanding (AC4).
        ordering = [rank.asc() if order == "asc" else rank.desc(), Invoice.due_date.asc()]
    else:
        column = _SORT_COLUMNS[sort]
        ordering = [column.asc().nulls_last() if order == "asc" else column.desc().nulls_last()]
    statement = statement.order_by(*ordering, Invoice.invoice_number_key.asc())
    statement = statement.offset(offset).limit(limit)

    return [
        InvoiceRow(invoice, Status(status_value), reminded_at)
        for invoice, status_value, reminded_at in await session.execute(statement)
    ]
