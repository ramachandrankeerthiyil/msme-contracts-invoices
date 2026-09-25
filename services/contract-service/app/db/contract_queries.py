"""Contract list queries (CON-002), shared with the dashboard (CON-003) so a dashboard number and
the list behind it always come from the same filter.
"""

import uuid
from dataclasses import dataclass
from datetime import date
from typing import Literal

from sqlalchemy import ColumnElement, exists, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Contract, ContractParty
from app.domain.contract_status import (
    Lifecycle,
    View,
    at_risk_expr,
    expiring_soon_expr,
    high_risk_count_expr,
    high_risk_expr,
    lifecycle_expr,
    lifecycle_rank_expr,
)

SortKey = Literal["end_date", "start_date", "title", "status", "high_risks", "uploaded_at"]
SortOrder = Literal["asc", "desc"]


@dataclass(frozen=True)
class ContractFilters:
    view: View = View.ALL
    q: str | None = None


@dataclass(frozen=True)
class Counts:
    by_view: dict[View, int]
    expiring_soon: int
    high_risk: int


@dataclass(frozen=True)
class ContractRow:
    contract: Contract
    lifecycle: Lifecycle
    high_risks: int
    parties: list[str]


def _escape_like(text: str) -> str:
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _search(q: str | None) -> list[ColumnElement[bool]]:
    if not q or not q.strip():
        return []
    pattern = f"%{_escape_like(q.strip())}%"
    party_match = exists(
        select(ContractParty.id).where(
            ContractParty.contract_id == Contract.id,
            ContractParty.name.ilike(pattern, escape="\\"),
        )
    )
    return [
        or_(
            Contract.title.ilike(pattern, escape="\\"),
            Contract.file_name.ilike(pattern, escape="\\"),
            party_match,
        )
    ]


def view_condition(view: View, today: date, at_risk_days: int) -> ColumnElement[bool]:
    if view == View.ALL:
        return Contract.processing_status == "completed"
    if view == View.AT_RISK:
        return at_risk_expr(today, at_risk_days)
    return lifecycle_expr(today) == Lifecycle(view.value).value


async def count_views(
    session: AsyncSession, filters: ContractFilters, *, today: date, at_risk_days: int
) -> Counts:
    """Per-view counts for everything matching the search (the view itself is ignored)."""
    rows = (
        select(
            lifecycle_expr(today).label("lifecycle"),
            at_risk_expr(today, at_risk_days).label("at_risk"),
            expiring_soon_expr(today, at_risk_days).label("expiring_soon"),
            high_risk_expr(today).label("high_risk"),
            Contract.processing_status.label("processing_status"),
        )
        .where(*_search(filters.q))
        .subquery()
    )
    count = func.count()
    statement = select(
        count.filter(rows.c.processing_status == "completed"),
        count.filter(rows.c.at_risk),
        count.filter(rows.c.expiring_soon),
        count.filter(rows.c.high_risk),
        *[count.filter(rows.c.lifecycle == lifecycle.value) for lifecycle in Lifecycle],
    )
    completed, at_risk, expiring, high, *per_lifecycle = (await session.execute(statement)).one()
    by_view = {View.ALL: completed, View.AT_RISK: at_risk}
    for lifecycle, value in zip(Lifecycle, per_lifecycle, strict=True):
        by_view[View(lifecycle.value)] = value
    return Counts(by_view=by_view, expiring_soon=expiring, high_risk=high)


async def search(
    session: AsyncSession,
    filters: ContractFilters,
    *,
    today: date,
    at_risk_days: int,
    sort: SortKey = "end_date",
    order: SortOrder = "asc",
    offset: int = 0,
    limit: int | None = 25,
    extra_order: list[ColumnElement] | None = None,
) -> list[ContractRow]:
    high_risks = high_risk_count_expr()
    lifecycle = lifecycle_expr(today)
    columns: dict[str, ColumnElement] = {
        "end_date": Contract.end_date,
        "start_date": Contract.start_date,
        "title": func.lower(func.coalesce(Contract.title, Contract.file_name)),
        "status": lifecycle_rank_expr(today),
        "high_risks": high_risks,
        "uploaded_at": Contract.uploaded_at,
    }
    column = columns[sort]
    ordering = [column.asc().nulls_last() if order == "asc" else column.desc().nulls_last()]
    if sort == "status":  # within a status, soonest end first (as the invoice list does)
        ordering.append(Contract.end_date.asc().nulls_last())
    statement = (
        select(Contract, lifecycle.label("lifecycle"), high_risks.label("high_risks"))
        .where(view_condition(filters.view, today, at_risk_days), *_search(filters.q))
        .order_by(*(extra_order or []), *ordering, Contract.uploaded_at.desc(), Contract.id)
        .offset(offset)
        .limit(limit)
    )
    found = (await session.execute(statement)).all()
    parties = await _party_names(session, [contract.id for contract, _, _ in found])
    return [
        ContractRow(contract, Lifecycle(value), high or 0, parties.get(contract.id, []))
        for contract, value, high in found
    ]


async def _party_names(session: AsyncSession, ids: list[uuid.UUID]) -> dict[uuid.UUID, list[str]]:
    if not ids:
        return {}
    result = await session.execute(
        select(ContractParty.contract_id, ContractParty.name)
        .where(ContractParty.contract_id.in_(ids))
        .order_by(ContractParty.contract_id, ContractParty.position)
    )
    names: dict[uuid.UUID, list[str]] = {}
    for contract_id, name in result:
        names.setdefault(contract_id, []).append(name)
    return names
