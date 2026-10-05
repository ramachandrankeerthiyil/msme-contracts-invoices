"""INV-004 API tests: draft and send endpoints, with "today" pinned to 25 Sep 2026 and a
recording stand-in for the mail server (no socket is ever opened)."""

from datetime import date, timedelta
from decimal import Decimal
from email.message import EmailMessage

import pytest
from fastapi.testclient import TestClient

from app.core.metrics import REGISTRY
from app.domain.clock import get_today
from app.domain.email_sender import EmailSendError, get_email_sender
from app.domain.reminders import compose_draft
from app.main import create_app
from tests.invoices.workbooks import HEADERS_WITH_EMAIL, row, upload, workbook_bytes

TODAY = date(2026, 9, 25)
CLIENT_EMAIL = "accounts@deccanprinting.example"
UNKNOWN_ID = "00000000-0000-4000-8000-000000000000"


def d(offset: int) -> date:
    return TODAY + timedelta(days=offset)


# number, customer, raised, due, amount, paid, email
INVOICES = [
    ("OUT-1", "Deccan Printing Works", d(-71), d(-41), 125000, None, CLIENT_EMAIL),
    ("OUT-2", "Nilgiri Tea Traders", d(-36), d(-6), 54000, None, None),
    ("RISK-1", "Green Leaf Organics", d(-26), d(4), 31500, None, "pay@greenleaf.example"),
    ("OPEN-1", "Sunrise Pharma", d(-11), d(19), 410000, None, "ap@sunrise.example"),
    ("PAID-1", "Bluewave Logistics LLP", d(-41), d(-11), 96400, d(-13), "ap@bluewave.example"),
]


class RecordingSender:
    """Stands in for the SMTP server: records every message, or fails on demand."""

    def __init__(self) -> None:
        self.sent: list[tuple[EmailMessage, str]] = []
        self.failure: Exception | None = None

    async def send(self, message: EmailMessage, *, to: str) -> None:
        if self.failure:
            raise self.failure
        self.sent.append((message, to))


@pytest.fixture
def sender() -> RecordingSender:
    return RecordingSender()


@pytest.fixture
def client(settings, uploads_dir, clean_tables, sender):
    app = create_app(settings.model_copy(update={"uploads_dir": str(uploads_dir)}))
    app.dependency_overrides[get_today] = lambda: TODAY
    app.dependency_overrides[get_email_sender] = lambda: sender
    with TestClient(app) as test_client:
        yield test_client


def load(client, invoices=INVOICES) -> dict[str, str]:
    rows = [row(n, c, r, due, a, p) + [e] for n, c, r, due, a, p, e in invoices]
    body = upload(client, workbook_bytes(rows, headers=HEADERS_WITH_EMAIL)).json()
    assert body["rows_rejected"] == 0, body
    return {item["invoice_number"]: item["id"] for item in list_all(client)}


def list_all(client) -> list[dict]:
    response = client.get("/api/invoices?view=all&page_size=100")
    assert response.status_code == 200, response.text
    return response.json()["items"]


def item(client, number: str) -> dict:
    return next(i for i in list_all(client) if i["invoice_number"] == number)


def draft_url(invoice_id: str) -> str:
    return f"/api/invoices/{invoice_id}/reminder-draft"


def send_url(invoice_id: str) -> str:
    return f"/api/invoices/{invoice_id}/reminders"


GOOD = {"subject": "Payment reminder", "message": "Dear Deccan,\n\nPlease pay invoice OUT-1."}


def reminder_rows(db_rows):
    return db_rows(
        "SELECT recipient, subject, body, sent_at FROM invoice_reminders ORDER BY sent_at"
    )


# --- AC1: who gets a button -----------------------------------------------------------------


def test_INV_004_AC1_only_outstanding_invoices_can_be_reminded(client):
    load(client)

    flags = {i["invoice_number"]: (i["status"], i["can_remind"]) for i in list_all(client)}

    assert flags == {
        "OUT-1": ("outstanding", True),
        "OUT-2": ("outstanding", True),
        "RISK-1": ("at_risk", False),
        "OPEN-1": ("open", False),
        "PAID-1": ("paid", False),
    }


def test_INV_004_AC1_the_list_carries_the_stored_email_and_no_reminder_yet(client):
    load(client)

    out1, out2 = item(client, "OUT-1"), item(client, "OUT-2")

    assert (out1["customer_email"], out1["last_reminder_at"]) == (CLIENT_EMAIL, None)
    assert (out2["customer_email"], out2["last_reminder_at"]) == (None, None)


# --- AC2, AC3: the draft --------------------------------------------------------------------


