"""create invoice tables (INV-001)

Revision ID: 0001
Revises:
Create Date: 2026-09-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    ]


def upgrade() -> None:
    op.create_table(
        "invoice_uploads",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("file_name", sa.Text(), nullable=False),
        sa.Column("stored_path", sa.Text()),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("rows_total", sa.Integer(), nullable=False),
        sa.Column("rows_created", sa.Integer(), nullable=False),
        sa.Column("rows_updated", sa.Integer(), nullable=False),
        sa.Column("rows_overwritten", sa.Integer(), nullable=False),
        sa.Column("rows_rejected", sa.Integer(), nullable=False),
        sa.Column("rejections", JSONB(), nullable=False, server_default="[]"),
        sa.Column("overwrites", JSONB(), nullable=False, server_default="[]"),
        *_timestamps(),
        sa.CheckConstraint(
            "status IN ('completed', 'no_valid_rows')", name="ck_invoice_uploads_status"
        ),
    )
    op.create_index("ix_invoice_uploads_uploaded_at", "invoice_uploads", ["uploaded_at"])

    op.create_table(
        "invoices",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("invoice_number", sa.Text(), nullable=False),
        sa.Column("invoice_number_key", sa.Text(), nullable=False, unique=True),
        sa.Column("customer_name", sa.Text(), nullable=False),
        sa.Column("date_raised", sa.Date(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("paid_date", sa.Date()),
        sa.Column("record_status", sa.Text(), nullable=False),
        sa.Column("record_updated_at", sa.DateTime(timezone=True)),
        sa.Column(
            "first_upload_id", sa.Uuid(), sa.ForeignKey("invoice_uploads.id"), nullable=False
        ),
        sa.Column("last_upload_id", sa.Uuid(), sa.ForeignKey("invoice_uploads.id"), nullable=False),
        *_timestamps(),
        sa.CheckConstraint("amount > 0", name="ck_invoices_amount_positive"),
        sa.CheckConstraint("record_status IN ('new', 'updated')", name="ck_invoices_record_status"),
    )
    op.create_index("ix_invoices_due_date", "invoices", ["due_date"])
    op.create_index("ix_invoices_paid_date", "invoices", ["paid_date"])


def downgrade() -> None:
    op.drop_table("invoices")
    op.drop_table("invoice_uploads")
