"""Email payment reminder endpoints (INV-004). Business rules: invoices/module.md."""

import time
import uuid
from datetime import UTC, date, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from prometheus_client import Counter
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import ReminderDraftOut, ReminderOut, SendReminderIn
from app.config import Settings
from app.core.errors import AppError
from app.core.logging import get_logger
from app.core.metrics import REGISTRY
from app.db import get_session
from app.db.models import Invoice
from app.db.reminder_repo import add_reminder, get_invoice, last_reminder_at
from app.domain.clock import get_today
from app.domain.email_sender import (
    EmailSender,
    EmailSendError,
    build_reminder_message,
    get_email_sender,
)
from app.domain.invoice_status import status_of
from app.domain.reminders import (
    EMAIL_NOT_SENT_MESSAGE,
    NOT_REMINDABLE_MESSAGE,
    compose_draft,
    is_remindable,
    no_customer_email_message,
)

router = APIRouter(tags=["Reminders"])
log = get_logger("invoice_reminder")

INVOICE_REMINDERS = Counter(
    "invoice_reminders_total", "Reminder emails by result", ["result"], registry=REGISTRY
)

Today = Annotated[date, Depends(get_today)]
Session = Annotated[AsyncSession, Depends(get_session)]
Sender = Annotated[EmailSender, Depends(get_email_sender)]


async def _remindable_invoice(
    session: AsyncSession, invoice_id: uuid.UUID, today: date, settings: Settings
) -> Invoice:
    invoice = await get_invoice(session, invoice_id)
    if invoice is None:
        raise AppError("INVOICE_NOT_FOUND", "We couldn't find that invoice.", status=404)
    status = status_of(invoice.due_date, invoice.paid_date, today, settings.invoice_at_risk_days)
    if not is_remindable(status):
        raise AppError("INVOICE_NOT_REMINDABLE", NOT_REMINDABLE_MESSAGE, status=409)
    return invoice


@router.get("/{invoice_id}/reminder-draft", response_model=ReminderDraftOut)
async def reminder_draft(
    invoice_id: uuid.UUID, request: Request, today: Today, session: Session
) -> ReminderDraftOut:
    """Composes the draft. Sends nothing and stores nothing (AC2, AC3)."""
    settings: Settings = request.app.state.settings
    invoice = await _remindable_invoice(session, invoice_id, today, settings)
    draft = compose_draft(
        invoice_number=invoice.invoice_number,
        customer_name=invoice.customer_name,
        amount=invoice.amount,
        date_raised=invoice.date_raised,
        due_date=invoice.due_date,
        today=today,
        sender_name=settings.reminder_sender_name,
    )
    return ReminderDraftOut(
        invoice_id=invoice.id,
        invoice_number=invoice.invoice_number,
        customer_name=invoice.customer_name,
        to=invoice.customer_email,
        subject=draft.subject,
        message=draft.message,
        last_reminder_at=await last_reminder_at(session, invoice.id),
    )


@router.post("/{invoice_id}/reminders", response_model=ReminderOut, status_code=201)
async def send_reminder(
    invoice_id: uuid.UUID,
    body: SendReminderIn,
    request: Request,
    today: Today,
    session: Session,
    sender: Sender,
) -> ReminderOut:
    """Sends the user-approved subject and message to the invoice's stored address (AC5-AC10)."""
    settings: Settings = request.app.state.settings
    invoice = await _remindable_invoice(session, invoice_id, today, settings)
    recipient = invoice.customer_email
    if not recipient:
        raise AppError(
            "NO_CUSTOMER_EMAIL", no_customer_email_message(invoice.customer_name), status=409
        )

    message = build_reminder_message(
        sender_name=settings.reminder_sender_name,
        sender_address=settings.smtp_from_address,
        to=recipient,
        subject=body.subject,
        body=body.message,
    )
    started = time.perf_counter()
    try:
        await sender.send(message, to=recipient)
    except EmailSendError as exc:
        INVOICE_REMINDERS.labels(result="failed").inc()
        # No recipient, subject or text in the log (AC12): only the invoice and the reason.
        log.warning(
            "invoice_reminder.failed",
            message="Reminder email was not sent",
            invoice_id=str(invoice_id),
            reason=exc.reason,
            duration_ms=round((time.perf_counter() - started) * 1000, 1),
        )
        raise AppError("EMAIL_NOT_SENT", EMAIL_NOT_SENT_MESSAGE, status=424) from exc

    reminder_id = uuid.uuid4()
    sent_at = datetime.now(UTC)
    try:
        await add_reminder(
            session,
            reminder_id=reminder_id,
            invoice_id=invoice_id,
            recipient=recipient,
            subject=body.subject,
            body=body.message,
            sent_at=sent_at,
        )
    except Exception as exc:
        # The email has gone. Telling the user otherwise would invite a duplicate, so this is
        # logged and the call still succeeds. The reason is a class name: a database error's text
        # can include the recipient, subject and message (AC12).
        await session.rollback()
        log.error(
            "invoice_reminder.record_failed",
            message="Reminder email was sent but could not be recorded",
            invoice_id=str(invoice_id),
            reason=type(exc).__name__,
        )

    INVOICE_REMINDERS.labels(result="sent").inc()
    log.info(
        "invoice_reminder.sent",
        message="Reminder email sent",
        invoice_id=str(invoice_id),
        reminder_id=str(reminder_id),
        duration_ms=round((time.perf_counter() - started) * 1000, 1),
    )
    return ReminderOut(id=reminder_id, invoice_id=invoice_id, to=recipient, sent_at=sent_at)