def test_INV_004_AC2_the_draft_has_to_subject_and_message_and_sends_nothing(
    client, sender, db_rows
):
    ids = load(client)

    response = client.get(draft_url(ids["OUT-1"]))

    assert response.status_code == 200
    body = response.json()
    assert body["invoice_id"] == ids["OUT-1"]
    assert (body["invoice_number"], body["customer_name"]) == ("OUT-1", "Deccan Printing Works")
    assert body["to"] == CLIENT_EMAIL
    assert body["subject"] and body["message"]
    assert body["last_reminder_at"] is None
    assert sender.sent == []
    assert reminder_rows(db_rows) == []


def test_INV_004_AC3_the_draft_is_composed_from_the_invoices_own_data(client, settings):
    ids = load(client)

    body = client.get(draft_url(ids["OUT-1"])).json()

    expected = compose_draft(
        invoice_number="OUT-1",
        customer_name="Deccan Printing Works",
        amount=Decimal("125000.00"),
        date_raised=d(-71),
        due_date=d(-41),
        today=TODAY,
        sender_name=settings.reminder_sender_name,
    )
    assert body["subject"] == expected.subject
    assert body["message"] == expected.message
    assert "₹1,25,000.00" in body["subject"]
    assert "41 days overdue" in body["message"]


def test_INV_004_AC3_the_draft_uses_the_invoices_days_overdue_not_a_fixed_number(client):
    ids = load(client)

    body = client.get(draft_url(ids["OUT-2"])).json()

    assert "6 days overdue" in body["message"]
    assert "Nilgiri Tea Traders" in body["message"]


# --- AC4, AC10: what may be sent ------------------------------------------------------------


@pytest.mark.parametrize(
    "payload",
    [
        {"subject": "", "message": "Text"},
        {"subject": "   ", "message": "Text"},
        {"subject": "S" * 201, "message": "Text"},
        {"subject": "Hello", "message": ""},
        {"subject": "Hello", "message": "M" * 5001},
        {"subject": "Hello"},
        {"message": "Text"},
        {},
    ],
)
def test_INV_004_AC4_invalid_subject_or_message_is_rejected_and_nothing_is_sent(
    client, sender, db_rows, payload
):
    ids = load(client)

    response = client.post(send_url(ids["OUT-1"]), json=payload)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert sender.sent == []
    assert reminder_rows(db_rows) == []


def test_INV_004_AC4_the_length_limits_are_inclusive(client, sender):
    ids = load(client)

    response = client.post(
        send_url(ids["OUT-1"]), json={"subject": "S" * 200, "message": "M" * 5000}
    )

    assert response.status_code == 201
    assert len(sender.sent) == 1


@pytest.mark.parametrize("subject", ["Line one\nLine two", "a\r\nBcc: victim@elsewhere.example"])
def test_INV_004_AC10_a_subject_with_a_line_break_is_rejected(client, sender, subject):
    ids = load(client)

    response = client.post(send_url(ids["OUT-1"]), json={**GOOD, "subject": subject})

    assert response.status_code == 422
    assert sender.sent == []


@pytest.mark.parametrize("extra", ["to", "cc", "bcc", "from", "recipient"])
def test_INV_004_AC10_the_browser_cannot_supply_a_recipient(client, sender, db_rows, extra):
    ids = load(client)

    response = client.post(
        send_url(ids["OUT-1"]), json={**GOOD, extra: "someone-else@elsewhere.example"}
    )

    assert response.status_code == 422
    assert sender.sent == []
    assert reminder_rows(db_rows) == []


# --- AC5: sending ---------------------------------------------------------------------------


def test_INV_004_AC5_the_reminder_is_sent_once_to_the_stored_address(client, sender, settings):
    ids = load(client)

    response = client.post(send_url(ids["OUT-1"]), json=GOOD)

    assert response.status_code == 201
    body = response.json()
    assert body["invoice_id"] == ids["OUT-1"]
    assert body["to"] == CLIENT_EMAIL
    assert body["id"] and body["sent_at"]

    assert len(sender.sent) == 1
    message, envelope_to = sender.sent[0]
    assert envelope_to == CLIENT_EMAIL
    assert message["To"] == CLIENT_EMAIL
    assert message["Subject"] == GOOD["subject"]
    assert settings.smtp_from_address in message["From"]
    assert settings.reminder_sender_name in message["From"]
    assert message.get_content().strip() == GOOD["message"]
    assert message.get_all("Cc") is None and message.get_all("Bcc") is None


def test_INV_004_AC5_the_subject_and_message_sent_are_the_ones_the_user_edited(client, sender):
    ids = load(client)
    edited = {"subject": "  Quick note about OUT-1  ", "message": "Hi team,\nPlease check.\n"}

    client.post(send_url(ids["OUT-1"]), json=edited)

    message, _ = sender.sent[0]
    assert message["Subject"] == "Quick note about OUT-1"
    assert message.get_content().strip() == "Hi team,\nPlease check."


