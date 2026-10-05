"""POST /api/assistant/chat: one streamed answer as Server-Sent Events (AST-001 design "API")."""

import asyncio
import time
from collections.abc import AsyncIterator
from contextlib import aclosing
from datetime import date
from typing import Annotated, Literal

import anyio
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field, field_validator, model_validator
from starlette.responses import StreamingResponse
from starlette.types import Receive, Scope, Send

from app.assistant.clock import get_today
from app.assistant.events import AssistantError, Event, Usage
from app.assistant.guard import DECLINED, GuardDecision
from app.assistant.loop import ChatStats, answer
from app.assistant.refusals import reply_for
from app.assistant.telemetry import CHATS, FIRST_TEXT_SECONDS, GUARD, LLM_TOKENS
from app.assistant.tools import Lookups
from app.core.logging import get_logger

router = APIRouter(tags=["Assistant"])
log = get_logger("assistant")

MAX_MESSAGES = 20
MAX_USER_CHARS = 1_000
MAX_ASSISTANT_CHARS = 8_000


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1)

    @field_validator("content")
    @classmethod
    def not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value

    @model_validator(mode="after")
    def within_length(self) -> "ChatMessage":
        limit = MAX_USER_CHARS if self.role == "user" else MAX_ASSISTANT_CHARS
        if len(self.content) > limit:
            raise ValueError(f"{self.role} messages can be at most {limit:,} characters")
        return self


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(min_length=1, max_length=MAX_MESSAGES)

    @model_validator(mode="after")
    def alternating_roles(self) -> "ChatRequest":
        for index, message in enumerate(self.messages):
            expected = "user" if index % 2 == 0 else "assistant"
            if message.role != expected:
                raise ValueError("messages must alternate, starting with the user")
        if self.messages[-1].role != "user":
            raise ValueError("the last message must be the user's question")
        return self


