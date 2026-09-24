"""In-file duplicate resolution (INV-001 AC6a): the last valid row for an invoice number wins."""

from dataclasses import dataclass, field

from app.domain.invoice_rules import ParsedInvoice


@dataclass(frozen=True)
class Overwrite:
    row: int
    replaced_row: int
    invoice_number: str


@dataclass
class ResolvedRows:
    # invoice_number_key → (invoice, row number), in first-seen order
    invoices: dict[str, tuple[ParsedInvoice, int]] = field(default_factory=dict)
    overwrites: list[Overwrite] = field(default_factory=list)
    overwritten_keys: set[str] = field(default_factory=set)


def resolve_duplicates(valid_rows: list[tuple[int, ParsedInvoice]]) -> ResolvedRows:
    """Rows must be in file order. Invalid rows are never passed in, so they never overwrite."""
    resolved = ResolvedRows()
    for row_number, invoice in valid_rows:
        previous = resolved.invoices.get(invoice.key)
        if previous is not None:
            resolved.overwrites.append(Overwrite(row_number, previous[1], invoice.invoice_number))
            resolved.overwritten_keys.add(invoice.key)
        resolved.invoices[invoice.key] = (invoice, row_number)
    return resolved
