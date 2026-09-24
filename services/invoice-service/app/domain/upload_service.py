"""Invoice upload orchestration: read → validate → dedupe → persist → log/metrics (INV-001)."""

import asyncio
import shutil
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path

from prometheus_client import Counter
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.metrics import REGISTRY
from app.db.invoice_repo import upsert_invoices
from app.db.models import InvoiceUpload
from app.domain.duplicates import resolve_duplicates
from app.domain.excel_reader import RawRow, check_file_type, read_rows
from app.domain.invoice_rules import INVOICE_NUMBER, ParsedInvoice, display_cell, validate_row

log = get_logger("invoice_upload")

INVOICE_UPLOADS = Counter(
    "invoice_uploads_total", "Invoice uploads by result", ["result"], registry=REGISTRY
)
INVOICE_ROWS = Counter(
    "invoice_rows_total", "Invoice rows processed by outcome", ["outcome"], registry=REGISTRY
)


def _read_workbook(file_path: Path) -> list[RawRow]:
    check_file_type(file_path)
    return read_rows(file_path)


def _store_file(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)


async def process_upload(
    session: AsyncSession, *, file_path: Path, file_name: str, uploads_dir: Path
) -> InvoiceUpload:
    """Everything is saved in one transaction, or nothing is (AC12)."""
    started = time.perf_counter()
    # Parsing and file I/O are blocking; keep them off the event loop.
    raw_rows = await asyncio.to_thread(_read_workbook, file_path)

    valid: list[tuple[int, ParsedInvoice]] = []
    rejections: list[dict[str, object]] = []
    for raw in raw_rows:
        result = validate_row(raw.values, raw.formula_columns)
        if isinstance(result, ParsedInvoice):
            valid.append((raw.row_number, result))
        else:
            rejections.append(
                {
                    "row": raw.row_number,
                    "invoice_number": display_cell(raw.values.get(INVOICE_NUMBER)),
                    "reason": " ".join(result),
                }
            )
    resolved = resolve_duplicates(valid)

    upload_id = uuid.uuid4()
    now = datetime.now(UTC)
    stored_path = uploads_dir / f"{upload_id}.xlsx"
    upload = InvoiceUpload(
        id=upload_id,
        file_name=file_name,
        uploaded_at=now,
        status="completed" if resolved.invoices else "no_valid_rows",
        rows_total=len(raw_rows),
        rows_created=0,
        rows_updated=0,
        rows_overwritten=len(resolved.overwrites),
        rows_rejected=len(rejections),
        rejections=rejections,
        overwrites=[
            {"row": o.row, "replaced_row": o.replaced_row, "invoice_number": o.invoice_number}
            for o in resolved.overwrites
        ],
    )

    try:
        async with session.begin():
            session.add(upload)
            await session.flush()
            if resolved.invoices:
                upload.rows_created, upload.rows_updated = await upsert_invoices(
                    session, upload_id=upload_id, now=now, resolved=resolved
                )
            await asyncio.to_thread(_store_file, file_path, stored_path)
            upload.stored_path = str(stored_path)
    except Exception:
        await asyncio.to_thread(stored_path.unlink, missing_ok=True)
        raise

    for outcome, count in (
        ("created", upload.rows_created),
        ("updated", upload.rows_updated),
        ("overwritten", upload.rows_overwritten),
        ("rejected", upload.rows_rejected),
    ):
        INVOICE_ROWS.labels(outcome=outcome).inc(count)
    INVOICE_UPLOADS.labels(result="success").inc()
    log.info(
        "invoice_upload.completed",
        message="Invoice upload processed",
        upload_id=str(upload_id),
        status=upload.status,
        rows_total=upload.rows_total,
        rows_created=upload.rows_created,
        rows_updated=upload.rows_updated,
        rows_overwritten=upload.rows_overwritten,
        rows_rejected=upload.rows_rejected,
        duration_ms=round((time.perf_counter() - started) * 1000, 1),
    )
    return upload
