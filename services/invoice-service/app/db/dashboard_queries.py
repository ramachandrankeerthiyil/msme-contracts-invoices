"""Invoice dashboard figures (INV-003), built entirely from the INV-002 list filters."""

from dataclasses import dataclass
from datetime import date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.invoice_queries import InvoiceFilters, InvoiceRow, Summary, search, summarize
from app.db.models import InvoiceUpload
from app.domain.clock import local_date
from app.domain.invoice_status import View

TOP_FOLLOW_UP = 5


@dataclass(frozen=True)
class Week:
    start: date
    end: date
    anchor_uploaded_at: datetime

    @property
    def this_week(self) -> InvoiceFilters:
        """Invoices due in the week, any status (AC2, AC3)."""
        return InvoiceFilters(view=View.ALL, due_from=self.start, due_to=self.end)

    @property
    def follow_up(self) -> InvoiceFilters:
        """Outstanding or at risk, due by the end of the week, incl. older overdue (AC4, opt. B)."""
        return InvoiceFilters(view=View.FOLLOW_UP, due_to=self.end)


@dataclass(frozen=True)
class DashboardData:
    week: Week
    this_week: Summary
    follow_up: Summary
    top_follow_up: list[InvoiceRow]


async def current_week(session: AsyncSession, time_zone: str) -> Week | None:
    """[U, U+6], where U is the local date of the latest upload that saved rows (AC1)."""
    anchor = await session.scalar(
        select(func.max(InvoiceUpload.uploaded_at)).where(InvoiceUpload.status == "completed")
    )
    if anchor is None:
        return None
    start = local_date(anchor, time_zone)
    return Week(start=start, end=start + timedelta(days=6), anchor_uploaded_at=anchor)


async def load_dashboard(
    session: AsyncSession, *, today: date, at_risk_days: int, time_zone: str
) -> DashboardData | None:
    week = await current_week(session, time_zone)
    if week is None:
        return None
    rules = {"today": today, "at_risk_days": at_risk_days}
    return DashboardData(
        week=week,
        this_week=await summarize(session, week.this_week, **rules),
        follow_up=await summarize(session, week.follow_up, **rules),
        top_follow_up=await search(session, week.follow_up, **rules, limit=TOP_FOLLOW_UP),
    )
