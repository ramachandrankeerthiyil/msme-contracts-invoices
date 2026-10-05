import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, StringConstraints, field_validator

from app.domain.invoice_status import Status, View
from app.domain.reminders import MAX_MESSAGE_LENGTH, MAX_SUBJECT_LENGTH


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
    customer_email: str | None  # INV-004
    can_remind: bool  # INV-004: true when the invoice is Outstanding
    last_reminder_at: datetime | None  # INV-004


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


# --- INV-004: email reminder ---------------------------------------------------------------


class ReminderDraftOut(BaseModel):
    invoice_id: uuid.UUID
    invoice_number: str
    customer_name: str
    to: str | None
    subject: str
    message: str
    last_reminder_at: datetime | None


class SendReminderIn(BaseModel):
    """Exactly a subject and a message. Any other field, such as `to`, is rejected (AC10)."""

    model_config = ConfigDict(extra="forbid")

    subject: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=MAX_SUBJECT_LENGTH)
    ]
    message: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=MAX_MESSAGE_LENGTH)
    ]

    @field_validator("subject")
    @classmethod
    def subject_on_one_line(cls, value: str) -> str:
        if "\r" in value or "\n" in value:
            raise ValueError("The subject must be on one line.")
        return value


class ReminderOut(BaseModel):
    id: uuid.UUID
    invoice_id: uuid.UUID
    to: str
    sent_at: datetime


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
