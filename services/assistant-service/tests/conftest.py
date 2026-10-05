import io
import json
import logging
from collections.abc import AsyncIterator, Callable, Iterator
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.assistant.clock import get_today
from app.assistant.events import StepResult, ToolCall, Usage
from app.assistant.guard import GuardDecision, Intent
from app.config import Settings
from app.core.logging import build_formatter
from app.main import create_app

TODAY = date(2026, 9, 25)
LogLines = Callable[[], list[dict[str, Any]]]

BLUEWAVE_ID = "11111111-1111-4111-8111-111111111111"
SHARMA_ID = "22222222-2222-4222-8222-222222222222"


# --- The invoice and contract services, mocked -------------------------------------------------


def _invoice(number, customer, due, amount, status, days, paid=None):
    return {
        "id": f"00000000-0000-4000-8000-{number[-4:]:0>12}",
        "invoice_number": number,
        "customer_name": customer,
        "date_raised": "2026-08-01",
        "due_date": due,
        "amount": amount,
        "paid_date": paid,
        "status": status,
        "days_until_due": days,
        "record_status": "new",
        "record_updated_at": None,
    }


INVOICES = [
    _invoice("INV-2606", "Deccan Printing Works", "2026-08-16", "250000.00", "outstanding", -40),
    _invoice("INV-2611", "Kaveri Textiles", "2026-09-27", "1234567.50", "at_risk", 2),
    _invoice("INV-2620", "Nilgiri Foods", "2026-10-20", "4500.00", "open", 25),
    _invoice("INV-2590", "Bluewave Logistics", "2026-09-01", "80000.00", "paid", None, "2026-09-02"),  # noqa: E501
]
VIEW_STATUSES = {
    "follow_up": {"outstanding", "at_risk"},
    "outstanding": {"outstanding"},
    "at_risk": {"at_risk"},
    "open": {"open"},
    "paid": {"paid"},
    "all": {"outstanding", "at_risk", "open", "paid"},
}


def _contract_item(cid, title, parties, end, lifecycle, reasons, high):
    return {
        "id": cid,
        "title": title,
        "file_name": f"{title}.docx",
        "parties": parties,
        "start_date": "2025-10-01",
        "end_date": end,
        "days_until_end": None if end is None else (date.fromisoformat(end) - TODAY).days,
        "lifecycle": lifecycle,
        "at_risk": bool(reasons),
        "at_risk_reasons": reasons,
        "high_risk_count": high,
        "uploaded_at": "2026-09-20T10:00:00Z",
        "processing_status": "completed",
    }


CONTRACTS = [
    _contract_item(
        BLUEWAVE_ID, "Master Services Agreement", ["Bluewave Logistics", "Our Company"],
        "2026-09-27", "in_force", ["Expires in 2 days", "2 high risks"], 2,
    ),
    _contract_item(
        SHARMA_ID, "Supply Agreement", ["Sharma Traders", "Our Company"],
        "2027-03-31", "in_force", [], 0,
    ),
]
CONTRACT_DETAIL = {
    **CONTRACTS[0],
    "today": TODAY.isoformat(),
    "file_type": "docx",
    "error_message": None,
    "summary": "Logistics services for two years.",
    "parties": [
        {"name": "Bluewave Logistics", "role": "Service provider"},
        {"name": "Our Company", "role": "Customer"},
    ],
    "key_dates": [
        {"label": "End date", "date": "2026-09-27", "days_from_today": 2,
         "source_text": "ends on 27 September 2026", "source_verified": True},
    ],
    "terms": [{"category": "payment", "summary": "Pay within 30 days.",
               "source_text": "within thirty days", "source_verified": True}],
    "risks": [
        {"severity": "high", "title": "Unlimited liability", "description": "No cap on liability.",
         "source_text": "liability shall be unlimited", "source_verified": True},
        {"severity": "high", "title": "Auto-renewal", "description": "Renews unless notice.",
         "source_text": "shall renew automatically", "source_verified": True},
    ],
    "extraction_model": "claude-sonnet-5",
    "processed_at": "2026-09-20T10:01:00Z",
}


