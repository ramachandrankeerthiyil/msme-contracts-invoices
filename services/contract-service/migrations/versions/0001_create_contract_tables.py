"""create contract tables (CON-001)

Revision ID: 0001
Revises:
Create Date: 2026-09-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

STATUSES = "'uploaded', 'extracting_text', 'analysing', 'completed', 'failed'"
CATEGORIES = (
    "'payment', 'termination', 'renewal', 'liability', 'confidentiality', 'governing_law', 'other'"
)


def _timestamps() -> list[sa.Column]:
    now = sa.func.now()
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=now),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=now),
    ]


def _child(name: str, *columns: sa.Column, checks: tuple[sa.CheckConstraint, ...] = ()) -> None:
    op.create_table(
        name,
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "contract_id",
            sa.Uuid(),
            sa.ForeignKey("contracts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("position", sa.Integer(), nullable=False),
        *columns,
        *checks,
    )
    op.create_index(f"ix_{name}_contract_id", name, ["contract_id"])


def upgrade() -> None:
    op.create_table(
        "contracts",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("file_name", sa.Text(), nullable=False),
        sa.Column("file_type", sa.Text(), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("file_sha256", sa.Text(), nullable=False, unique=True),
        sa.Column("stored_path", sa.Text(), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("processing_status", sa.Text(), nullable=False),
        sa.Column("error_code", sa.Text()),
        sa.Column("error_message", sa.Text()),
        sa.Column("processing_started_at", sa.DateTime(timezone=True)),
        sa.Column("processing_finished_at", sa.DateTime(timezone=True)),
        sa.Column("page_count", sa.Integer()),
        sa.Column("text_chars", sa.Integer()),
        sa.Column("title", sa.Text()),
        sa.Column("summary", sa.Text()),
        sa.Column("start_date", sa.Date()),
        sa.Column("end_date", sa.Date()),
        sa.Column("extraction_model", sa.Text()),
        sa.Column("raw_extraction", JSONB()),
        sa.Column("input_tokens", sa.Integer()),
        sa.Column("output_tokens", sa.Integer()),
        sa.Column("cache_read_tokens", sa.Integer()),
        *_timestamps(),
        sa.CheckConstraint(f"processing_status IN ({STATUSES})", name="ck_contracts_status"),
        sa.CheckConstraint("file_type IN ('pdf', 'docx')", name="ck_contracts_file_type"),
    )
    op.create_index("ix_contracts_processing_status", "contracts", ["processing_status"])
    op.create_index("ix_contracts_end_date", "contracts", ["end_date"])

    _child(
        "contract_parties",
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("role", sa.Text(), nullable=False),
    )
    _child(
        "contract_key_dates",
        sa.Column("label", sa.Text(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("source_text", sa.Text(), nullable=False),
        sa.Column("source_verified", sa.Boolean(), nullable=False),
    )
    _child(
        "contract_terms",
        sa.Column("category", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("source_text", sa.Text(), nullable=False),
        sa.Column("source_verified", sa.Boolean(), nullable=False),
        checks=(sa.CheckConstraint(f"category IN ({CATEGORIES})", name="ck_terms_category"),),
    )
    _child(
        "contract_risks",
        sa.Column("severity", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("source_text", sa.Text(), nullable=False),
        sa.Column("source_verified", sa.Boolean(), nullable=False),
        checks=(
            sa.CheckConstraint("severity IN ('high', 'medium', 'low')", name="ck_risks_severity"),
        ),
    )
    op.create_index("ix_contract_risks_severity", "contract_risks", ["contract_id", "severity"])


def downgrade() -> None:
    for table in ("contract_risks", "contract_terms", "contract_key_dates", "contract_parties"):
        op.drop_table(table)
    op.drop_table("contracts")
