"""INV-004 unit tests: draft wording, INR formatting, the email message, and SMTP sending."""

import asyncio
import smtplib
import ssl
from datetime import date
from decimal import Decimal
from email.message import EmailMessage

import pytest
from pydantic import ValidationError

from app.api.schemas import SendReminderIn
from app.config import Settings
from app.domain.email_sender import EmailSendError, SmtpEmailSender, build_reminder_message
from app.domain.invoice_status import Status
from app.domain.reminders import (
    REMINDABLE_STATUSES,
    compose_draft,
    format_inr,
    is_remindable,
)

TODAY = date(2026, 9, 25)


def draft(**overrides):
    args = {
        "invoice_number": "INV-2606",
        "customer_name": "Deccan Printing Works",
        "amount": Decimal("125000.00"),
        "date_raised": date(2026, 7, 16),
        "due_date": date(2026, 8, 15),
        "today": TODAY,
        "sender_name": "Accounts Team",
    }
    args.update(overrides)
    return compose_draft(**args)


# --- AC1: who can be reminded ---------------------------------------------------------------


def test_INV_004_AC1_only_outstanding_invoices_can_be_reminded():
    assert frozenset({Status.OUTSTANDING}) == REMINDABLE_STATUSES
    assert {s: is_remindable(s) for s in Status} == {
        Status.OUTSTANDING: True,
        Status.AT_RISK: False,
        Status.OPEN: False,
        Status.PAID: False,
    }


# --- AC3: the draft -------------------------------------------------------------------------


def test_INV_004_AC3_subject_and_message_are_composed_from_the_invoice():
    result = draft()

    assert result.subject == (
        "Payment reminder: invoice INV-2606 (₹1,25,000.00) was due on 15 Aug 2026"
    )
    assert result.message == (
        "Dear Deccan Printing Works,\n\n"
        "I hope you are well. This is a friendly reminder that invoice INV-2606 for ₹1,25,000.00, "
        "raised on 16 Jul 2026, was due on 15 Aug 2026 and is now 41 days overdue.\n\n"
        "Please arrange payment at your earliest convenience. If you have already paid, please "
        "ignore this message and let us know the payment details so that we can update our "
        "records.\n\n"
        "If you have any questions about this invoice, please get in touch.\n\n"
        "Thank you,\nAccounts Team"
    )


def test_INV_004_AC3_one_day_overdue_is_singular():
    result = draft(due_date=date(2026, 9, 24))

    assert "is now 1 day overdue." in result.message


def test_INV_004_AC3_the_sender_name_signs_the_message():
    assert draft(sender_name="Meera at Sunrise Traders").message.endswith(
        "Thank you,\nMeera at Sunrise Traders"
    )


def test_INV_004_AC3_the_draft_is_plain_text_with_the_names_unchanged():
    result = draft(customer_name='R&D <Labs> "Pvt" Ltd')

    assert result.message.startswith('Dear R&D <Labs> "Pvt" Ltd,')
    assert "&amp;" not in result.message


@pytest.mark.parametrize(
    ("amount", "expected"),
    [
        ("0.50", "₹0.50"),
        ("999", "₹999.00"),
        ("1000", "₹1,000.00"),
        ("12500.55", "₹12,500.55"),
        ("125000", "₹1,25,000.00"),
        ("425000", "₹4,25,000.00"),
        ("994150.75", "₹9,94,150.75"),
        ("10000000", "₹1,00,00,000.00"),
        ("123456789.10", "₹12,34,56,789.10"),
    ],
)
def test_INV_004_AC3_amounts_use_indian_digit_grouping(amount, expected):
    assert format_inr(Decimal(amount)) == expected


# --- AC4, AC10: what the browser may send ---------------------------------------------------


def test_INV_004_AC4_subject_and_message_are_trimmed():
    body = SendReminderIn(subject="  Hello  ", message="\n Text \n")

    assert (body.subject, body.message) == ("Hello", "Text")


@pytest.mark.parametrize(
    "payload",
    [
        {"subject": "", "message": "Text"},
        {"subject": "   ", "message": "Text"},
        {"subject": "S" * 201, "message": "Text"},
        {"subject": "Hello", "message": ""},
        {"subject": "Hello", "message": "M" * 5001},
    ],
)
def test_INV_004_AC4_empty_or_over_long_values_are_rejected(payload):
    with pytest.raises(ValidationError):
        SendReminderIn(**payload)


def test_INV_004_AC4_the_limits_themselves_are_accepted():
    body = SendReminderIn(subject="S" * 200, message="M" * 5000)

    assert (len(body.subject), len(body.message)) == (200, 5000)


@pytest.mark.parametrize(
    "subject", ["Line one\nLine two", "Line one\rLine two", "a\r\nBcc: x@y.in"]
)
def test_INV_004_AC10_a_subject_with_a_line_break_is_rejected(subject):
    with pytest.raises(ValidationError, match="one line"):
        SendReminderIn(subject=subject, message="Text")


@pytest.mark.parametrize("extra", ["to", "cc", "bcc", "from"])
def test_INV_004_AC10_no_recipient_field_is_accepted(extra):
    with pytest.raises(ValidationError):
        SendReminderIn(subject="Hello", message="Text", **{extra: "someone@else.in"})


# --- AC5, AC10: the email itself ------------------------------------------------------------


def make_message(**overrides) -> EmailMessage:
    args = {
        "sender_name": "Accounts Team",
        "sender_address": "accounts@acme.in",
        "to": "client@customer.in",
        "subject": "Payment reminder ₹1,25,000.00",
        "body": "Dear client,\n\nPlease pay.",
    }
    args.update(overrides)
    return build_reminder_message(**args)