@dataclass
class Downstream:
    """In-memory stand-in for invoice-service and contract-service (read-only APIs)."""

    requests: list[httpx.Request] = field(default_factory=list)
    fail: set[str] = field(default_factory=set)  # "invoice" / "contract" → 500
    unreachable: set[str] = field(default_factory=set)  # → connection error

    def handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        service = "invoice" if request.url.host == "invoice-service" else "contract"
        if service in self.unreachable:
            raise httpx.ConnectError("connection refused", request=request)
        if service in self.fail:
            return httpx.Response(500, json={"error": {"code": "INTERNAL_ERROR"}})
        path, params = request.url.path, request.url.params
        if path == "/health":
            return httpx.Response(200, json={"status": "ok"})
        if path == "/api/invoices":
            return httpx.Response(200, json=self._invoice_page(params))
        if path == "/api/invoices/dashboard":
            return httpx.Response(200, json=self._invoice_dashboard())
        if path == "/api/contracts":
            return httpx.Response(200, json=self._contract_page(params))
        if path == "/api/contracts/dashboard":
            return httpx.Response(200, json=self._contract_dashboard())
        if path == f"/api/contracts/{BLUEWAVE_ID}":
            return httpx.Response(200, json=CONTRACT_DETAIL)
        return httpx.Response(404, json={"error": {"code": "NOT_FOUND"}})

    def paths(self) -> list[str]:
        return [f"{r.method} {r.url.path}" for r in self.requests if r.url.path != "/health"]

    @staticmethod
    def _invoice_page(params: httpx.QueryParams) -> dict[str, Any]:
        view = params.get("view", "follow_up")
        q = (params.get("q") or "").lower()
        rows = [
            i for i in INVOICES
            if i["status"] in VIEW_STATUSES[view]
            and (not q or q in i["invoice_number"].lower() or q in i["customer_name"].lower())
            and (not params.get("due_from") or i["due_date"] >= params["due_from"])
            and (not params.get("due_to") or i["due_date"] <= params["due_to"])
        ]
        rows.sort(key=lambda i: i["due_date"], reverse=params.get("order") == "desc")
        size = int(params.get("page_size", 25))
        return {
            "today": TODAY.isoformat(),
            "items": rows[:size],
            "total": len(rows),
            "page": 1,
            "page_size": size,
            "total_amount": str(sum(Decimal(i["amount"]) for i in rows)),
            "counts": {
                view: sum(i["status"] in statuses for i in INVOICES)
                for view, statuses in VIEW_STATUSES.items()
            },
        }

    @staticmethod
    def _invoice_dashboard() -> dict[str, Any]:
        return {
            "today": TODAY.isoformat(),
            "has_data": True,
            "week": {"start": "2026-09-20", "end": "2026-09-26",
                     "anchor_uploaded_at": "2026-09-20T09:00:00Z"},
            "value_this_week": "0.00",
            "invoices_this_week": 0,
            "follow_up": {"total": 2, "outstanding": 1, "at_risk": 1},
            "value_by_status": [
                {"status": "outstanding", "amount": "250000.00", "count": 1},
                {"status": "paid", "amount": "80000.00", "count": 1},
            ],
            "top_follow_up": [INVOICES[0]],
            "links": None,
        }

    @staticmethod
    def _contract_page(params: httpx.QueryParams) -> dict[str, Any]:
        view, q = params.get("view", "all"), (params.get("q") or "").lower()
        rows = [
            c for c in CONTRACTS
            if (view == "all" or (view == "at_risk" and c["at_risk"]) or c["lifecycle"] == view)
            and (not q or q in " ".join([c["title"], *c["parties"]]).lower())
        ]
        return {
            "today": TODAY.isoformat(),
            "items": rows[: int(params.get("page_size", 25))],
            "total": len(rows),
            "page": 1,
            "page_size": int(params.get("page_size", 25)),
            "counts": {},
        }

    @staticmethod
    def _contract_dashboard() -> dict[str, Any]:
        return {
            "today": TODAY.isoformat(),
            "has_data": True,
            "counts": {"total": 2, "in_force": 2, "at_risk": 1, "expired": 0,
                       "not_started": 0, "no_end_date": 0},
            "at_risk_breakdown": {"expiring_soon": 1, "high_risk": 1},
            "needs_attention": [CONTRACTS[0]],
            "unread": {"processing": 0, "failed": 0},
        }


# --- A scripted model ---------------------------------------------------------------------------


Calls = list[tuple[str, dict[str, Any]]]
Step = str | Calls | tuple[str, Calls] | Exception


