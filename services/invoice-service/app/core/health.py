"""Liveness and readiness endpoints (PLT-002 AC6)."""

import asyncio
from collections.abc import Awaitable, Callable

from fastapi import APIRouter, FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.logging import get_logger

log = get_logger("health")

DB_CHECK_TIMEOUT_SECONDS = 2.0

# A readiness check returns True when healthy. Services may register extra checks.
ReadyCheck = Callable[[FastAPI], Awaitable[bool]]

router = APIRouter(include_in_schema=False)


async def check_database(app: FastAPI) -> bool:
    engine: AsyncEngine = app.state.engine
    try:
        async with asyncio.timeout(DB_CHECK_TIMEOUT_SECONDS), engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception as exc:  # any failure means "not ready"
        log.warning(
            "db.ready_check_failed",
            message="Database readiness check failed",
            error=f"{type(exc).__name__}: {exc}",
        )
        return False


@router.get("/health")
def health(request: Request) -> dict[str, str]:
    settings = request.app.state.settings
    return {"status": "ok", "service": settings.service_name, "version": settings.service_version}


@router.get("/ready")
async def ready(request: Request) -> JSONResponse:
    app = request.app
    # Services without a database (assistant-service) have no engine and skip that check.
    database = {"database": check_database} if getattr(app.state, "engine", None) else {}
    checks: dict[str, ReadyCheck] = {**database, **app.state.ready_checks}
    results = {name: "ok" if await check(app) else "fail" for name, check in checks.items()}
    is_ready = all(result == "ok" for result in results.values())
    return JSONResponse(
        status_code=200 if is_ready else 503,
        content={"status": "ready" if is_ready else "not_ready", "checks": results},
    )
