from datetime import date, datetime
from decimal import Decimal

import pytest

from app.domain.duplicates import resolve_duplicates
from app.domain.invoice_rules import (
    ParsedInvoice,
    invoice_number_key,
    parse_amount,
    parse_customer_email,
    parse_date,
    parse_invoice_number,
    validate_row,
)


def values(**overrides):
    base = {
        "Invoice Number": "INV-1",
        "Customer Name": "Acme Traders",
        "Date Raised": date(2026, 9, 1),
        "Due Date": date(2026, 10, 1),
        "Amount": 1000,
        "Paid Date": None,
    }
    base.update(overrides)
    return base


# --- AC4: field parsing -------------------------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("INV-1", "INV-1"),
        ("  INV-2  ", "INV-2"),
        (1001.0, "1001"),
        (1001, "1001"),
        ("A" * 50, "A" * 50),
    ],
)
def test_INV_001_AC4_invoice_number_accepts(raw, expected):
    assert parse_invoice_number(raw) == (expected, None)


@pytest.mark.parametrize(
    ("raw", "problem"),
    [
        (None, "Invoice Number is missing."),
        ("   ", "Invoice Number is missing."),
        ("A" * 51, "Invoice Number is too long (max 50 characters)."),
    ],
)
def test_INV_001_AC4_invoice_number_rejects(raw, problem):
    assert parse_invoice_number(raw) == (None, problem)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (datetime(2026, 9, 5, 0, 0), date(2026, 9, 5)),
        (date(2026, 9, 5), date(2026, 9, 5)),
        (46270, date(2026, 9, 5)),  # Excel serial number
        ("2026-09-05", date(2026, 9, 5)),
        ("05-09-2026", date(2026, 9, 5)),
        ("05/09/2026", date(2026, 9, 5)),  # day first
        ("05-Sep-2026", date(2026, 9, 5)),
        ("5 Sep 2026", date(2026, 9, 5)),
    ],
)
def test_INV_001_AC4_dates_accept_excel_and_day_first_text(raw, expected):
    assert parse_date(raw, "Due Date", required=True) == (expected, None)


@pytest.mark.parametrize("raw", ["31/13/2026", "2026/09/05x", "tomorrow", -5])
def test_INV_001_AC4_dates_reject_invalid(raw):
    value, problem = parse_date(raw, "Due Date", required=True)
    assert value is None
    assert (
        problem is not None
        and problem.startswith("Due Date '")
        and "is not a valid date" in problem
    )


def test_INV_001_AC7_blank_paid_date_is_allowed():
    assert parse_date(None, "Paid Date", required=False) == (None, None)
    assert parse_date("", "Paid Date", required=False) == (None, None)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (1000, Decimal("1000.00")),
        (12500.55, Decimal("12500.55")),
        ("1,25,000.50", Decimal("125000.50")),
        ("₹ 4,25,000", Decimal("425000.00")),
        ("12500.500", Decimal("12500.50")),
    ],
)
def test_INV_001_AC4_amount_accepts(raw, expected):
    assert parse_amount(raw) == (expected, None)


@pytest.mark.parametrize(
    ("raw", "problem"),
    [
        (None, "Amount is missing."),
        (0, "Amount must be greater than zero."),
        (-1500, "Amount must be greater than zero."),
        (12500.555, "Amount can have at most 2 decimal places."),
        ("abc", "Amount 'abc' is not a number."),
        (1e12, "Amount is too large."),
        (True, "Amount 'True' is not a number."),
    ],
)
def test_INV_001_AC4_amount_rejects(raw, problem):
    assert parse_amount(raw) == (None, problem)


# --- AC13: Customer Email ------------------------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (None, None),
        ("", None),
        ("   ", None),
        ("accounts@acme.in", "accounts@acme.in"),
        ("  Accounts@Acme.IN  ", "accounts@acme.in"),
        ("first.last+tag@sub.example.co.in", "first.last+tag@sub.example.co.in"),
    ],
)
def test_INV_001_AC13_email_accepts(raw, expected):
    assert parse_customer_email(raw) == (expected, None)


