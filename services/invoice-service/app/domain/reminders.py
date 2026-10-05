"""Payment reminder rules and the draft email (INV-004 design "Logic"). Pure functions, no I/O."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from app.domain.invoice_rules import display_date
from app.domain.invoice_status import Status

# Which invoices may be reminded. Changing this one set is all it takes to extend the feature.
REMINDABLE_STATUSES = frozenset({Status.OUTSTANDING})

MAX_SUBJECT_LENGTH = 200
MAX_MESSAGE_LENGTH = 5000

NOT_REMINDABLE_MESSAGE = "This invoice is no longer overdue, so no reminder was sent."
EMAIL_NOT_SENT_MESSAGE = (
    "We couldn't send this email, so nothing was sent. Please try again in a minute."
)


def is_remindable(status: Status) -> bool:
    return status in REMINDABLE_STATUSES


def no_customer_email_message(customer_name: str) -> str:
    return (
        f"We don't have an email address for {customer_name}. "
        "Add it in the Customer Email column of your sheet and upload it again."
    )


def format_inr(amount: Decimal) -> str:
    """₹1,25,000.00: Indian digit grouping, as the UI shows amounts (en-IN)."""
    whole, _, fraction = f"{amount.quantize(Decimal('0.01')):.2f}".partition(".")
    head, tail = whole[:-3], whole[-3:]
    groups: list[str] = []
    while len(head) > 2:
        groups.insert(0, head[-2:])
        head = head[:-2]
    if head:
        groups.insert(0, head)
    return f"₹{','.join([*groups, tail])}.{fraction}"


@dataclass(frozen=True)
class ReminderDraft:
    subject: str
    message: str


def compose_draft(
    *,
    invoice_number: str,
    customer_name: str,
    amount: Decimal,
    date_raised: date,
    due_date: date,
    today: date,
    sender_name: str,
) -> ReminderDraft:
    """The reminder for an overdue invoice (AC3). Plain text, one paragraph per line."""
    overdue = (today - due_date).days
    days = f"{overdue} day{'s' if overdue != 1 else ''}"
    total = format_inr(amount)
    subject = (
        f"Payment reminder: invoice {invoice_number} ({total}) was due on {display_date(due_date)}"
    )
    paragraphs = [
        f"Dear {customer_name},",
        (
            f"I hope you are well. This is a friendly reminder that invoice {invoice_number} "
            f"for {total}, raised on {display_date(date_raised)}, was due on "
            f"{display_date(due_date)} and is now {days} overdue."
        ),
        (
            "Please arrange payment at your earliest convenience. If you have already paid, "
            "please ignore this message and let us know the payment details so that we can "
            "update our records."
        ),
        "If you have any questions about this invoice, please get in touch.",
        f"Thank you,\n{sender_name}",
    ]
    return ReminderDraft(subject=subject, message="\n\n".join(paragraphs))
