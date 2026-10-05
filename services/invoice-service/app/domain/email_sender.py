"""Sending a reminder email over SMTP (INV-004, ADR-0004).

Plain text only. Header injection is prevented twice: the API rejects a subject with a line
break, and `EmailMessage` itself refuses CR/LF in any header. The recipient is passed separately
as the SMTP envelope address, so it can never turn into several recipients.
"""

import asyncio
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr, formatdate, make_msgid
from typing import Protocol

from fastapi import Request

from app.config import Settings


class EmailSendError(Exception):
    """The mail server did not accept the message. `reason` is safe to log (a class name)."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class EmailSender(Protocol):
    async def send(self, message: EmailMessage, *, to: str) -> None: ...


def build_reminder_message(
    *, sender_name: str, sender_address: str, to: str, subject: str, body: str
) -> EmailMessage:
    message = EmailMessage()
    message["From"] = formataddr((sender_name, sender_address))
    message["To"] = to
    message["Subject"] = subject
    message["Date"] = formatdate(localtime=False)
    message["Message-ID"] = make_msgid(domain=sender_address.rpartition("@")[2] or None)
    message.set_content(body)
    return message


class SmtpEmailSender:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def send(self, message: EmailMessage, *, to: str) -> None:
        # smtplib is blocking, so it runs in a worker thread.
        await asyncio.to_thread(self._send_blocking, message, to)

    def _send_blocking(self, message: EmailMessage, to: str) -> None:
        settings = self._settings
        try:
            with smtplib.SMTP(
                settings.smtp_host, settings.smtp_port, timeout=settings.smtp_timeout_seconds
            ) as smtp:
                if settings.smtp_starttls:
                    smtp.starttls(context=ssl.create_default_context())
                if settings.smtp_username:
                    smtp.login(settings.smtp_username, settings.smtp_password.get_secret_value())
                smtp.send_message(message, to_addrs=[to])
        except OSError as exc:  # smtplib.SMTPException, timeouts and TLS errors are all OSError
            raise EmailSendError(type(exc).__name__) from exc


def get_email_sender(request: Request) -> EmailSender:
    """FastAPI dependency. Tests replace it with a recorder, so no socket is ever opened."""
    return request.app.state.email_sender
