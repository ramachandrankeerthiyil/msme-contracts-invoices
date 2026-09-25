import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.domain.invoice_status import Status, View


class Rejection(BaseModel):
    row: int
    invoice_number: str | None
    reason: str


class Overwrite(BaseModel):
    row: int
    replaced_row: int
    invoice_number: str


class UploadListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    file_name: str
    uploaded_at: datetime
    status: Literal["completed", "no_valid_rows"]
    rows_total: int
    rows_created: int
    rows_updated: int
    rows_overwritten: int
    rows_rejected: int


class UploadSummary(UploadListItem):
    rejections: list[Rejection]
    overwrites: list[Overwrite]


class UploadPage(BaseModel):
    items: list[UploadListItem]
    total: int
    page: int
    page_size: int


# --- INV-002: invoice list -----------------------------------------------------------------


class InvoiceItem(BaseModel):
    id: uuid.UUID
    invoice_number: str
    customer_name: str
    date_raised: date
    due_date: date
    amount: Decimal
    paid_date: date | None
    status: Status
    days_until_due: int | None
    record_status: Literal["new", "updated"]
    record_updated_at: datetime | None


class ViewCounts(BaseModel):
    follow_up: int
    outstanding: int
    at_risk: int
    open: int
    paid: int
    all: int


class InvoicePage(BaseModel):
    today: date
    items: list[InvoiceItem]
    total: int
    page: int
    page_size: int
    total_amount: Decimal
    counts: ViewCounts


# --- INV-003: dashboard --------------------------------------------------------------------


class WeekOut(BaseModel):
    start: date
    end: date
    anchor_uploaded_at: datetime


class FollowUpOut(BaseModel):
    total: int
    outstanding: int
    at_risk: int


class StatusValue(BaseModel):
    status: Status
    amount: Decimal
    count: int


class TopFollowUpItem(BaseModel):
    id: uuid.UUID
    invoice_number: str
    customer_name: str
    amount: Decimal
    due_date: date
    days_until_due: int | None
    status: Status


class ListLink(BaseModel):
    """Query parameters for GET /api/invoices that return exactly the invoices behind a card."""

    view: View
    due_from: date | None = None
    due_to: date | None = None


class DashboardLinks(BaseModel):
    this_week: ListLink
    follow_up: ListLink


class Dashboard(BaseModel):
    today: date
    has_data: bool
    week: WeekOut | None = None
    value_this_week: Decimal | None = None
    invoices_this_week: int | None = None
    follow_up: FollowUpOut | None = None
    value_by_status: list[StatusValue] | None = None
    top_follow_up: list[TopFollowUpItem] | None = None
    links: DashboardLinks | None = None
