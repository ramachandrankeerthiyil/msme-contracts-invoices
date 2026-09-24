"""Parsing and validation of one invoice row (INV-001 design "Logic §3"). Pure functions, no I/O.

Every problem message is plain language, because it is shown to the user as-is.
"""

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any

INVOICE_NUMBER = "Invoice Number"
CUSTOMER_NAME = "Customer Name"
DATE_RAISED = "Date Raised"
DUE_DATE = "Due Date"
AMOUNT = "Amount"
PAID_DATE = "Paid Date"
REQUIRED_COLUMNS = (INVOICE_NUMBER, CUSTOMER_NAME, DATE_RAISED, DUE_DATE, AMOUNT, PAID_DATE)

MAX_INVOICE_NUMBER_LENGTH = 50
MAX_CUSTOMER_NAME_LENGTH = 200
MAX_AMOUNT = Decimal("1000000000000")  # < 10^12 fits NUMERIC(14,2)
CENT = Decimal("0.01")

EXCEL_EPOCH = date(1899, 12, 30)
MAX_EXCEL_SERIAL = 2958465  # 31 Dec 9999
# Day first (Indian convention): 05/09/2026 is 5 September.
TEXT_DATE_FORMATS = ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%d-%b-%Y", "%d %b %Y")

FORMULA_PROBLEM = (
    "{column} contains a formula with no saved value. "
    "Open the file in Excel, save it, and upload again."
)


@dataclass(frozen=True)
class ParsedInvoice:
    invoice_number: str
    customer_name: str
    date_raised: date
    due_date: date
    amount: Decimal
    paid_date: date | None

    @property
    def key(self) -> str:
        return invoice_number_key(self.invoice_number)


def invoice_number_key(invoice_number: str) -> str:
    """Case- and space-insensitive identity: ' inv-1 ' and 'INV-1' are the same invoice."""
    return invoice_number.strip().upper()


def display_date(value: date) -> str:
    return value.strftime("%d %b %Y")


def _is_blank(value: Any) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def display_cell(value: Any) -> str | None:
    """A raw cell value as the user would recognise it (for rejection messages)."""
    if _is_blank(value):
        return None
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    if isinstance(value, datetime):
        return display_date(value.date())
    if isinstance(value, date):
        return display_date(value)
    return str(value).strip()


def parse_invoice_number(value: Any) -> tuple[str | None, str | None]:
    if _is_blank(value):
        return None, f"{INVOICE_NUMBER} is missing."
    if isinstance(value, bool):
        return None, f"{INVOICE_NUMBER} '{value}' is not valid."
    if isinstance(value, float) and value.is_integer():
        text = str(int(value))
    else:
        text = str(value).strip()
    if len(text) > MAX_INVOICE_NUMBER_LENGTH:
        return None, f"{INVOICE_NUMBER} is too long (max {MAX_INVOICE_NUMBER_LENGTH} characters)."
    return text, None


def parse_customer_name(value: Any) -> tuple[str | None, str | None]:
    if _is_blank(value):
        return None, f"{CUSTOMER_NAME} is missing."
    text = " ".join(str(value).split())
    if len(text) > MAX_CUSTOMER_NAME_LENGTH:
        return None, f"{CUSTOMER_NAME} is too long (max {MAX_CUSTOMER_NAME_LENGTH} characters)."
    return text, None


def parse_date(value: Any, column: str, *, required: bool) -> tuple[date | None, str | None]:
    if _is_blank(value):
        return None, (f"{column} is missing." if required else None)
    if isinstance(value, datetime):
        return value.date(), None
    if isinstance(value, date):
        return value, None
    if isinstance(value, int | float) and not isinstance(value, bool):
        if 1 <= value <= MAX_EXCEL_SERIAL:
            return EXCEL_EPOCH + timedelta(days=int(value)), None
        return None, f"{column} '{display_cell(value)}' is not a valid date."
    text = str(value).strip()
    for fmt in TEXT_DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date(), None
        except ValueError:
            continue
    return None, f"{column} '{text}' is not a valid date."


def parse_amount(value: Any) -> tuple[Decimal | None, str | None]:
    if _is_blank(value):
        return None, f"{AMOUNT} is missing."
    if isinstance(value, bool):
        return None, f"{AMOUNT} '{value}' is not a number."
    if isinstance(value, int | float):
        text = str(value)  # shortest round-trip repr: 12500.55 stays 12500.55
    else:
        text = str(value).replace("₹", "").replace(",", "").replace(" ", "").strip()
    try:
        amount = Decimal(text)
    except InvalidOperation:
        return None, f"{AMOUNT} '{str(value).strip()}' is not a number."
    if not amount.is_finite():
        return None, f"{AMOUNT} '{str(value).strip()}' is not a number."
    if amount <= 0:
        return None, f"{AMOUNT} must be greater than zero."
    if amount != amount.quantize(CENT):
        return None, f"{AMOUNT} can have at most 2 decimal places."
    if amount >= MAX_AMOUNT:
        return None, f"{AMOUNT} is too large."
    return amount.quantize(CENT), None


def validate_row(
    values: dict[str, Any], formula_columns: frozenset[str] = frozenset()
) -> ParsedInvoice | list[str]:
    """Returns the parsed invoice, or every problem found in the row."""
    problems: list[str] = [
        FORMULA_PROBLEM.format(column=c) for c in REQUIRED_COLUMNS if c in formula_columns
    ]

    def check(column: str, parsed: tuple[Any, str | None]) -> Any:
        value, problem = parsed
        if column in formula_columns:
            return None  # already reported
        if problem:
            problems.append(problem)
        return value

    number = check(INVOICE_NUMBER, parse_invoice_number(values.get(INVOICE_NUMBER)))
    customer = check(CUSTOMER_NAME, parse_customer_name(values.get(CUSTOMER_NAME)))
    raised = check(DATE_RAISED, parse_date(values.get(DATE_RAISED), DATE_RAISED, required=True))
    due = check(DUE_DATE, parse_date(values.get(DUE_DATE), DUE_DATE, required=True))
    amount = check(AMOUNT, parse_amount(values.get(AMOUNT)))
    paid = check(PAID_DATE, parse_date(values.get(PAID_DATE), PAID_DATE, required=False))

    if raised and due and due < raised:
        problems.append(
            f"{DUE_DATE} ({display_date(due)}) is before {DATE_RAISED} ({display_date(raised)})."
        )
    if raised and paid and paid < raised:
        problems.append(
            f"{PAID_DATE} ({display_date(paid)}) is before {DATE_RAISED} ({display_date(raised)})."
        )

    if problems:
        return problems
    assert number and customer and raised and due and amount  # guaranteed when no problems
    return ParsedInvoice(number, customer, raised, due, amount, paid)