class ScriptedModel:
    """Plays back fixed steps: text (streamed in two pieces), a list of tool calls, text followed
    by tool calls (a tuple), or an error.

    Records the messages it was given at each step so tests can inspect tool results.
    """

    model = "scripted"

    def __init__(self, *steps: Step) -> None:
        self.steps = list(steps)
        self.seen: list[list[Any]] = []
        self.requests: list[dict[str, Any]] = []  # the system prompt and tools of every step

    async def stream_step(self, *, system, tools, messages) -> AsyncIterator[str | StepResult]:
        self.seen.append(json.loads(json.dumps(messages, default=str)))
        self.requests.append({"system": system, "tools": tools})
        step = self.steps.pop(0) if self.steps else "(script ended)"
        usage = Usage(input_tokens=100, output_tokens=10, cache_read_tokens=50)
        if isinstance(step, Exception):
            raise step
        if isinstance(step, str):
            text, tools = step, []
        elif isinstance(step, tuple):
            text, tools = step
        else:
            text, tools = "", step
        half = len(text) // 2
        for piece in (text[:half], text[half:]):
            if piece:
                yield piece
        blocks: list[dict[str, Any]] = [{"type": "text", "text": text}] if text else []
        if not tools:
            yield StepResult(blocks, "end_turn", usage=usage)
            return
        n = len(self.seen)
        calls = [ToolCall(f"call_{n}_{i}", name, args) for i, (name, args) in enumerate(tools)]
        blocks += [
            {"type": "tool_use", "id": c.id, "name": c.name, "input": c.input} for c in calls
        ]
        yield StepResult(blocks, "tool_use", tool_calls=calls, usage=usage)

    def tool_results(self, step: int) -> list[dict[str, Any]]:
        """The tool results (decoded) sent to the model at the given step (0-based)."""
        blocks = self.seen[step][-1]["content"]
        return [
            {**json.loads(b["content"]), "_is_error": b["is_error"]}
            for b in blocks
            if b.get("type") == "tool_result"
        ]


class ScriptedGuard:
    """Plays back fixed intent decisions (the last one repeats), or fails open on demand.

    `None` stands for "the check was unavailable". Records the history it was shown.
    """

    model = "scripted-guard"

    def __init__(self, *decisions: Intent | None | GuardDecision) -> None:
        self.decisions = list(decisions) or [Intent.DATA]
        self.seen: list[list[dict[str, str]]] = []

    async def classify(self, history: list[dict[str, str]]) -> GuardDecision:
        self.seen.append([dict(m) for m in history])
        item = self.decisions.pop(0) if len(self.decisions) > 1 else self.decisions[0]
        if isinstance(item, GuardDecision):
            return item
        usage = Usage(input_tokens=40, output_tokens=5)
        if item is None:
            return GuardDecision(None, "fallback", 7, reason="TimeoutError")
        return GuardDecision(item, "classifier", 7, usage)


# --- Fixtures ------------------------------------------------------------------------------------


@pytest.fixture
def settings() -> Settings:
    return Settings(
        _env_file=None,
        assistant_llm="fake",
        anthropic_api_key="",
        fake_word_delay=0,
        log_level="INFO",
    )


@pytest.fixture
def downstream() -> Downstream:
    return Downstream()


@pytest.fixture
def app(settings: Settings, downstream: Downstream) -> FastAPI:
    app = create_app(settings, transport=httpx.MockTransport(downstream.handle))
    app.dependency_overrides[get_today] = lambda: TODAY
    # Everything is "about the business" unless a test installs another guard (AST-002).
    app.state.guard = ScriptedGuard(Intent.DATA)
    return app


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def use_model(app: FastAPI) -> Callable[..., ScriptedModel]:
    def install(*steps: Step) -> ScriptedModel:
        model = ScriptedModel(*steps)
        app.state.model = model
        return model

    return install


@pytest.fixture
def use_guard(app: FastAPI) -> Callable[..., ScriptedGuard]:
    def install(*decisions: Intent | None | GuardDecision) -> ScriptedGuard:
        guard = ScriptedGuard(*decisions)
        app.state.guard = guard
        return guard

    return install


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


Events = list[tuple[str, dict[str, Any]]]


def parse_sse(body: str) -> Events:
    events = []
    for chunk in body.strip().split("\n\n"):
        lines = dict(line.split(": ", 1) for line in chunk.splitlines())
        events.append((lines["event"], json.loads(lines["data"])))
    return events


@pytest.fixture
def ask(client: TestClient) -> Callable[..., Events]:
    """Asks a question (or sends a whole history) and returns the parsed events."""

    def send(question: str | list[dict[str, str]], **headers: str) -> Events:
        messages = question if isinstance(question, list) else [
            {"role": "user", "content": question}
        ]
        response = client.post(
            "/api/assistant/chat", json={"messages": messages}, headers=headers
        )
        assert response.status_code == 200, response.text
        assert response.headers["content-type"].startswith("text/event-stream")
        return parse_sse(response.text)

    return send


def answer_text(events: Events) -> str:
    return "".join(data["delta"] for kind, data in events if kind == "text")