def test_INV_004_AC5_the_message_is_plain_text_from_the_configured_sender():
    message = make_message()

    assert message["From"] == "Accounts Team <accounts@acme.in>"
    assert message["To"] == "client@customer.in"
    assert message["Subject"] == "Payment reminder ₹1,25,000.00"
    assert message["Date"] and message["Message-ID"].endswith("@acme.in>")
    assert not message.is_multipart()
    assert message.get_content_type() == "text/plain"
    assert message.get_content().strip() == "Dear client,\n\nPlease pay."


def test_INV_004_AC10_a_line_break_cannot_reach_a_header():
    with pytest.raises(ValueError, match="linefeed"):
        make_message(subject="Hello\nBcc: victim@elsewhere.in")


def test_INV_004_AC10_the_message_has_exactly_one_recipient_and_no_hidden_headers():
    message = make_message()

    assert message.get_all("To") == ["client@customer.in"]
    assert message.get_all("Cc") is None
    assert message.get_all("Bcc") is None


# --- AC7, AC14: SMTP sending ----------------------------------------------------------------


class FakeSmtp:
    """Stands in for smtplib.SMTP and records what was done to it."""

    instances: list["FakeSmtp"] = []
    failure: Exception | None = None

    def __init__(self, host, port, timeout):
        self.host, self.port, self.timeout = host, port, timeout
        self.calls: list[tuple] = []
        FakeSmtp.instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False

    def starttls(self, context):
        self.calls.append(("starttls", isinstance(context, ssl.SSLContext)))

    def login(self, username, password):
        self.calls.append(("login", username, password))

    def send_message(self, message, to_addrs):
        if FakeSmtp.failure:
            raise FakeSmtp.failure
        self.calls.append(("send_message", message["To"], to_addrs))


@pytest.fixture
def fake_smtp(monkeypatch):
    FakeSmtp.instances = []
    FakeSmtp.failure = None
    monkeypatch.setattr(smtplib, "SMTP", FakeSmtp)
    return FakeSmtp


SMTP_ENV = (
    "SMTP_HOST",
    "SMTP_PORT",
    "SMTP_USERNAME",
    "SMTP_PASSWORD",
    "SMTP_STARTTLS",
    "SMTP_FROM_ADDRESS",
    "REMINDER_SENDER_NAME",
    "SMTP_TIMEOUT_SECONDS",
)


@pytest.fixture(autouse=True)
def clean_smtp_env(monkeypatch):
    """Real SMTP_* values in the container must not change what these tests expect."""
    for name in SMTP_ENV:
        monkeypatch.delenv(name, raising=False)


def smtp_settings(**overrides) -> Settings:
    return Settings(_env_file=None, **overrides)


def test_INV_004_AC5_a_message_is_sent_to_the_envelope_address(fake_smtp):
    sender = SmtpEmailSender(smtp_settings(smtp_host="mail.example", smtp_port=2525))

    asyncio.run(sender.send(make_message(), to="client@customer.in"))

    (smtp,) = fake_smtp.instances
    assert (smtp.host, smtp.port, smtp.timeout) == ("mail.example", 2525, 10)
    assert smtp.calls == [("send_message", "client@customer.in", ["client@customer.in"])]


def test_INV_004_AC5_starttls_and_login_are_used_when_configured(fake_smtp):
    sender = SmtpEmailSender(
        smtp_settings(smtp_starttls=True, smtp_username="user", smtp_password="s3cret")
    )

    asyncio.run(sender.send(make_message(), to="client@customer.in"))

    (smtp,) = fake_smtp.instances
    assert [call[0] for call in smtp.calls] == ["starttls", "login", "send_message"]
    assert smtp.calls[0] == ("starttls", True)
    assert smtp.calls[1] == ("login", "user", "s3cret")


@pytest.mark.parametrize(
    ("failure", "reason"),
    [
        (ConnectionRefusedError(), "ConnectionRefusedError"),
        (TimeoutError(), "TimeoutError"),
        (smtplib.SMTPAuthenticationError(535, b"bad credentials"), "SMTPAuthenticationError"),
        (smtplib.SMTPRecipientsRefused({"x@y.in": (550, b"no")}), "SMTPRecipientsRefused"),
        (smtplib.SMTPServerDisconnected("gone"), "SMTPServerDisconnected"),
        (ssl.SSLError("handshake"), "SSLError"),
    ],
)
def test_INV_004_AC7_server_problems_become_an_email_send_error(fake_smtp, failure, reason):
    fake_smtp.failure = failure
    sender = SmtpEmailSender(smtp_settings())

    with pytest.raises(EmailSendError) as caught:
        asyncio.run(sender.send(make_message(), to="client@customer.in"))

    assert caught.value.reason == reason


# --- AC14: configuration --------------------------------------------------------------------


def test_INV_004_AC14_defaults_point_at_the_local_mail_sink():
    defaults = smtp_settings()

    assert (defaults.smtp_host, defaults.smtp_port) == ("mailpit", 1025)
    assert defaults.smtp_starttls is False
    assert defaults.smtp_username == ""
    assert defaults.smtp_from_address == "accounts@msme-poc.local"
    assert defaults.reminder_sender_name == "Accounts Team"
    assert defaults.smtp_timeout_seconds == 10


def test_INV_004_AC14_the_smtp_password_is_never_shown():
    secret = smtp_settings(smtp_password="s3cret")

    assert "s3cret" not in repr(secret)
    assert "s3cret" not in secret.model_dump_json()
