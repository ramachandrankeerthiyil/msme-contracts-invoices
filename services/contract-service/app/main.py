import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import api_routers
from app.config import Settings, get_settings
from app.core import health, metrics
from app.core.access_log import AccessLogMiddleware
from app.core.errors import UnhandledErrorMiddleware, register_error_handlers
from app.core.health import ReadyCheck
from app.core.logging import configure_logging, get_logger
from app.core.metrics import MetricsMiddleware
from app.core.request_context import RequestContextMiddleware
from app.db import create_engine, create_sessionmaker
from app.domain.pipeline import ContractPipeline
from app.extraction.base import Extractor
from app.extraction.claude import ClaudeExtractor
from app.extraction.fake import FakeExtractor

log = get_logger("app")

SHUTDOWN_GRACE_SECONDS = 30


async def check_llm_configured(app: FastAPI) -> bool:
    """Contract extraction needs the Claude API key (PLT-002 AC6). No network call is made."""
    settings = app.state.settings
    return settings.contract_extractor == "fake" or bool(
        settings.anthropic_api_key.get_secret_value()
    )


def build_extractor(settings: Settings) -> Extractor:
    if settings.contract_extractor == "fake":
        return FakeExtractor()
    return ClaudeExtractor(
        api_key=settings.anthropic_api_key.get_secret_value(),
        model=settings.contract_llm_model,
        effort=settings.contract_llm_effort,
    )


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.service_name, settings.log_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        engine = create_engine(settings)
        app.state.engine = engine
        app.state.sessionmaker = create_sessionmaker(engine)
        pipeline = ContractPipeline(
            app.state.sessionmaker, build_extractor(settings), settings.contract_max_concurrent
        )
        app.state.pipeline = pipeline
        try:
            interrupted = await pipeline.mark_interrupted()
            if interrupted:
                log.warning(
                    "contract_extraction.interrupted",
                    message="Contracts left mid-reading were marked as failed",
                    contracts=interrupted,
                )
        except Exception as exc:  # the DB may not be up yet; /ready reports it
            log.warning(
                "db.startup_check_failed",
                message="Could not check for interrupted work",
                error=f"{type(exc).__name__}: {exc}",
            )
        log.info(
            "app.started",
            message=f"{settings.service_name} {settings.service_version} started",
            version=settings.service_version,
            log_level=settings.log_level,
            extractor=settings.contract_extractor,
            model=settings.contract_llm_model,
        )
        yield
        try:
            await asyncio.wait_for(pipeline.wait_idle(), SHUTDOWN_GRACE_SECONDS)
        except TimeoutError:
            log.warning(
                "app.shutdown_timeout", message="Contract reading still running at shutdown"
            )
        await engine.dispose()

    app = FastAPI(
        title="Contract Service",
        version=settings.service_version,
        lifespan=lifespan,
        docs_url=f"{settings.api_prefix}/docs",
        openapi_url=f"{settings.api_prefix}/openapi.json",
        redoc_url=None,
    )
    app.state.settings = settings
    ready_checks: dict[str, ReadyCheck] = {"llm_api_key": check_llm_configured}
    app.state.ready_checks = ready_checks

    register_error_handlers(app)
    app.include_router(health.router)
    app.include_router(metrics.router)
    for router in api_routers:
        app.include_router(router, prefix=settings.api_prefix)

    # Added innermost first: the last one added wraps all the others.
    app.add_middleware(UnhandledErrorMiddleware)
    app.add_middleware(MetricsMiddleware)
    app.add_middleware(AccessLogMiddleware)
    app.add_middleware(RequestContextMiddleware)

    return app
