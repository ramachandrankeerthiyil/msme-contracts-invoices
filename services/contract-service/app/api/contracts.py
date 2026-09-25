"""Contract list, dashboard, detail and original file (CON-002, CON-003)."""

import uuid
from datetime import date
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import ContractId, contract_not_found
from app.api.schemas import (
    AtRiskBreakdown,
    ContractDetail,
    ContractListItem,
    ContractPage,
    Dashboard,
    DashboardCounts,
    KeyDateOut,
    LifecycleCount,
    ListLink,
    PartyOut,
    RiskOut,
    TermOut,
    Unread,
    ViewCounts,
)
from app.db import get_session
from app.db.contract_queries import ContractFilters, ContractRow, SortKey, SortOrder, count_views
from app.db.contract_queries import search as search_contracts
from app.db.dashboard_queries import load_dashboard
from app.db.models import TERM_CATEGORIES, Contract
from app.domain.clock import get_today
from app.domain.contract_status import READ_LIFECYCLES, View, at_risk_reasons, lifecycle_of

router = APIRouter(tags=["Contracts"])

Today = Annotated[date, Depends(get_today)]
Session = Annotated[AsyncSession, Depends(get_session)]
SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}
CATEGORY_ORDER = {category: index for index, category in enumerate(TERM_CATEGORIES)}
MEDIA_TYPES = {
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


def contract_filters(
    view: View = View.ALL, q: Annotated[str | None, Query(max_length=100)] = None
) -> ContractFilters:
    return ContractFilters(view=view, q=q)


def _at_risk_days(request: Request) -> int:
    return request.app.state.settings.contract_at_risk_days


def _days(end: date | None, today: date) -> int | None:
    return None if end is None else (end - today).days


def _item(row: ContractRow, today: date, at_risk_days: int) -> ContractListItem:
    contract = row.contract
    reasons = at_risk_reasons(row.lifecycle, contract.end_date, row.high_risks, today, at_risk_days)
    return ContractListItem(
        id=contract.id,
        title=contract.title or contract.file_name,
        file_name=contract.file_name,
        parties=row.parties,
        start_date=contract.start_date,
        end_date=contract.end_date,
        days_until_end=_days(contract.end_date, today),
        lifecycle=row.lifecycle,
        at_risk=bool(reasons),
        at_risk_reasons=reasons,
        high_risk_count=row.high_risks,
        uploaded_at=contract.uploaded_at,
        processing_status=contract.processing_status,
    )


@router.get("", response_model=ContractPage)
async def list_contracts(
    request: Request,
    filters: Annotated[ContractFilters, Depends(contract_filters)],
    today: Today,
    session: Session,
    sort: SortKey = "end_date",
    order: SortOrder = "asc",
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
) -> ContractPage:
    days = _at_risk_days(request)
    counts = await count_views(session, filters, today=today, at_risk_days=days)
    rows = await search_contracts(
        session,
        filters,
        today=today,
        at_risk_days=days,
        sort=sort,
        order=order,
        offset=(page - 1) * page_size,
        limit=page_size,
    )
    return ContractPage(
        today=today,
        items=[_item(row, today, days) for row in rows],
        total=counts.by_view[filters.view],
        page=page,
        page_size=page_size,
        counts=ViewCounts(**{view.value: counts.by_view[view] for view in View}),
    )


@router.get("/dashboard", response_model=Dashboard, response_model_exclude_none=True)
async def dashboard(request: Request, today: Today, session: Session) -> Dashboard:
    days = _at_risk_days(request)
    data = await load_dashboard(session, today=today, at_risk_days=days)
    if data is None:
        return Dashboard(today=today, has_data=False)
    by_view = data.counts.by_view
    return Dashboard(
        today=today,
        has_data=True,
        counts=DashboardCounts(
            total=by_view[View.ALL],
            in_force=by_view[View.IN_FORCE],
            at_risk=by_view[View.AT_RISK],
            expired=by_view[View.EXPIRED],
            not_started=by_view[View.NOT_STARTED],
            no_end_date=by_view[View.NO_END_DATE],
        ),
        at_risk_breakdown=AtRiskBreakdown(
            expiring_soon=data.counts.expiring_soon, high_risk=data.counts.high_risk
        ),
        by_lifecycle=[
            LifecycleCount(lifecycle=lifecycle, count=by_view[View(lifecycle.value)])
            for lifecycle in READ_LIFECYCLES
        ],
        needs_attention=[_item(row, today, days) for row in data.needs_attention],
        unread=Unread(processing=by_view[View.PROCESSING], failed=by_view[View.FAILED]),
        links={
            "total": ListLink(view=View.ALL),
            **{view.value: ListLink(view=view) for view in View if view != View.ALL},
        },
    )


async def _get_contract(session: AsyncSession, contract_id: uuid.UUID) -> Contract:
    contract = await session.scalar(
        select(Contract)
        .where(Contract.id == contract_id)
        .options(
            selectinload(Contract.parties),
            selectinload(Contract.key_dates),
            selectinload(Contract.terms),
            selectinload(Contract.risks),
        )
    )
    if contract is None:
        raise contract_not_found()
    return contract


@router.get("/{contract_id}", response_model=ContractDetail)
async def get_contract(
    request: Request, contract_id: ContractId, today: Today, session: Session
) -> ContractDetail:
    days = _at_risk_days(request)
    contract = await _get_contract(session, contract_id)
    lifecycle = lifecycle_of(
        contract.processing_status, contract.start_date, contract.end_date, today
    )
    high_risks = sum(1 for risk in contract.risks if risk.severity == "high")
    reasons = at_risk_reasons(lifecycle, contract.end_date, high_risks, today, days)
    return ContractDetail(
        today=today,
        id=contract.id,
        title=contract.title or contract.file_name,
        file_name=contract.file_name,
        file_type=contract.file_type,
        uploaded_at=contract.uploaded_at,
        processing_status=contract.processing_status,
        error_message=contract.error_message,
        lifecycle=lifecycle,
        at_risk=bool(reasons),
        at_risk_reasons=reasons,
        high_risk_count=high_risks,
        start_date=contract.start_date,
        end_date=contract.end_date,
        days_until_end=_days(contract.end_date, today),
        summary=contract.summary,
        parties=[PartyOut(name=p.name, role=p.role) for p in contract.parties],
        key_dates=[
            KeyDateOut(
                label=k.label,
                date=k.date,
                days_from_today=(k.date - today).days,
                source_text=k.source_text,
                source_verified=k.source_verified,
            )
            for k in sorted(contract.key_dates, key=lambda k: (k.date, k.position))
        ],
        terms=[
            TermOut(
                category=t.category,
                summary=t.summary,
                source_text=t.source_text,
                source_verified=t.source_verified,
            )
            for t in sorted(contract.terms, key=lambda t: (CATEGORY_ORDER[t.category], t.position))
        ],
        risks=[
            RiskOut(
                severity=r.severity,
                title=r.title,
                description=r.description,
                source_text=r.source_text,
                source_verified=r.source_verified,
            )
            for r in sorted(contract.risks, key=lambda r: (SEVERITY_ORDER[r.severity], r.position))
        ],
        extraction_model=contract.extraction_model,
        processed_at=contract.processing_finished_at
        if contract.processing_status == "completed"
        else None,
    )


@router.get("/{contract_id}/file", response_class=FileResponse)
async def download_original(contract_id: ContractId, session: Session) -> FileResponse:
    contract = await session.get(Contract, contract_id)
    if contract is None:
        raise contract_not_found()
    return FileResponse(
        Path(contract.stored_path),
        media_type=MEDIA_TYPES[contract.file_type],
        filename=contract.file_name,
    )
