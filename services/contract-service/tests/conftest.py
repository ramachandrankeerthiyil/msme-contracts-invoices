import asyncio
import io
import json
import logging
import os
from collections.abc import Callable, Iterator
from typing import Any

import pytest

# Tests always run against the separate test database created by db/init/01-schemas.sh.
# This must happen before app.config is imported (get_settings is cached).
_base_db = os.environ.get("POSTGRES_DB", "msme")
os.environ["POSTGRES_DB"] = _base_db if _base_db.endswith("_test") else f"{_base_db}_test"

from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from pydantic import SecretStr  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import create_async_engine  # noqa: E402

from app.config import Settings, get_settings  # noqa: E402
from app.core.errors import AppError  # noqa: E402
from app.core.logging import build_formatter  # noqa: E402
from app.main import create_app  # noqa: E402

LogLines = Callable[[], list[dict[str, Any]]]


async def _execute(settings: Settings, *statements: str) -> None:
    engine = create_async_engine(settings.database_url)
    async with engine.begin() as conn:
        for statement in statements:
            await conn.execute(text(statement))
    await engine.dispose()


@pytest.fixture(scope="session")
def settings() -> Settings:
    # A dummy key so readiness passes; tests never call the real Claude API.
    return get_settings().model_copy(update={"anthropic_api_key": SecretStr("test-key")})


@pytest.fixture(scope="session", autouse=True)
def database(settings: Settings) -> Iterator[None]:
    """A fresh copy of the service schema for this test run, dropped afterwards."""
    schema = settings.db_schema
    asyncio.run(
        _execute(settings, f'DROP SCHEMA IF EXISTS "{schema}" CASCADE', f'CREATE SCHEMA "{schema}"')
    )
    command.upgrade(Config("alembic.ini"), "head")
    yield
    asyncio.run(_execute(settings, f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))


def _add_probe_routes(app: FastAPI) -> None:
    """Routes that exist only in tests, to exercise error handling and route labels."""
    prefix = app.state.settings.api_prefix

    @app.get(f"{prefix}/_test/boom")
    def boom() -> None:
        raise RuntimeError("probe failure")

    @app.get(f"{prefix}/_test/app-error")
    def app_error() -> None:
        raise AppError("DEMO_ERROR", "A friendly message.", status=409, details={"hint": "x"})

    @app.get(f"{prefix}/_test/items/{{item_id}}")
    def item(item_id: int) -> dict[str, int]:
        return {"item_id": item_id}


@pytest.fixture
def app(settings: Settings) -> FastAPI:
    app = create_app(settings)
    _add_probe_routes(app)
    return app


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def logs(app: FastAPI, settings: Settings) -> Iterator[LogLines]:
    """Captures JSON log lines emitted during the test (depends on `app`, which resets logging)."""
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(build_formatter(settings.service_name))
    root = logging.getLogger()
    root.addHandler(handler)

    def lines() -> list[dict[str, Any]]:
        return [json.loads(line) for line in stream.getvalue().splitlines() if line.strip()]

    yield lines
    root.removeHandler(handler)
