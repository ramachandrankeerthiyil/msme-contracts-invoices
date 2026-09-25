"""Background reading of an uploaded contract (CON-001 design "Overview").

uploaded → extracting_text → analysing → completed | failed. Runs as an asyncio task in the
service process (at most `contract_max_concurrent` at a time). Logs carry the originating
request_id and the contract_id, never document text or extracted content (PLT-002 AC5).
"""

import asyncio
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path

import structlog
from prometheus_client import Counter, Histogram
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.logging import get_logger
from app.core.metrics import REGISTRY
from app.db.models import (
    IN_PROGRESS,
    Contract,
    ContractKeyDate,
    ContractParty,
    ContractRisk,
    ContractTerm,
)
from app.domain.text_extraction import TextExtractionError, extract_text
from app.extraction.base import ExtractionFailed, ExtractionResult, Extractor
from app.extraction.quotes import QuoteChecker

log = get_logger("contract_pipeline")

EXTRACTIONS = Counter(
    "contract_extractions_total", "Contract extractions by result", ["result"], registry=REGISTRY
)
EXTRACTION_SECONDS = Histogram(
    "contract_extraction_duration_seconds",
    "Time to read one contract (text + AI)",
    ["model"],
    registry=REGISTRY,
    buckets=(1, 5, 10, 20, 30, 45, 60, 90, 120, 180, 300),
)
LLM_TOKENS = Counter(
    "llm_tokens_total", "Claude tokens used", ["model", "direction"], registry=REGISTRY
)

INTERRUPTED_MESSAGE = "Reading was interrupted. Please try again."
MAX_ATTEMPTS = 2  # one automatic retry (AC7)


def _now() -> datetime:
    return datetime.now(UTC)


