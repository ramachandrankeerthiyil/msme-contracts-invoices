import asyncio
from collections.abc import Callable, Iterator
from datetime import date
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.config import Settings
from app.domain.clock import get_today
from app.extraction.base import ExtractionFailed, ExtractionResult
from app.extraction.schema import ContractExtraction
from app.main import create_app
from tests.conftest import _execute
from tests.contracts.documents import DOCX

TODAY = date(2026, 9, 25)


class ScriptedExtractor:
    """Returns a prepared result (or failure) per file name; counts calls."""

    model = "scripted"

    def __init__(self) -> None:
        self.script: dict[str, list[Any]] = {}
        self.calls: list[str] = []

    def on(self, file_name: str, *outcomes: Any) -> None:
        self.script[file_name] = list(outcomes)

    async def extract(self, contract_text: str, file_name: str) -> ExtractionResult:
        self.calls.append(file_name)
        outcomes = self.script.get(file_name) or [ExtractionFailed("no script for file")]
        outcome = outcomes.pop(0) if len(outcomes) > 1 else outcomes[0]
        if isinstance(outcome, Exception):
            raise outcome
        if isinstance(outcome, ContractExtraction):
            return ExtractionResult(
                data=outcome,
                model=self.model,
                input_tokens=1200,
                output_tokens=800,
                cache_read_tokens=300,
            )
        return outcome


@pytest.fixture
def clean_contracts(settings: Settings) -> None:
    asyncio.run(_execute(settings, f'TRUNCATE "{settings.db_schema}".contracts CASCADE'))


@pytest.fixture
def uploads_dir(tmp_path: Path) -> Path:
    return tmp_path / "uploads"


@pytest.fixture
def extractor() -> ScriptedExtractor:
    return ScriptedExtractor()


@pytest.fixture
def api(
    settings: Settings, uploads_dir: Path, clean_contracts: None, extractor: ScriptedExtractor
) -> Iterator[TestClient]:
    """Client with empty contract tables, a pinned today and a scripted extractor."""
    app = create_app(settings.model_copy(update={"uploads_dir": str(uploads_dir)}))
    app.dependency_overrides[get_today] = lambda: TODAY
    with TestClient(app) as client:
        app.state.pipeline._extractor = extractor
        yield client


def upload(
    client: TestClient, content: bytes, name: str = "contract.docx", mime: str = DOCX
) -> Any:
    return client.post("/api/contracts/uploads", files={"file": (name, content, mime)})


def wait_for_pipeline(client: TestClient) -> None:
    client.portal.call(client.app.state.pipeline.wait_idle)  # type: ignore[union-attr]


def detail(client: TestClient, contract_id: str) -> dict[str, Any]:
    response = client.get(f"/api/contracts/{contract_id}")
    assert response.status_code == 200, response.text
    return response.json()


async def _fetch(settings: Settings, statement: str) -> list[dict[str, Any]]:
    engine = create_async_engine(
        settings.database_url, connect_args={"server_settings": {"search_path": settings.db_schema}}
    )
    async with engine.connect() as conn:
        rows = [dict(row._mapping) for row in await conn.execute(text(statement))]
    await engine.dispose()
    return rows


@pytest.fixture
def db_rows(settings: Settings) -> Callable[[str], list[dict[str, Any]]]:
    return lambda statement: asyncio.run(_fetch(settings, statement))
