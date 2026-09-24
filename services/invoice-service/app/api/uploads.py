"""Invoice upload endpoints (INV-001)."""

import asyncio
import tempfile
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, UploadFile
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import UploadPage, UploadSummary
from app.core.errors import AppError
from app.core.logging import get_logger
from app.db import get_session
from app.db.invoice_repo import list_uploads
from app.domain.excel_reader import MAX_UPLOAD_BYTES, file_too_large
from app.domain.template import build_template
from app.domain.upload_service import INVOICE_UPLOADS, process_upload

router = APIRouter(tags=["Invoice uploads"])
log = get_logger("invoice_upload")

XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
_CHUNK = 1024 * 1024


async def _remove(path: Path) -> None:
    await asyncio.to_thread(path.unlink, missing_ok=True)


async def _save_to_temp(upload: UploadFile) -> tuple[Path, int]:
    """Streams the upload to disk, stopping as soon as it passes the size limit (AC2)."""
    size = 0
    too_large = False
    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as handle:
        path = Path(handle.name)
        while chunk := await upload.read(_CHUNK):
            size += len(chunk)
            if size > MAX_UPLOAD_BYTES:
                too_large = True
                break
            handle.write(chunk)
    if too_large:
        await _remove(path)
        raise file_too_large()
    return path, size


@router.post("/uploads", status_code=201, response_model=UploadSummary)
async def upload_invoices(
    request: Request,
    file: UploadFile,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> UploadSummary:
    file_name = (file.filename or "invoices.xlsx")[:255]
    temp_path: Path | None = None
    try:
        temp_path, size_bytes = await _save_to_temp(file)
        log.info(
            "invoice_upload.received",
            message="Invoice file received",
            file_name=file_name,
            size_bytes=size_bytes,
        )
        upload = await process_upload(
            session,
            file_path=temp_path,
            file_name=file_name,
            uploads_dir=Path(request.app.state.settings.uploads_dir),
        )
    except AppError as exc:
        INVOICE_UPLOADS.labels(result="rejected").inc()
        log.warning(
            "invoice_upload.rejected",
            message=f"Invoice file rejected: {exc.code}",
            code=exc.code,
            file_name=file_name,
            missing=exc.details.get("missing"),
        )
        raise
    except Exception:
        INVOICE_UPLOADS.labels(result="error").inc()
        log.error(
            "invoice_upload.failed", message="Invoice upload failed; rolled back", exc_info=True
        )
        raise
    finally:
        if temp_path is not None:
            await _remove(temp_path)
    return UploadSummary.model_validate(upload)


@router.get("/uploads", response_model=UploadPage)
async def get_uploads(
    session: Annotated[AsyncSession, Depends(get_session)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=50)] = 10,
) -> UploadPage:
    items, total = await list_uploads(session, page=page, page_size=page_size)
    return UploadPage(items=items, total=total, page=page, page_size=page_size)


@router.get("/template", response_class=Response)
def download_template() -> Response:
    return Response(
        content=build_template(),
        media_type=XLSX_MEDIA_TYPE,
        headers={"Content-Disposition": 'attachment; filename="invoice-template.xlsx"'},
    )
