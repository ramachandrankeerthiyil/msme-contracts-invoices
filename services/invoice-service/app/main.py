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

log = get_logger("app")


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.service_name, settings.log_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        engine = create_engine(settings)
        app.state.engine = engine
        app.state.sessionmaker = create_sessionmaker(engine)
        log.info(
            "app.started",
            message=f"{settings.service_name} {settings.service_version} started",
            version=settings.service_version,
            log_level=settings.log_level,
        )
        yield
        await engine.dispose()

    app = FastAPI(
        title="Invoice Service",
        version=settings.service_version,
        lifespan=lifespan,
        docs_url=f"{settings.api_prefix}/docs",
        openapi_url=f"{settings.api_prefix}/openapi.json",
        redoc_url=None,
    )
    app.state.settings = settings
    ready_checks: dict[str, ReadyCheck] = {}
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
