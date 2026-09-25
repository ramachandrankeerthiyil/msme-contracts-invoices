import uuid
from datetime import date, datetime

from pydantic import BaseModel

from app.domain.contract_status import Lifecycle, View

# --- CON-001 -------------------------------------------------------------------------------


class UploadAccepted(BaseModel):
    id: uuid.UUID
    processing_status: str


# --- CON-002: list ---------------------------------------------------------------------------


class ContractListItem(BaseModel):
    id: uuid.UUID
    title: str
    file_name: str
    parties: list[str]
    start_date: date | None
    end_date: date | None
    days_until_end: int | None
    lifecycle: Lifecycle
    at_risk: bool
    at_risk_reasons: list[str]
    high_risk_count: int
    uploaded_at: datetime
    processing_status: str


class ViewCounts(BaseModel):
    all: int
    in_force: int
    at_risk: int
    not_started: int
    expired: int
    no_end_date: int
    processing: int
    failed: int


class ContractPage(BaseModel):
    today: date
    items: list[ContractListItem]
    total: int
    page: int
    page_size: int
    counts: ViewCounts


# --- CON-002: detail -------------------------------------------------------------------------


class PartyOut(BaseModel):
    name: str
    role: str


class KeyDateOut(BaseModel):
    label: str
    date: date
    days_from_today: int
    source_text: str
    source_verified: bool


class TermOut(BaseModel):
    category: str
    summary: str
    source_text: str
    source_verified: bool


class RiskOut(BaseModel):
    severity: str
    title: str
    description: str
    source_text: str
    source_verified: bool


class ContractDetail(BaseModel):
    today: date
    id: uuid.UUID
    title: str
    file_name: str
    file_type: str
    uploaded_at: datetime
    processing_status: str
    error_message: str | None
    lifecycle: Lifecycle
    at_risk: bool
    at_risk_reasons: list[str]
    high_risk_count: int
    start_date: date | None
    end_date: date | None
    days_until_end: int | None
    summary: str | None
    parties: list[PartyOut]
    key_dates: list[KeyDateOut]
    terms: list[TermOut]
    risks: list[RiskOut]
    extraction_model: str | None
    processed_at: datetime | None


# --- CON-003: dashboard ----------------------------------------------------------------------


class DashboardCounts(BaseModel):
    total: int
    in_force: int
    at_risk: int
    expired: int
    not_started: int
    no_end_date: int


class AtRiskBreakdown(BaseModel):
    expiring_soon: int
    high_risk: int


class LifecycleCount(BaseModel):
    lifecycle: Lifecycle
    count: int


class Unread(BaseModel):
    processing: int
    failed: int


class ListLink(BaseModel):
    view: View


class Dashboard(BaseModel):
    today: date
    has_data: bool
    counts: DashboardCounts | None = None
    at_risk_breakdown: AtRiskBreakdown | None = None
    by_lifecycle: list[LifecycleCount] | None = None
    needs_attention: list[ContractListItem] | None = None
    unread: Unread | None = None
    links: dict[str, ListLink] | None = None
