"""Invoice persistence (INV-001 design "Logic §5")."""

import uuid
from collections.abc import Iterator, Sequence
from datetime import datetime
from typing import Any

from sqlalchemy import func, literal_column, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Invoice, InvoiceUpload
from app.domain.duplicates import ResolvedRows

# Keeps each INSERT well under Postgres' 32,767 bind-parameter limit (12 columns per row).
UPSERT_BATCH_SIZE = 1000


def _batches(items: Sequence[Any], size: int) -> Iterator[Sequence[Any]]:
    for start in range(0, len(items), size):
        yield items[start : start + size]


async def upsert_invoices(
    session: AsyncSession, *, upload_id: uuid.UUID, now: datetime, resolved: ResolvedRows
) -> tuple[int, int]:
    """Creates new invoices and overwrites existing ones. Returns (created, updated)."""
    rows = []
    for key, (invoice, _row) in resolved.invoices.items():
        replaced_in_file = key in resolved.overwritten_keys
        rows.append(
            {
                "id": uuid.uuid4(),
                "invoice_number": invoice.invoice_number,
                "invoice_number_key": key,
                "customer_name": invoice.customer_name,
                "date_raised": invoice.date_raised,
                "due_date": invoice.due_date,
                "amount": invoice.amount,
                "paid_date": invoice.paid_date,
                "record_status": "updated" if replaced_in_file else "new",
                "record_updated_at": now if replaced_in_file else None,
                "first_upload_id": upload_id,
                "last_upload_id": upload_id,
            }
        )

    created = updated = 0
    for batch in _batches(rows, UPSERT_BATCH_SIZE):
        statement = pg_insert(Invoice).values(list(batch))
        excluded = statement.excluded
        statement = statement.on_conflict_do_update(
            index_elements=[Invoice.invoice_number_key],
            set_={
                "invoice_number": excluded.invoice_number,
                "customer_name": excluded.customer_name,
                "date_raised": excluded.date_raised,
                "due_date": excluded.due_date,
                "amount": excluded.amount,
                "paid_date": excluded.paid_date,
                "record_status": "updated",
                "record_updated_at": now,
                "last_upload_id": excluded.last_upload_id,
                "updated_at": now,
            },
        ).returning(literal_column("(xmax = 0)").label("inserted"))
        for (inserted,) in await session.execute(statement):
            if inserted:
                created += 1
            else:
                updated += 1
    return created, updated


async def list_uploads(
    session: AsyncSession, *, page: int, page_size: int
) -> tuple[list[InvoiceUpload], int]:
    total = await session.scalar(select(func.count()).select_from(InvoiceUpload)) or 0
    result = await session.scalars(
        select(InvoiceUpload)
        .order_by(InvoiceUpload.uploaded_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(result), total
