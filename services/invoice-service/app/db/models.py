"""Invoice tables (INV-001 design "Data"). Tables live in the service schema via search_path."""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Integer, Numeric, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class InvoiceUpload(Base):
    __tablename__ = "invoice_uploads"
    __table_args__ = (
        CheckConstraint(
            "status IN ('completed', 'no_valid_rows')", name="ck_invoice_uploads_status"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    file_name: Mapped[str] = mapped_column(Text)
    stored_path: Mapped[str | None] = mapped_column(Text)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(Text)
    rows_total: Mapped[int] = mapped_column(Integer)
    rows_created: Mapped[int] = mapped_column(Integer)
    rows_updated: Mapped[int] = mapped_column(Integer)
    rows_overwritten: Mapped[int] = mapped_column(Integer)
    rows_rejected: Mapped[int] = mapped_column(Integer)
    rejections: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, server_default="[]")
    overwrites: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, server_default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Invoice(Base):
    __tablename__ = "invoices"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_invoices_amount_positive"),
        CheckConstraint("record_status IN ('new', 'updated')", name="ck_invoices_record_status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    invoice_number: Mapped[str] = mapped_column(Text)
    invoice_number_key: Mapped[str] = mapped_column(Text, unique=True)
    customer_name: Mapped[str] = mapped_column(Text)
    date_raised: Mapped[date] = mapped_column(Date)
    due_date: Mapped[date] = mapped_column(Date, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    paid_date: Mapped[date | None] = mapped_column(Date, index=True)
    customer_email: Mapped[str | None] = mapped_column(Text)
    record_status: Mapped[str] = mapped_column(Text)
    record_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    first_upload_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("invoice_uploads.id"))
    last_upload_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("invoice_uploads.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class InvoiceReminder(Base):
    """One reminder email the mail server accepted (INV-004). Failures are never stored."""

    __tablename__ = "invoice_reminders"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    invoice_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("invoices.id", ondelete="CASCADE"))
    recipient: Mapped[str] = mapped_column(Text)
    subject: Mapped[str] = mapped_column(Text)
    body: Mapped[str] = mapped_column(Text)
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
