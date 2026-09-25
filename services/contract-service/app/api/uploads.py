"""Contract upload and retry (CON-001)."""

import asyncio
import shutil
import tempfile
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, Request, UploadFile
from prometheus_client import Counter
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import ContractId, contract_not_found
from app.api.schemas import UploadAccepted
from app.core.errors import AppError
from app.core.logging import get_logger
from app.core.metrics import REGISTRY
from app.db import get_session
from app.db.models import Contract
from app.domain.clock import display_date, local_date
from app.domain.file_types import (
    MAX_UPLOAD_BYTES,
    detect_file_type,
    file_too_large,
    sha256_of,
)

router = APIRouter(tags=["Contract uploads"])
log = get_logger("contract_upload")

UPLOADS = Counter(
    "contract_uploads_total", "Contract uploads by result", ["result"], registry=REGISTRY
)
Session = Annotated[AsyncSession, Depends(get_session)]
_CHUNK = 1024 * 1024


async def _remove(path: Path) -> None:
    await asyncio.to_thread(path.unlink, missing_ok=True)


async def _save_to_temp(upload: UploadFile) -> tuple[Path, int]:
    """Streams the upload to disk, stopping as soon as it passes the size limit (AC3)."""
    size = 0
    too_large = False
    with tempfile.NamedTemporaryFile(delete=False) as handle:
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


def _store(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)


def _duplicate(existing: Contract, time_zone: str) -> AppError:
    uploaded = display_date(local_date(existing.uploaded_at, time_zone))
    return AppError(
        "DUPLICATE_CONTRACT",
        f"This contract was already uploaded on {uploaded}.",
        status=409,
        details={"contract_id": str(existing.id), "uploaded_at": existing.uploaded_at.isoformat()},
    )


@router.post("/uploads", status_code=202, response_model=UploadAccepted)
async def upload_contract(request: Request, file: UploadFile, session: Session) -> UploadAccepted:
    settings = request.app.state.settings
    file_name = (file.filename or "contract")[:255]
    temp_path: Path | None = None
    try:
        temp_path, size = await _save_to_temp(file)
        file_type = await asyncio.to_thread(detect_file_type, temp_path)
        log.info(
            "contract_upload.received",
            message="Contract file received",
            file_type=file_type,
            size_bytes=size,
        )
        sha = await asyncio.to_thread(sha256_of, temp_path)
        existing = await session.scalar(select(Contract).where(Contract.file_sha256 == sha))
        if existing is not None:
            raise _duplicate(existing, settings.app_timezone)

        contract_id = uuid.uuid4()
        stored = Path(settings.uploads_dir) / f"{contract_id}.{file_type}"
        await asyncio.to_thread(_store, temp_path, stored)
        session.add(
            Contract(
                id=contract_id,
                file_name=file_name,
                file_type=file_type,
                file_size=size,
                file_sha256=sha,
                stored_path=str(stored),
                uploaded_at=datetime.now(UTC),
                processing_status="uploaded",
            )
        )
        try:
            await session.commit()
        except IntegrityError:  # the same file uploaded twice at the same moment
            await session.rollback()
            await _remove(stored)
            existing = await session.scalar(select(Contract).where(Contract.file_sha256 == sha))
            if existing is None:
                raise
            raise _duplicate(existing, settings.app_timezone) from None
    except AppError as exc:
        result = "duplicate" if exc.code == "DUPLICATE_CONTRACT" else "rejected"
        UPLOADS.labels(result=result).inc()
        log.warning(
            "contract_upload.rejected",
            message=f"Contract upload not accepted: {exc.code}",
            code=exc.code,
        )
        raise
    finally:
        if temp_path is not None:
            await _remove(temp_path)

    request.app.state.pipeline.schedule(contract_id, getattr(request.state, "request_id", None))
    UPLOADS.labels(result="accepted").inc()
    return UploadAccepted(id=contract_id, processing_status="uploaded")


@router.post("/{contract_id}/retry", status_code=202, response_model=UploadAccepted)
async def retry_contract(
    request: Request, contract_id: ContractId, session: Session
) -> UploadAccepted:
    contract = await session.get(Contract, contract_id)
    if contract is None:
        raise contract_not_found()
    if contract.processing_status != "failed":
        raise AppError(
            "NOT_RETRYABLE", "This contract is not waiting to be tried again.", status=409
        )
    contract.processing_status = "uploaded"
    contract.error_code = None
    contract.error_message = None
    contract.processing_started_at = None
    contract.processing_finished_at = None
    await session.commit()
    request.app.state.pipeline.schedule(contract_id, getattr(request.state, "request_id", None))
    return UploadAccepted(id=contract_id, processing_status="uploaded")