class ContractPipeline:
    def __init__(
        self,
        sessionmaker: async_sessionmaker[AsyncSession],
        extractor: Extractor,
        max_concurrent: int = 2,
    ) -> None:
        self._sessionmaker = sessionmaker
        self._extractor = extractor
        self._slots = asyncio.Semaphore(max_concurrent)
        self._tasks: set[asyncio.Task[None]] = set()

    # --- scheduling -----------------------------------------------------------------------

    def schedule(self, contract_id: uuid.UUID, request_id: str | None) -> None:
        task = asyncio.create_task(self.run(contract_id, request_id))
        self._tasks.add(task)  # keep a reference until done
        task.add_done_callback(self._tasks.discard)

    async def wait_idle(self) -> None:
        """Waits for scheduled work (tests, shutdown)."""
        while self._tasks:
            await asyncio.gather(*list(self._tasks), return_exceptions=True)

    async def mark_interrupted(self) -> int:
        """At startup nothing is running yet, so any in-progress contract was interrupted."""
        async with self._sessionmaker() as session, session.begin():
            result = await session.execute(
                update(Contract)
                .where(Contract.processing_status.in_(IN_PROGRESS))
                .values(
                    processing_status="failed",
                    error_code="INTERRUPTED",
                    error_message=INTERRUPTED_MESSAGE,
                    processing_finished_at=_now(),
                    updated_at=_now(),
                )
            )
        return result.rowcount or 0

    # --- the job --------------------------------------------------------------------------

    async def run(self, contract_id: uuid.UUID, request_id: str | None = None) -> None:
        structlog.contextvars.bind_contextvars(request_id=request_id, contract_id=str(contract_id))
        async with self._slots:
            try:
                await self._run(contract_id)
            except Exception:
                log.error(
                    "contract_extraction.failed",
                    message="Unexpected error while reading a contract",
                    error_code="INTERNAL",
                    exc_info=True,
                )
                EXTRACTIONS.labels(result="failed").inc()
                await self._fail(contract_id, "INTERNAL", INTERRUPTED_MESSAGE)

    async def _run(self, contract_id: uuid.UUID) -> None:
        started = time.perf_counter()
        async with self._sessionmaker() as session:
            contract = await session.get(Contract, contract_id)
            if contract is None:
                return
            file_path, file_type, file_name = (
                Path(contract.stored_path),
                contract.file_type,
                contract.file_name,
            )
        await self._set(
            contract_id, processing_status="extracting_text", processing_started_at=_now()
        )

        try:
            extracted = await asyncio.to_thread(extract_text, file_path, file_type)  # type: ignore[arg-type]
        except TextExtractionError as exc:
            log.warning(
                "contract_extraction.failed",
                message="No usable text in document",
                error_code=exc.code,
                attempt=0,
            )
            EXTRACTIONS.labels(result="failed").inc()
            await self._fail(contract_id, exc.code, exc.message)
            return

        await self._set(
            contract_id,
            processing_status="analysing",
            page_count=extracted.pages,
            text_chars=len(extracted.text),
        )

        result: ExtractionResult | None = None
        failure: ExtractionFailed | None = None
        for attempt in range(1, MAX_ATTEMPTS + 1):
            log.info(
                "contract_extraction.started",
                message="Reading contract with AI",
                attempt=attempt,
                model=self._extractor.model,
            )
            try:
                result = await self._extractor.extract(extracted.text, file_name)
                break
            except ExtractionFailed as exc:
                failure = exc
                log.warning(
                    "contract_extraction.failed",
                    message="AI extraction attempt failed",
                    error_code=exc.code,
                    attempt=attempt,
                    reason=exc.reason,
                )
                if not exc.retryable:
                    break

        if result is None:
            assert failure is not None
            EXTRACTIONS.labels(result="failed").inc()
            await self._fail(contract_id, failure.code, failure.user_message)
            return

        unverified = await self._save(contract_id, result, QuoteChecker(extracted.text))
        duration = time.perf_counter() - started
        EXTRACTIONS.labels(result="completed").inc()
        EXTRACTION_SECONDS.labels(model=result.model).observe(duration)
        for direction, tokens in (
            ("input", result.input_tokens),
            ("output", result.output_tokens),
            ("cache_read", result.cache_read_tokens),
            ("cache_write", result.cache_write_tokens),
        ):
            LLM_TOKENS.labels(model=result.model, direction=direction).inc(tokens)
        data = result.data
        log.info(
            "contract_extraction.completed",
            message="Contract read",
            duration_ms=round(duration * 1000),
            model=result.model,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            cache_read_tokens=result.cache_read_tokens,
            pages=extracted.pages,
            parties=len(data.parties),
            key_dates=len(data.key_dates),
            terms=len(data.terms),
            risks=len(data.risks),
            unverified_quotes=unverified,
        )

    # --- persistence ----------------------------------------------------------------------

    async def _set(self, contract_id: uuid.UUID, **values: object) -> None:
        async with self._sessionmaker() as session, session.begin():
            await session.execute(
                update(Contract)
                .where(Contract.id == contract_id)
                .values(**values, updated_at=_now())
            )

    async def _fail(self, contract_id: uuid.UUID, code: str, message: str) -> None:
        await self._set(
            contract_id,
            processing_status="failed",
            error_code=code,
            error_message=message,
            processing_finished_at=_now(),
        )

    async def _save(
        self, contract_id: uuid.UUID, result: ExtractionResult, quotes: QuoteChecker
    ) -> int:
        """Replaces any earlier results in one transaction (AC5). Returns unverified quotes."""
        data = result.data
        unverified = 0

        def verified(quote: str) -> bool:
            nonlocal unverified
            ok = quotes.verified(quote)
            unverified += not ok
            return ok

        async with self._sessionmaker() as session, session.begin():
            # Lock the contract row; it may have been removed while the AI was reading it.
            still_there = await session.scalar(
                select(Contract.id).where(Contract.id == contract_id).with_for_update()
            )
            if still_there is None:
                log.info(
                    "contract_extraction.discarded",
                    message="Contract was removed while being read; result discarded",
                )
                return 0
            for table in (ContractParty, ContractKeyDate, ContractTerm, ContractRisk):
                await session.execute(delete(table).where(table.contract_id == contract_id))
            session.add_all(
                [
                    ContractParty(contract_id=contract_id, position=i, name=p.name, role=p.role)
                    for i, p in enumerate(data.parties)
                ]
                + [
                    ContractKeyDate(
                        contract_id=contract_id,
                        position=i,
                        label=k.label,
                        date=k.date,
                        source_text=k.source_text,
                        source_verified=verified(k.source_text),
                    )
                    for i, k in enumerate(sorted(data.key_dates, key=lambda k: k.date))
                ]
                + [
                    ContractTerm(
                        contract_id=contract_id,
                        position=i,
                        category=t.category,
                        summary=t.summary,
                        source_text=t.source_text,
                        source_verified=verified(t.source_text),
                    )
                    for i, t in enumerate(data.terms)
                ]
                + [
                    ContractRisk(
                        contract_id=contract_id,
                        position=i,
                        severity=r.severity,
                        title=r.title,
                        description=r.description,
                        source_text=r.source_text,
                        source_verified=verified(r.source_text),
                    )
                    for i, r in enumerate(data.risks)
                ]
            )
            await session.execute(
                update(Contract)
                .where(Contract.id == contract_id)
                .values(
                    processing_status="completed",
                    error_code=None,
                    error_message=None,
                    processing_finished_at=_now(),
                    title=data.title,
                    summary=data.summary,
                    start_date=data.start_date,
                    end_date=data.end_date,
                    extraction_model=result.model,
                    raw_extraction=data.model_dump(mode="json"),
                    input_tokens=result.input_tokens,
                    output_tokens=result.output_tokens,
                    cache_read_tokens=result.cache_read_tokens,
                    updated_at=_now(),
                )
            )
        return unverified