# --- AC6: no address ------------------------------------------------------------------------


def test_INV_004_AC6_without_an_email_the_draft_has_no_recipient(client):
    ids = load(client)

    body = client.get(draft_url(ids["OUT-2"])).json()

    assert body["to"] is None


def test_INV_004_AC6_without_an_email_nothing_can_be_sent(client, sender, db_rows):
    ids = load(client)

    response = client.post(send_url(ids["OUT-2"]), json=GOOD)

    assert response.status_code == 409
    error = response.json()["error"]
    assert error["code"] == "NO_CUSTOMER_EMAIL"
    assert error["message"] == (
        "We don't have an email address for Nilgiri Tea Traders. "
        "Add it in the Customer Email column of your sheet and upload it again."
    )
    assert sender.sent == []
    assert reminder_rows(db_rows) == []


# --- AC7: the mail server fails -------------------------------------------------------------


def test_INV_004_AC7_a_failed_send_says_so_and_records_nothing(client, sender, db_rows):
    ids = load(client)
    sender.failure = EmailSendError("ConnectionRefusedError")

    response = client.post(send_url(ids["OUT-1"]), json=GOOD)

    assert response.status_code == 424
    error = response.json()["error"]
    assert error["code"] == "EMAIL_NOT_SENT"
    assert error["message"] == (
        "We couldn't send this email, so nothing was sent. Please try again in a minute."
    )
    assert reminder_rows(db_rows) == []
    assert item(client, "OUT-1")["last_reminder_at"] is None


def test_INV_004_AC7_after_a_failure_the_user_can_try_again(client, sender, db_rows):
    ids = load(client)
    sender.failure = EmailSendError("TimeoutError")
    assert client.post(send_url(ids["OUT-1"]), json=GOOD).status_code == 424

    sender.failure = None
    response = client.post(send_url(ids["OUT-1"]), json=GOOD)

    assert response.status_code == 201
    assert len(sender.sent) == 1
    assert len(reminder_rows(db_rows)) == 1


# --- AC8: the reminder is recorded ----------------------------------------------------------


def test_INV_004_AC8_a_sent_reminder_is_recorded_with_what_was_sent(client, db_rows):
    ids = load(client)

    client.post(send_url(ids["OUT-1"]), json=GOOD)

    (stored,) = reminder_rows(db_rows)
    assert stored["recipient"] == CLIENT_EMAIL
    assert stored["subject"] == GOOD["subject"]
    assert stored["body"] == GOOD["message"]
    assert stored["sent_at"] is not None


def test_INV_004_AC8_the_list_and_the_draft_show_the_last_reminder(client):
    ids = load(client)
    sent = client.post(send_url(ids["OUT-1"]), json=GOOD).json()

    assert item(client, "OUT-1")["last_reminder_at"] is not None
    assert item(client, "OUT-2")["last_reminder_at"] is None
    draft = client.get(draft_url(ids["OUT-1"])).json()
    assert draft["last_reminder_at"] is not None
    assert draft["last_reminder_at"][:19] == sent["sent_at"][:19]


def test_INV_004_AC8_a_second_reminder_is_allowed_and_becomes_the_latest(client, sender, db_rows):
    ids = load(client)
    first = client.post(send_url(ids["OUT-1"]), json=GOOD).json()

    second = client.post(send_url(ids["OUT-1"]), json=GOOD)

    assert second.status_code == 201
    assert len(sender.sent) == 2
    assert len(reminder_rows(db_rows)) == 2
    assert item(client, "OUT-1")["last_reminder_at"][:26] >= first["sent_at"][:26]


def test_INV_004_AC8_a_paid_invoice_keeps_its_reminder_history_on_the_list(client, db_rows):
    ids = load(client)
    client.post(send_url(ids["OUT-1"]), json=GOOD)
    paid = [
        (n, c, r, due, a, d(-1) if n == "OUT-1" else p, e) for n, c, r, due, a, p, e in INVOICES
    ]
    load(client, paid)

    after = item(client, "OUT-1")

    assert (after["status"], after["can_remind"]) == ("paid", False)
    assert after["last_reminder_at"] is not None


# --- AC9: no longer overdue -----------------------------------------------------------------


@pytest.mark.parametrize("number", ["RISK-1", "OPEN-1", "PAID-1"])
def test_INV_004_AC9_an_invoice_that_is_not_overdue_gets_no_draft_and_no_email(
    client, sender, db_rows, number
):
    ids = load(client)

    draft = client.get(draft_url(ids[number]))
    send = client.post(send_url(ids[number]), json=GOOD)

    for response in (draft, send):
        assert response.status_code == 409
        error = response.json()["error"]
        assert error["code"] == "INVOICE_NOT_REMINDABLE"
        assert error["message"] == "This invoice is no longer overdue, so no reminder was sent."
    assert sender.sent == []
    assert reminder_rows(db_rows) == []