@pytest.mark.parametrize(
    "raw",
    [
        "accounts",
        "accounts@",
        "@acme.in",
        "accounts@acme",
        "no spaces@acme.in",
        "a@b@acme.in",
        "a@acme..in",
        "a@acme.in,b@acme.in",
        "a@acme.in;b@acme.in",
        "<a@acme.in>",
        "x" * 250 + "@acme.in",
    ],
)
def test_INV_001_AC13_email_rejects(raw):
    value, problem = parse_customer_email(raw)

    assert value is None
    assert problem == f"Customer Email '{raw.strip()}' is not a valid email address."


def test_INV_001_AC13_the_row_carries_the_email_and_blank_means_none():
    with_email = validate_row(values(**{"Customer Email": " Billing@Acme.in "}))
    without = validate_row(values())

    assert with_email.customer_email == "billing@acme.in"
    assert without.customer_email is None


# --- AC4: whole-row validation ------------------------------------------------------------


def test_INV_001_AC4_valid_row_is_parsed():
    result = validate_row(values(**{"Paid Date": date(2026, 9, 20)}))

    assert result == ParsedInvoice(
        "INV-1",
        "Acme Traders",
        date(2026, 9, 1),
        date(2026, 10, 1),
        Decimal("1000.00"),
        date(2026, 9, 20),
    )


def test_INV_001_AC4_cross_field_rules():
    result = validate_row(values(**{"Due Date": date(2026, 8, 1), "Paid Date": date(2026, 8, 15)}))

    assert result == [
        "Due Date (01 Aug 2026) is before Date Raised (01 Sep 2026).",
        "Paid Date (15 Aug 2026) is before Date Raised (01 Sep 2026).",
    ]


def test_INV_001_AC4_all_problems_in_a_row_are_reported_together():
    result = validate_row(values(**{"Customer Name": None, "Amount": -1}))

    assert result == ["Customer Name is missing.", "Amount must be greater than zero."]


def test_INV_001_AC4_formula_without_saved_value_is_explained():
    result = validate_row(values(Amount=None), frozenset({"Amount"}))

    assert result == [
        "Amount contains a formula with no saved value. "
        "Open the file in Excel, save it, and upload again."
    ]


def test_INV_001_invoice_number_key_ignores_case_and_spaces():
    assert invoice_number_key(" inv-1 ") == invoice_number_key("INV-1") == "INV-1"


# --- AC6a: in-file duplicates -------------------------------------------------------------


def _invoice(number: str, amount: str) -> ParsedInvoice:
    return ParsedInvoice(number, "Acme", date(2026, 9, 1), date(2026, 10, 1), Decimal(amount), None)


def test_INV_001_AC6a_last_row_wins_and_overwrites_are_recorded():
    resolved = resolve_duplicates(
        [
            (2, _invoice("INV-1", "100")),
            (3, _invoice("INV-2", "200")),
            (7, _invoice("inv-1 ", "150")),
        ]
    )

    assert list(resolved.invoices) == ["INV-1", "INV-2"]
    assert resolved.invoices["INV-1"] == (_invoice("inv-1 ", "150"), 7)
    assert [(o.row, o.replaced_row) for o in resolved.overwrites] == [(7, 2)]
    assert resolved.overwritten_keys == {"INV-1"}


def test_INV_001_AC6a_chains_of_duplicates_record_each_replacement():
    resolved = resolve_duplicates(
        [(2, _invoice("INV-1", "1")), (3, _invoice("INV-1", "2")), (4, _invoice("INV-1", "3"))]
    )

    assert resolved.invoices["INV-1"][1] == 4
    assert [(o.row, o.replaced_row) for o in resolved.overwrites] == [(3, 2), (4, 3)]
