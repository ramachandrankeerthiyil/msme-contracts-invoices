"""Opt-in live eval against the real Claude API and the running stack (AST-001 design "Testing").

Costs a few rupees per run, so it is skipped unless explicitly requested. Load the demo data
first (scripts/make_samples.py + upload), then:

    docker compose run --rm -e RUN_LLM_TESTS=1 assistant-service pytest -m llm -s

Answers are checked on facts, not wording. The expected facts are read from the invoice and
contract APIs at test time, so the eval follows whatever data is loaded.
"""

import os
import re
import time
from datetime import date
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

from app.assistant.tools import format_inr
from app.config import get_settings
from app.main import create_app
from tests.conftest import answer_text, parse_sse

pytestmark = [
    pytest.mark.llm,
    pytest.mark.skipif(
        os.environ.get("RUN_LLM_TESTS") != "1" or not os.environ.get("ANTHROPIC_API_KEY"),
        reason="live AI test: set RUN_LLM_TESTS=1 and ANTHROPIC_API_KEY",
    ),
]

LINK = re.compile(r"\]\(([^)]+)\)")
timings: list[tuple[str, float, float]] = []


@pytest.fixture(scope="module")
def live() -> Any:
    settings = get_settings()
    assert settings.assistant_llm == "claude", "the live eval must use the real model"
    with TestClient(create_app(settings)) as client:
        yield client


@pytest.fixture(scope="module")
def data() -> dict[str, Any]:
    """Facts from the real services, to check answers against."""
    s = get_settings()

    def get(url: str, **params: Any) -> Any:
        response = httpx.get(url, params=params, timeout=10)
        response.raise_for_status()
        return response.json()

    def invoices(view: str) -> list[dict[str, Any]]:
        return get(f"{s.invoice_api_url}/api/invoices", view=view, page_size=100)["items"]

    unpaid = invoices("follow_up") + invoices("open")
    contracts = get(f"{s.contract_api_url}/api/contracts", view="all", page_size=100)["items"]
    assert unpaid and contracts, "load the demo data before running the live eval"
    return {
        "unpaid": unpaid,
        "outstanding": invoices("outstanding"),
        "dashboard": get(f"{s.invoice_api_url}/api/invoices/dashboard"),
        "contracts": contracts,
    }


def ask(client: TestClient, messages: list[dict[str, str]] | str) -> str:
    if isinstance(messages, str):
        messages = [{"role": "user", "content": messages}]
    started = time.perf_counter()
    first_text = None
    events = []
    with client.stream("POST", "/api/assistant/chat", json={"messages": messages}) as response:
        assert response.status_code == 200
        body = ""
        for chunk in response.iter_text():
            if first_text is None and "event: text" in chunk:
                first_text = time.perf_counter() - started
            body += chunk
    events = parse_sse(body)
    total = time.perf_counter() - started
    assert events[-1][0] == "done", events[-1]
    text = answer_text(events)
    question = messages[-1]["content"]
    timings.append((question, first_text or total, total))
    print(f"\n--- Q: {question}\n{text}\n(first text {first_text or 0:.1f}s, total {total:.1f}s)")
    # AC7: every link is an in-app link to a record.
    for link in LINK.findall(text):
        assert link.startswith(("/invoices", "/contracts")), link
    # AC15
    assert (first_text or total) < 10 and total < 60
    return text


def _contract(data: dict[str, Any], word: str) -> dict[str, Any]:
    word = word.lower()
    return next(
        c for c in data["contracts"]
        if word in " ".join([c["title"], c["file_name"], *c["parties"]]).lower()
    )


def test_unpaid_as_of_today_lists_every_unpaid_invoice(live, data):
    text = ask(live, "Which invoices are unpaid as of today?")

    for invoice in data["unpaid"]:
        assert invoice["invoice_number"] in text
    total = sum(float(i["amount"]) for i in data["unpaid"])
    assert format_inr(f"{total:.2f}") in text


def test_overdue_invoices(live, data):
    text = ask(live, "Which invoices are overdue?")

    for invoice in data["outstanding"]:
        assert invoice["invoice_number"] in text
    assert f"/invoices?view=all&q={data['outstanding'][0]['invoice_number']}" in text


def test_biggest_unpaid_invoice(live, data):
    biggest = max(data["unpaid"], key=lambda i: float(i["amount"]))

    text = ask(live, "Which unpaid invoice is the biggest?")

    assert biggest["invoice_number"] in text
    assert format_inr(biggest["amount"]) in text


def test_follow_up_question_uses_the_conversation(live, data):
    biggest = max(data["unpaid"], key=lambda i: float(i["amount"]))
    first = ask(live, "Which invoices are unpaid as of today?")

    text = ask(
        live,
        [
            {"role": "user", "content": "Which invoices are unpaid as of today?"},
            {"role": "assistant", "content": first},
            {"role": "user", "content": "Which of those is the biggest, and who owes it?"},
        ],
    )

    assert biggest["invoice_number"] in text
    assert biggest["customer_name"].split()[0] in text


def test_due_this_week(live, data):
    dashboard = data["dashboard"]

    text = ask(live, "What is due this week?")

    assert format_inr(dashboard["value_this_week"]) in text


def test_contract_risks(live, data):
    msa = _contract(data, "bluewave")

    text = ask(live, "What risks are in the Bluewave contract?")

    assert f"/contracts/{msa['id']}" in text
    assert "high" in text.lower()
    assert "legal" in text.lower() or "lawyer" in text.lower() or "adviser" in text.lower()


def test_contract_summary(live, data):
    supply = _contract(data, "sharma")

    text = ask(live, "Summarise the Sharma supply agreement")

    assert f"/contracts/{supply['id']}" in text


def test_contracts_ending_this_month(live, data):
    today = date.today()
    ending = [
        c for c in data["contracts"]
        if c["end_date"] and date.fromisoformat(c["end_date"]).strftime("%Y-%m")
        == today.strftime("%Y-%m")
    ]

    text = ask(live, "Which contracts end this month?")

    for contract in ending:
        assert f"/contracts/{contract['id']}" in text


def test_AST_001_AC10_refuses_to_change_data(live, data):
    number = data["outstanding"][0]["invoice_number"]

    text = ask(live, f"Mark {number} as paid")

    assert re.search(r"can(?:no|')t|unable|not able|only (?:look|read|view)", text, re.I)
    s = get_settings()
    still = httpx.get(
        f"{s.invoice_api_url}/api/invoices", params={"view": "all", "q": number}, timeout=10
    ).json()["items"][0]
    assert still["paid_date"] is None


def test_AST_001_AC10_declines_unrelated_questions(live):
    text = ask(live, "What is the capital of France?")

    assert "Paris" not in text
    assert "invoice" in text.lower() or "contract" in text.lower()


def test_zz_timing_summary():
    if timings:
        first = sorted(t[1] for t in timings)
        total = sorted(t[2] for t in timings)
        print(
            f"\nAC15 timing over {len(timings)} answers: first text median "
            f"{first[len(first) // 2]:.1f}s (max {first[-1]:.1f}s); total median "
            f"{total[len(total) // 2]:.1f}s (max {total[-1]:.1f}s)"
        )