def test_INV_004_AC9_an_invoice_paid_by_a_later_upload_can_no_longer_be_reminded(client, sender):
    ids = load(client)
    assert client.get(draft_url(ids["OUT-1"])).status_code == 200
    paid = [
        (n, c, r, due, a, d(-1) if n == "OUT-1" else p, e) for n, c, r, due, a, p, e in INVOICES
    ]
    load(client, paid)

    response = client.post(send_url(ids["OUT-1"]), json=GOOD)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "INVOICE_NOT_REMINDABLE"
    assert sender.sent == []


def test_INV_004_AC9_the_send_uses_the_address_stored_at_send_time(client, sender):
    ids = load(client)
    changed = [
        (*inv[:6], "new-address@deccanprinting.example") if inv[0] == "OUT-1" else inv
        for inv in INVOICES
    ]
    load(client, changed)

    body = client.post(send_url(ids["OUT-1"]), json=GOOD).json()

    assert body["to"] == "new-address@deccanprinting.example"
    assert sender.sent[0][1] == "new-address@deccanprinting.example"


def test_INV_004_AC9_an_unknown_invoice_is_not_found(client, sender):
    load(client)

    for response in (
        client.get(draft_url(UNKNOWN_ID)),
        client.post(send_url(UNKNOWN_ID), json=GOOD),
    ):
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "INVOICE_NOT_FOUND"
    assert sender.sent == []


def test_INV_004_a_malformed_invoice_id_is_a_validation_error(client):
    assert client.get(draft_url("not-a-uuid")).status_code == 422
    assert client.post(send_url("not-a-uuid"), json=GOOD).status_code == 422


# --- AC12: nothing personal in logs ---------------------------------------------------------


def sample(name, labels):
    return REGISTRY.get_sample_value(name, labels) or 0.0


def test_INV_004_AC12_a_send_is_logged_without_the_address_subject_or_message(client, sender, logs):
    ids = load(client)
    before = sample("invoice_reminders_total", {"result": "sent"})

    client.post(send_url(ids["OUT-1"]), json=GOOD)

    sent = next(line for line in logs() if line["event"] == "invoice_reminder.sent")
    assert sent["level"] == "info"
    assert sent["invoice_id"] == ids["OUT-1"]
    assert sent["reminder_id"] and "duration_ms" in sent and "request_id" in sent
    everything = "\n".join(str(line) for line in logs())
    for private in (CLIENT_EMAIL, "deccanprinting", GOOD["subject"], "Please pay invoice"):
        assert private not in everything
    assert sample("invoice_reminders_total", {"result": "sent"}) == before + 1


def test_INV_004_AC12_a_failure_is_logged_with_a_reason_and_nothing_personal(client, sender, logs):
    ids = load(client)
    sender.failure = EmailSendError("ConnectionRefusedError")
    before = sample("invoice_reminders_total", {"result": "failed"})

    client.post(send_url(ids["OUT-1"]), json=GOOD)

    failed = next(line for line in logs() if line["event"] == "invoice_reminder.failed")
    assert failed["level"] == "warning"
    assert failed["invoice_id"] == ids["OUT-1"]
    assert failed["reason"] == "ConnectionRefusedError"
    everything = "\n".join(str(line) for line in logs())
    for private in (CLIENT_EMAIL, "deccanprinting", GOOD["subject"], "Please pay invoice"):
        assert private not in everything
    assert sample("invoice_reminders_total", {"result": "failed"}) == before + 1


def test_INV_004_AC12_drafting_logs_nothing_personal(client, logs):
    ids = load(client)

    client.get(draft_url(ids["OUT-1"]))

    everything = "\n".join(str(line) for line in logs())
    assert CLIENT_EMAIL not in everything
    assert "Deccan Printing Works" not in everything


# --- A reminder row failing to save after the mail went out ---------------------------------


def test_INV_004_a_recording_failure_after_a_successful_send_still_reports_success(
    client, sender, logs, monkeypatch
):
    from app.api import reminders

    async def broken_add_reminder(*_args, **_kwargs):
        raise RuntimeError(f"insert failed for {CLIENT_EMAIL}")

    monkeypatch.setattr(reminders, "add_reminder", broken_add_reminder)
    ids = load(client)

    response = client.post(send_url(ids["OUT-1"]), json=GOOD)

    assert response.status_code == 201
    assert len(sender.sent) == 1
    failed = next(line for line in logs() if line["event"] == "invoice_reminder.record_failed")
    assert failed["level"] == "error"
    assert failed["reason"] == "RuntimeError"
    assert CLIENT_EMAIL not in "\n".join(str(line) for line in logs())
