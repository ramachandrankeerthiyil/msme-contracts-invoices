from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI

from app.api import api_routers
from app.assistant.claude import ClaudeModel
from app.assistant.events import Model
from app.assistant.fake import FakeModel
from app.config import Settings, get_settings
from app.core import health, metrics
from app.core.access_log import AccessLogMiddleware
from app.core.errors import UnhandledErrorMiddleware, register_error_handlers
from app.core.health import ReadyCheck
from app.core.logging import configure_logging, get_logger
from app.core.metrics import MetricsMiddleware
from app.core.request_context import RequestContextMiddleware

log = get_logger("app")

HEALTH_TIMEOUT_SECONDS = 2.0


def build_model(settings: Settings) -> Model:
    if settings.assistant_llm == "fake":
        return FakeModel(word_delay=settings.fake_word_delay)
    return ClaudeModel(
        api_key=settings.anthropic_api_key.get_secret_value(),
        model=settings.assistant_llm_model,
        effort=settings.assistant_llm_effort,
    )


def _service_check(name: str, url: str) -> ReadyCheck:
    async def check(app: FastAPI) -> bool:
        try:
            response = await app.state.http.get(
                f"{url.rstrip('/')}/health", timeout=HEALTH_TIMEOUT_SECONDS
            )
            return response.status_code == 200
        except httpx.HTTPError as exc:
            log.warning(
                "downstream.ready_check_failed",
                message=f"{name} is not reachable",
                service=name,
                error=type(exc).__name__,
            )
            return False

    return check


async def _ai_key_check(app: FastAPI) -> bool:
    return bool(app.state.settings.anthropic_api_key.get_secret_value())


def create_app(
    settings: Settings | None = None, transport: httpx.AsyncBaseTransport | None = None
) -> FastAPI:
    """`transport` lets tests replace the invoice and contract services with a mock."""
    settings = settings or get_settings()
    configure_logging(settings.service_name, settings.log_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.http = httpx.AsyncClient(
            transport=transport, timeout=settings.lookup_timeout_seconds
        )
        log.info(
            "app.started",
            message=f"{settings.service_name} {settings.service_version} started",
            version=settings.service_version,
            log_level=settings.log_level,
            assistant_llm=settings.assistant_llm,
            model=app.state.model.model,
        )
        yield
        await app.state.http.aclose()

    app = FastAPI(
        title="Assistant Service",
        version=settings.service_version,
        lifespan=lifespan,
        docs_url=f"{settings.api_prefix}/docs",
        openapi_url=f"{settings.api_prefix}/openapi.json",
        redoc_url=None,
    )
    app.state.settings = settings
    app.state.model = build_model(settings)
    ready_checks: dict[str, ReadyCheck] = {
        "invoice_service": _service_check("invoice-service", settings.invoice_api_url),
        "contract_service": _service_check("contract-service", settings.contract_api_url),
    }
    if settings.assistant_llm == "claude":
        ready_checks["ai_key"] = _ai_key_check
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
