"""Reminder persistence (INV-004 design "Data")."""

import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Invoice, InvoiceReminder


async def get_invoice(session: AsyncSession, invoice_id: uuid.UUID) -> Invoice | None:
    return await session.get(Invoice, invoice_id)


async def last_reminder_at(session: AsyncSession, invoice_id: uuid.UUID) -> datetime | None:
    return await session.scalar(
        select(func.max(InvoiceReminder.sent_at)).where(InvoiceReminder.invoice_id == invoice_id)
    )


async def add_reminder(
    session: AsyncSession,
    *,
    reminder_id: uuid.UUID,
    invoice_id: uuid.UUID,
    recipient: str,
    subject: str,
    body: str,
    sent_at: datetime,
) -> None:
    session.add(
        InvoiceReminder(
            id=reminder_id,
            invoice_id=invoice_id,
            recipient=recipient,
            subject=subject,
            body=body,
            sent_at=sent_at,
        )
    )
    await session.commit()
