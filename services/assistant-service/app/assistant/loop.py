"""The assistant's tool loop (AST-001 design "Claude request" → Loop).

Streams one answer: model text as `text` events, each lookup as `status` running/done events,
and a final `done`. Parallel tool calls from one step run concurrently and go back to the model
in a single message. At most `max_lookups` lookups run per question; after that the model is
told to answer with what it has. Failures raise AssistantError for the caller to report.
"""

import asyncio
import json
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from app.assistant.events import AssistantError, Event, Model, StepResult, ToolCall, Usage
from app.assistant.guard import Intent
from app.assistant.prompt import LIMIT_REACHED_NOTE, build_system
from app.assistant.telemetry import TOOL_CALLS
from app.assistant.tools import TOOL_DEFINITIONS, Lookups, ToolOutcome, lookup_labels
from app.core.logging import get_logger

log = get_logger("assistant")


@dataclass
class ChatStats:
    """What the caller logs when the answer ends. Never contains question or answer text."""

    steps: int = 0
    tools: list[str] = field(default_factory=list)
    usage: Usage = field(default_factory=Usage)
    stop_reason: str | None = None


async def answer(
    *,
    model: Model,
    lookups: Lookups,
    history: list[dict[str, str]],
    today: date,
    timezone: str,
    max_lookups: int,
    stats: ChatStats,
    intent: Intent | None = Intent.DATA,
    invoice_days: int = 5,
    contract_days: int = 3,
) -> AsyncIterator[Event]:
    system = build_system(
        today, timezone, intent=intent, invoice_days=invoice_days, contract_days=contract_days
    )
    # A question about the app is answered from the guide, so no lookups are offered (AST-002).
    tools = [] if intent == Intent.ABOUT_APP else TOOL_DEFINITIONS
    messages: list[dict[str, Any]] = [dict(m) for m in history]
    max_steps = max_lookups + 2  # enough to use every lookup, then answer
    wrote_text = False
    status_ids = 0

    while True:
        if stats.steps >= max_steps:
            raise AssistantError("ASSISTANT_FAILED", f"no answer after {stats.steps} steps")
        stats.steps += 1
        step: StepResult | None = None
        separated = False
        async for item in model.stream_step(system=system, tools=tools, messages=messages):
            if isinstance(item, StepResult):
                step = item
                continue
            if wrote_text and not separated:
                # Text from an earlier step ("Let me check…") gets its own paragraph.
                yield Event("text", {"delta": "\n\n"})
            separated = True
            wrote_text = True
            yield Event("text", {"delta": item})
        if step is None:
            raise AssistantError("ASSISTANT_FAILED", "model step returned no result")
        stats.usage.add(step.usage)
        messages.append({"role": "assistant", "content": step.content})

        if not step.tool_calls:
            if not wrote_text:
                raise AssistantError("ASSISTANT_FAILED", f"empty answer ({step.stop_reason})")
            stats.stop_reason = step.stop_reason
            yield Event("done", {"stop_reason": step.stop_reason})
            return

        allowed = max(0, max_lookups - len(stats.tools))
        to_run, refused = step.tool_calls[:allowed], step.tool_calls[allowed:]
        ids = {}
        for call in to_run:
            status_ids += 1
            ids[call.id] = f"t{status_ids}"
            running, _ = lookup_labels(call.name, call.input)
            yield Event("status", {"id": ids[call.id], "state": "running", "label": running})

        outcomes = await asyncio.gather(*(_run_tool(lookups, call) for call in to_run))
        results: list[dict[str, Any]] = []
        for call, outcome in zip(to_run, outcomes, strict=True):
            stats.tools.append(call.name)
            _, done = lookup_labels(call.name, call.input)
            data: dict[str, Any] = {"id": ids[call.id], "state": "done", "label": done}
            if outcome.is_error:
                data |= {"state": "failed", "label": done.replace("Checked", "Couldn't check", 1)}
                if call.name == "get_contract_details":
                    data["label"] = "Couldn't read the contract"
            else:
                if outcome.done_label:
                    data["label"] = outcome.done_label
                if outcome.count is not None:
                    data["count"] = outcome.count
            yield Event("status", data)
            results.append(_tool_result(call.id, outcome.content, outcome.is_error))
        for call in refused:
            results.append(_tool_result(call.id, {"error": LIMIT_REACHED_NOTE}, True))
        if len(stats.tools) >= max_lookups:
            results.append({"type": "text", "text": LIMIT_REACHED_NOTE})
        messages.append({"role": "user", "content": results})


async def _run_tool(lookups: Lookups, call: ToolCall) -> ToolOutcome:
    start = time.perf_counter()
    outcome = await lookups.run(call.name, call.input)
    ok = not outcome.is_error
    TOOL_CALLS.labels(tool=call.name, ok=str(ok).lower()).inc()
    log.info(
        "assistant_tool.called",
        message=f"Lookup {call.name} {'succeeded' if ok else 'failed'}",
        tool=call.name,
        ok=ok,
        duration_ms=round((time.perf_counter() - start) * 1000),
        results=outcome.count,
        # The failure reason is fixed wording from tools.py, never user or document text.
        **({"reason": outcome.content.get("error")} if not ok else {}),
    )
    return outcome


def _tool_result(tool_use_id: str, content: dict[str, Any], is_error: bool) -> dict[str, Any]:
    return {
        "type": "tool_result",
        "tool_use_id": tool_use_id,
        "content": json.dumps(content, ensure_ascii=False, default=str),
        "is_error": is_error,
    }
