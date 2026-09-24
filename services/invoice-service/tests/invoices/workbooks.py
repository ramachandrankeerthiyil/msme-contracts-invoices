"""Builds test workbooks in memory, so no binary fixtures live in the repo."""

from datetime import date
from io import BytesIO
from typing import Any

from openpyxl import Workbook

HEADERS = ["Invoice Number", "Customer Name", "Date Raised", "Due Date", "Amount", "Paid Date"]
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def row(
    number: Any = "INV-1",
    customer: Any = "Acme Traders",
    raised: Any = date(2026, 9, 1),
    due: Any = date(2026, 10, 1),
    amount: Any = 1000,
    paid: Any = None,
) -> list[Any]:
    return [number, customer, raised, due, amount, paid]


def workbook_bytes(rows: list[list[Any]], headers: list[Any] | None = None) -> bytes:
    book = Workbook()
    sheet = book.active
    sheet.append(HEADERS if headers is None else headers)
    for values in rows:
        sheet.append(values)
    buffer = BytesIO()
    book.save(buffer)
    return buffer.getvalue()


def upload(client: Any, content: bytes, name: str = "invoices.xlsx", **kwargs: Any) -> Any:
    return client.post("/api/invoices/uploads", files={"file": (name, content, XLSX)}, **kwargs)
