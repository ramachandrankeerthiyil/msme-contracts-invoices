"""Invoice list and export (INV-002) and dashboard (INV-003) endpoints."""

import asyncio
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import (
    Dashboard,
    DashboardLinks,
    FollowUpOut,
    InvoiceItem,
    InvoicePage,
    ListLink,
    StatusValue,
    TopFollowUpItem,
    ViewCounts,
    WeekOut,
)
from app.api.uploads import XLSX_MEDIA_TYPE
from app.core.errors import AppError
from app.core.logging import get_logger
from app.db import get_session
from app.db.dashboard_queries import load_dashboard
from app.db.invoice_queries import InvoiceFilters, InvoiceRow, SortKey, SortOrder, search, summarize
from app.domain.clock import get_today
from app.domain.export import MAX_EXPORT_ROWS, build_export
from app.domain.invoice_status import STATUS_ORDER, Status, View, days_until_due
from app.domain.reminders import is_remindable

router = APIRouter(tags=["Invoices"])
log = get_logger("invoices")


def invoice_filters(
    view: View = View.FOLLOW_UP,
    q: Annotated[str | None, Query(max_length=100)] = None,
    updated: bool = False,
    due_from: date | None = None,
    due_to: date | None = None,
) -> InvoiceFilters:
    if due_from and due_to and due_from > due_to:
        raise AppError(
            "VALIDATION_ERROR", "The start date must be on or before the end date.", status=422
        )
    return InvoiceFilters(view=view, q=q, updated=updated, due_from=due_from, due_to=due_to)


Filters = Annotated[InvoiceFilters, Depends(invoice_filters)]
Today = Annotated[date, Depends(get_today)]
Session = Annotated[AsyncSession, Depends(get_session)]


def _to_item(row: InvoiceRow, today: date) -> InvoiceItem:
    invoice = row.invoice
    return InvoiceItem(
        id=invoice.id,
        invoice_number=invoice.invoice_number,
        customer_name=invoice.customer_name,
        date_raised=invoice.date_raised,
        due_date=invoice.due_date,
        amount=invoice.amount,
        paid_date=invoice.paid_date,
        status=row.status,
        days_until_due=days_until_due(invoice.due_date, invoice.paid_date, today),
        record_status=invoice.record_status,  # type: ignore[arg-type]
        record_updated_at=invoice.record_updated_at,
        customer_email=invoice.customer_email,
        can_remind=is_remindable(row.status),
        last_reminder_at=row.last_reminder_at,
    )


def _link(filters: InvoiceFilters) -> ListLink:
    return ListLink(view=filters.view, due_from=filters.due_from, due_to=filters.due_to)


@router.get("", response_model=InvoicePage)
async def list_invoices(
    request: Request,
    filters: Filters,
    today: Today,
    session: Session,
    sort: SortKey = "status",
    order: SortOrder = "asc",
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
) -> InvoicePage:
    rules = {"today": today, "at_risk_days": request.app.state.settings.invoice_at_risk_days}
    summary = await summarize(session, filters, **rules)
    rows = await search(
        session,
        filters,
        **rules,
        sort=sort,
        order=order,
        offset=(page - 1) * page_size,
        limit=page_size,
    )
    return InvoicePage(
        today=today,
        items=[_to_item(row, today) for row in rows],
        total=summary.total,
        page=page,
        page_size=page_size,
        total_amount=summary.total_amount,
        counts=ViewCounts(**{view.value: summary.count(view) for view in View}),
    )


@router.get("/export", response_class=Response)
async def export_invoices(
    request: Request,
    filters: Filters,
    today: Today,
    session: Session,
    sort: SortKey = "status",
    order: SortOrder = "asc",
) -> Response:
    settings = request.app.state.settings
    rows = await search(
        session,
        filters,
        today=today,
        at_risk_days=settings.invoice_at_risk_days,
        sort=sort,
        order=order,
        limit=MAX_EXPORT_ROWS + 1,
    )
    if len(rows) > MAX_EXPORT_ROWS:
        raise AppError(
            "TOO_MANY_ROWS",
            f"There are more than {MAX_EXPORT_ROWS:,} invoices in this view. "
            "Narrow the filters and try again.",
            status=422,
        )
    content = await asyncio.to_thread(
        build_export, rows, today=today, time_zone=settings.app_timezone
    )
    log.info("invoice_export.completed", message="Invoice export created", rows=len(rows))
    file_name = f"invoices-{today.isoformat()}.xlsx"
    return Response(
        content=content,
        media_type=XLSX_MEDIA_TYPE,
        headers={"Content-Disposition": f'attachment; filename="{file_name}"'},
    )


@router.get("/dashboard", response_model=Dashboard, response_model_exclude_none=True)
async def dashboard(request: Request, today: Today, session: Session) -> Dashboard:
    settings = request.app.state.settings
    data = await load_dashboard(
        session,
        today=today,
        at_risk_days=settings.invoice_at_risk_days,
        time_zone=settings.app_timezone,
    )
    if data is None:
        return Dashboard(today=today, has_data=False)

    week, this_week, follow_up = data.week, data.this_week, data.follow_up
    return Dashboard(
        today=today,
        has_data=True,
        week=WeekOut(start=week.start, end=week.end, anchor_uploaded_at=week.anchor_uploaded_at),
        value_this_week=this_week.total_amount,
        invoices_this_week=this_week.total,
        follow_up=FollowUpOut(
            total=follow_up.total,
            outstanding=follow_up.by_status[Status.OUTSTANDING].count,
            at_risk=follow_up.by_status[Status.AT_RISK].count,
        ),
        value_by_status=[
            StatusValue(
                status=status,
                amount=this_week.by_status[status].amount,
                count=this_week.by_status[status].count,
            )
            for status in STATUS_ORDER
        ],
        top_follow_up=[
            TopFollowUpItem(
                id=row.invoice.id,
                invoice_number=row.invoice.invoice_number,
                customer_name=row.invoice.customer_name,
                amount=row.invoice.amount,
                due_date=row.invoice.due_date,
                days_until_due=days_until_due(row.invoice.due_date, row.invoice.paid_date, today),
                status=row.status,
            )
            for row in data.top_follow_up
        ],
        links=DashboardLinks(this_week=_link(week.this_week), follow_up=_link(week.follow_up)),
    )
