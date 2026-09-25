"""Opt-in live check against the real Claude API (CON-001, "Live" row of the test plan).

Costs a few rupees per run, so it is skipped unless explicitly requested:

    docker compose run --rm -e RUN_LLM_TESTS=1 -v "$PWD/samples:/samples:ro" \
        contract-service pytest -m llm -s

The samples are regenerated relative to today by scripts/make_samples.py.
"""

import asyncio
import os
from datetime import date, timedelta
from pathlib import Path

import pytest

from app.config import get_settings
from app.domain.text_extraction import extract_text
from app.extraction.claude import ClaudeExtractor
from app.extraction.quotes import QuoteChecker

pytestmark = [
    pytest.mark.llm,
    pytest.mark.skipif(
        os.environ.get("RUN_LLM_TESTS") != "1" or not os.environ.get("ANTHROPIC_API_KEY"),
        reason="live AI test: set RUN_LLM_TESTS=1 and ANTHROPIC_API_KEY",
    ),
]

SAMPLES = Path(os.environ.get("SAMPLES_DIR", "/samples"))


def _extract(name: str):
    settings = get_settings()
    extractor = ClaudeExtractor(
        settings.anthropic_api_key.get_secret_value(),
        settings.contract_llm_model,
        settings.contract_llm_effort,
    )
    text = extract_text(SAMPLES / name, "docx").text
    result = asyncio.run(extractor.extract(text, name))
    checker = QuoteChecker(text)
    quotes = [item.source_text for item in (*result.data.risks, *result.data.terms)]
    verified = sum(checker.verified(q) for q in quotes)
    print(
        f"\n{name}: model={result.model} in={result.input_tokens} out={result.output_tokens} "
        f"cache_read={result.cache_read_tokens} parties={len(result.data.parties)} "
        f"risks={[r.severity for r in result.data.risks]} "
        f"start={result.data.start_date} end={result.data.end_date} "
        f"quotes verified={verified}/{len(quotes)}"
    )
    return result, verified, len(quotes)


def test_live_msa_is_expiring_and_high_risk():
    result, verified, total = _extract("contract-msa-bluewave.docx")
    data = result.data

    names = " ".join(p.name for p in data.parties)
    assert "Kaveri" in names and "Bluewave" in names
    assert data.end_date is not None
    assert abs((data.end_date - (date.today() + timedelta(days=2))).days) <= 1
    assert any(r.severity == "high" for r in data.risks)
    assert verified >= total * 0.8  # nearly all quotes are verbatim


def test_live_supply_agreement_is_in_force_with_no_high_risk_expected():
    result, verified, total = _extract("contract-supply-sharma.docx")
    data = result.data

    assert data.start_date is not None and data.start_date <= date.today()
    assert data.end_date is not None and data.end_date > date.today() + timedelta(days=30)
    assert len(data.parties) == 2
    assert verified >= total * 0.8