class EventStreamResponse(StreamingResponse):
    """SSE response that stops producing as soon as the browser disconnects (Stop, AC4).

    The producer and a disconnect watcher share a task group; whichever finishes first cancels
    the other. The event generator is then closed (shielded, so cleanup can finish), which
    closes the Claude stream behind it: no tokens are spent on an answer nobody reads.
    """

    media_type = "text/event-stream"

    def __init__(self, chunks: AsyncIterator[str]) -> None:
        super().__init__(chunks, headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
        self._chunks = chunks

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        async with anyio.create_task_group() as group:

            async def produce() -> None:
                try:
                    await send(
                        {
                            "type": "http.response.start",
                            "status": self.status_code,
                            "headers": self.raw_headers,
                        }
                    )
                    async for chunk in self._chunks:
                        await send(
                            {
                                "type": "http.response.body",
                                "body": chunk.encode(),
                                "more_body": True,
                            }
                        )
                    await send({"type": "http.response.body", "body": b"", "more_body": False})
                finally:
                    with anyio.CancelScope(shield=True):
                        await self._chunks.aclose()  # type: ignore[attr-defined]
                group.cancel_scope.cancel()

            async def watch_disconnect() -> None:
                while (await receive())["type"] != "http.disconnect":
                    pass
                group.cancel_scope.cancel()

            group.start_soon(produce)
            group.start_soon(watch_disconnect)


async def _guard(request: Request, history: list[dict[str, str]]) -> GuardDecision:
    """The intent check (AST-002). Never raises; logs and counts the decision, not the text."""
    guard = request.app.state.guard
    decision = await guard.classify(history)
    label = decision.intent.value if decision.intent else "unknown"
    GUARD.labels(intent=label).inc()
    _count_usage(guard.model, decision.usage)
    if decision.intent is None:
        log.warning(
            "assistant_guard.unavailable",
            message="Intent check unavailable; the question goes to the assistant's own rules",
            reason=decision.reason,
            duration_ms=decision.duration_ms,
        )
    log.info(
        "assistant_guard.decision",
        message=f"Question classified as {label}",
        intent=label,
        source=decision.source,
        model=guard.model,
        input_tokens=decision.usage.input_tokens,
        output_tokens=decision.usage.output_tokens,
        duration_ms=decision.duration_ms,
    )
    return decision


async def _events(
    request: Request, history: list[dict[str, str]], today: date
) -> AsyncIterator[str]:
    """Runs the loop and reports its outcome: logs, metrics and a final error event if needed."""
    app = request.app
    settings = app.state.settings
    model = app.state.model
    request_id = request.state.request_id
    stats = ChatStats()
    started = time.perf_counter()
    first_text_ms: int | None = None
    lookups = Lookups(
        app.state.http, settings.invoice_api_url, settings.contract_api_url, request_id
    )
    log.info(
        "assistant_chat.started",
        message="Question received",
        turns=len(history),
        question_chars=len(history[-1]["content"]),
    )
    try:
        decision = await _guard(request, history)
        if decision.intent in DECLINED:
            # A fixed reply: the question reaches neither the main model nor any lookup.
            first_text_ms = round((time.perf_counter() - started) * 1000)
            FIRST_TEXT_SECONDS.observe(first_text_ms / 1000)
            yield Event("text", {"delta": reply_for(decision.intent)}).sse()
            yield Event("done", {"stop_reason": "declined"}).sse()
            CHATS.labels(result="declined").inc()
            log.info(
                "assistant_chat.declined",
                message="Question declined as out of scope",
                intent=decision.intent.value,
                duration_ms=first_text_ms,
            )
            return
        events = answer(
            model=model,
            lookups=lookups,
            history=history,
            today=today,
            timezone=settings.app_timezone,
            max_lookups=settings.max_lookups,
            stats=stats,
            intent=decision.intent,
            invoice_days=settings.invoice_at_risk_days,
            contract_days=settings.contract_at_risk_days,
        )
        async with aclosing(events):
            async for event in events:
                if event.type == "text" and first_text_ms is None:
                    first_text_ms = round((time.perf_counter() - started) * 1000)
                    FIRST_TEXT_SECONDS.observe(first_text_ms / 1000)
                yield event.sse()
    except (asyncio.CancelledError, GeneratorExit):
        # Cancelled mid-lookup (CancelledError) or between events (GeneratorExit on close).
        CHATS.labels(result="cancelled").inc()
        log.info(
            "assistant_chat.cancelled",
            message="Answer stopped before it finished",
            steps=stats.steps,
            duration_ms=round((time.perf_counter() - started) * 1000),
        )
        _count_tokens(model.model, stats)
        raise
    except Exception as exc:
        error = exc if isinstance(exc, AssistantError) else None
        CHATS.labels(result="failed").inc()
        log.error(
            "assistant_chat.failed",
            message="Could not answer the question",
            code=error.code if error else "ASSISTANT_FAILED",
            reason=error.reason if error else f"{type(exc).__name__}",
            steps=stats.steps,
            exc_info=error is None,
        )
        _count_tokens(model.model, stats)
        failure = error or AssistantError("ASSISTANT_FAILED", type(exc).__name__)
        yield Event(
            "error",
            {"code": failure.code, "message": failure.user_message, "request_id": request_id},
        ).sse()
        return

    CHATS.labels(result="completed").inc()
    _count_tokens(model.model, stats)
    log.info(
        "assistant_chat.completed",
        message="Answer completed",
        model=model.model,
        intent=decision.intent.value if decision.intent else "unknown",
        steps=stats.steps,
        tools=stats.tools,
        input_tokens=stats.usage.input_tokens,
        output_tokens=stats.usage.output_tokens,
        cache_read_tokens=stats.usage.cache_read_tokens,
        cache_write_tokens=stats.usage.cache_write_tokens,
        duration_ms=round((time.perf_counter() - started) * 1000),
        first_text_ms=first_text_ms,
        stop_reason=stats.stop_reason,
    )


def _count_tokens(model: str, stats: ChatStats) -> None:
    _count_usage(model, stats.usage)


def _count_usage(model: str, usage: Usage) -> None:
    for direction, tokens in (
        ("input", usage.input_tokens),
        ("output", usage.output_tokens),
        ("cache_read", usage.cache_read_tokens),
        ("cache_write", usage.cache_write_tokens),
    ):
        if tokens:
            LLM_TOKENS.labels(model=model, direction=direction).inc(tokens)


@router.post(
    "/chat",
    response_class=EventStreamResponse,
    responses={200: {"content": {"text/event-stream": {}}, "description": "Answer events"}},
)
async def chat(
    request: Request, body: ChatRequest, today: Annotated[date, Depends(get_today)]
) -> EventStreamResponse:
    history = [{"role": m.role, "content": m.content} for m in body.messages]
    return EventStreamResponse(_events(request, history, today))
