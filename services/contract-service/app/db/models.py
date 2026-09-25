"""Contract tables (CON-001 design "Data"). Tables live in the service schema via search_path."""

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

PROCESSING_STATUSES = ("uploaded", "extracting_text", "analysing", "completed", "failed")
IN_PROGRESS = ("uploaded", "extracting_text", "analysing")
TERM_CATEGORIES = (
    "payment",
    "termination",
    "renewal",
    "liability",
    "confidentiality",
    "governing_law",
    "other",
)
SEVERITIES = ("high", "medium", "low")


def _in(values: tuple[str, ...]) -> str:
    return ", ".join(f"'{value}'" for value in values)


class Base(DeclarativeBase):
    pass


class Contract(Base):
    __tablename__ = "contracts"
    __table_args__ = (
        CheckConstraint(
            f"processing_status IN ({_in(PROCESSING_STATUSES)})", name="ck_contracts_status"
        ),
        CheckConstraint("file_type IN ('pdf', 'docx')", name="ck_contracts_file_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    file_name: Mapped[str] = mapped_column(Text)
    file_type: Mapped[str] = mapped_column(Text)
    file_size: Mapped[int] = mapped_column(Integer)
    file_sha256: Mapped[str] = mapped_column(Text, unique=True)
    stored_path: Mapped[str] = mapped_column(Text)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    processing_status: Mapped[str] = mapped_column(Text, index=True)
    error_code: Mapped[str | None] = mapped_column(Text)
    error_message: Mapped[str | None] = mapped_column(Text)
    processing_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    processing_finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    page_count: Mapped[int | None] = mapped_column(Integer)
    text_chars: Mapped[int | None] = mapped_column(Integer)

    title: Mapped[str | None] = mapped_column(Text)
    summary: Mapped[str | None] = mapped_column(Text)
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date, index=True)

    extraction_model: Mapped[str | None] = mapped_column(Text)
    raw_extraction: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    input_tokens: Mapped[int | None] = mapped_column(Integer)
    output_tokens: Mapped[int | None] = mapped_column(Integer)
    cache_read_tokens: Mapped[int | None] = mapped_column(Integer)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    parties: Mapped[list["ContractParty"]] = relationship(
        order_by="ContractParty.position", cascade="all, delete-orphan"
    )
    key_dates: Mapped[list["ContractKeyDate"]] = relationship(
        order_by="ContractKeyDate.position", cascade="all, delete-orphan"
    )
    terms: Mapped[list["ContractTerm"]] = relationship(
        order_by="ContractTerm.position", cascade="all, delete-orphan"
    )
    risks: Mapped[list["ContractRisk"]] = relationship(
        order_by="ContractRisk.position", cascade="all, delete-orphan"
    )


class _Child:
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    contract_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("contracts.id", ondelete="CASCADE"), index=True
    )
    position: Mapped[int] = mapped_column(Integer)


class ContractParty(_Child, Base):
    __tablename__ = "contract_parties"

    name: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(Text)


class ContractKeyDate(_Child, Base):
    __tablename__ = "contract_key_dates"

    label: Mapped[str] = mapped_column(Text)
    date: Mapped[date] = mapped_column(Date)
    source_text: Mapped[str] = mapped_column(Text)
    source_verified: Mapped[bool] = mapped_column(Boolean)


class ContractTerm(_Child, Base):
    __tablename__ = "contract_terms"
    __table_args__ = (
        CheckConstraint(f"category IN ({_in(TERM_CATEGORIES)})", name="ck_terms_category"),
    )

    category: Mapped[str] = mapped_column(Text)
    summary: Mapped[str] = mapped_column(Text)
    source_text: Mapped[str] = mapped_column(Text)
    source_verified: Mapped[bool] = mapped_column(Boolean)


class ContractRisk(_Child, Base):
    __tablename__ = "contract_risks"
    __table_args__ = (
        CheckConstraint(f"severity IN ({_in(SEVERITIES)})", name="ck_risks_severity"),
    )

    severity: Mapped[str] = mapped_column(Text)
    title: Mapped[str] = mapped_column(Text)
    description: Mapped[str] = mapped_column(Text)
    source_text: Mapped[str] = mapped_column(Text)
    source_verified: Mapped[bool] = mapped_column(Boolean)
