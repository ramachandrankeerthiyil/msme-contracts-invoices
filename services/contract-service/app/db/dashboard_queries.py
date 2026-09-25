"""Contract dashboard figures (CON-003), built from the CON-002 list filters."""

from dataclasses import dataclass
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.contract_queries import ContractFilters, ContractRow, Counts, count_views, search
from app.db.models import Contract
from app.domain.contract_status import View, at_risk_expr, at_risk_reasons

NEEDS_ATTENTION = 5


@dataclass(frozen=True)
class DashboardData:
    counts: Counts
    needs_attention: list[ContractRow]


async def load_dashboard(
    session: AsyncSession, *, today: date, at_risk_days: int
) -> DashboardData | None:
    """None when there are no contracts at all, read or not (AC7)."""
    if not await session.scalar(select(func.count()).select_from(Contract)):
        return None
    rules = {"today": today, "at_risk_days": at_risk_days}
    counts = await count_views(session, ContractFilters(), **rules)
    # At risk first, then the soonest end dates; expired and unread contracts are excluded.
    current = [View.IN_FORCE, View.NOT_STARTED, View.NO_END_DATE]
    rows: list[ContractRow] = []
    for view in current:
        rows += await search(
            session,
            ContractFilters(view=view),
            **rules,
            limit=NEEDS_ATTENTION,
            extra_order=[at_risk_expr(today, at_risk_days).desc()],
        )
    rows.sort(key=lambda row: (not _is_at_risk(row, today, at_risk_days), _end_key(row)))
    return DashboardData(counts=counts, needs_attention=rows[:NEEDS_ATTENTION])


def _end_key(row: ContractRow) -> tuple[int, date]:
    end = row.contract.end_date
    return (1, date.max) if end is None else (0, end)


def _is_at_risk(row: ContractRow, today: date, at_risk_days: int) -> bool:
    return bool(
        at_risk_reasons(row.lifecycle, row.contract.end_date, row.high_risks, today, at_risk_days)
    )
