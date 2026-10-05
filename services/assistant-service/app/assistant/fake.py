"""Deterministic stand-in for Claude (ASSISTANT_LLM=fake), used by e2e tests and demos.

Routes the question by keywords, calls the same real lookups Claude would, and writes an
answer from their results, word by word with a small delay so Stop can be exercised. It never
calls the Claude API.
"""

import asyncio
import json
import re
from collections.abc import AsyncIterator
from datetime import date
from typing import Any

from app.assistant.app_guide import APP_SUMMARY
from app.assistant.events import StepResult, ToolCall

FAKE_MODEL = "fake"
_WRITE_WORDS = ("mark", "change", "delete", "update", "edit", "remove", "send", "email")


class FakeModel:
    model = FAKE_MODEL

    def __init__(self, word_delay: float = 0.03) -> None:
        self._delay = word_delay

    async def stream_step(
        self, *, system: list[dict[str, Any]], tools: list[dict[str, Any]], messages: list[Any]
    ) -> AsyncIterator[str | StepResult]:
        question, calls, results = _current_turn(messages)
        if _classified_as_about_app(system):
            plan = _about_app_answer()
        else:
            plan = _plan(question.lower(), calls, results)
        if isinstance(plan, tuple):
            name, tool_input = plan
            call = ToolCall(id=f"fake_{len(calls) + 1}", name=name, input=tool_input)
            block = {"type": "tool_use", "id": call.id, "name": name, "input": tool_input}
            yield StepResult(content=[block], stop_reason="tool_use", tool_calls=[call])
            return
        for word in re.split(r"(?<=\s)", plan):
            await asyncio.sleep(self._delay)
            yield word
        yield StepResult(content=[{"type": "text", "text": plan}], stop_reason="end_turn")


def _classified_as_about_app(system: list[dict[str, Any]]) -> bool:
    """The guard's hint in the system prompt (AST-002): the question is about the app."""
    return any("classified as being about the app" in block.get("text", "") for block in system)


def _about_app_answer() -> str:
    return (
        f"{APP_SUMMARY}\n\nTo get started, [upload a contract](/contracts/upload) or "
        "[upload your invoices](/invoices/upload)."
    )


def _current_turn(messages: list[Any]) -> tuple[str, list[dict], dict[str, dict]]:
    """The latest question, the lookups made for it so far, and their results by call id."""
    start = max(
        i for i, m in enumerate(messages) if m["role"] == "user" and isinstance(m["content"], str)
    )
    calls, results = [], {}
    for message in messages[start + 1 :]:
        for block in message["content"]:
            if isinstance(block, dict) and block.get("type") == "tool_use":
                calls.append(block)
            elif isinstance(block, dict) and block.get("type") == "tool_result":
                results[block["tool_use_id"]] = json.loads(block["content"]) | {
                    "_is_error": block.get("is_error", False)
                }
    return messages[start]["content"], calls, results


def _plan(q: str, calls: list[dict], results: dict[str, dict]) -> tuple[str, dict] | str:
    """Next lookup as (tool, input), or the final answer text."""
    last = results[calls[-1]["id"]] if calls else None
    if last and last["_is_error"]:
        return "Sorry, I couldn't check that right now. Please try again in a moment."

    if any(word in q.split() for word in _WRITE_WORDS):
        return (
            "I can only look things up, so I can't change anything. To record a payment, "
            "upload an updated invoice spreadsheet on the [Upload invoices](/invoices/upload) page."
        )

    if "contract" in q or ("risk" in q and "invoice" not in q):
        if not calls:
            if "risk" in q or "summar" in q or "about" in q:
                return "search_contracts", _contract_search()
            return "get_contract_overview", {}
        if calls[-1]["name"] == "search_contracts":
            match = _pick_contract(q, last["contracts"])
            if match is None:
                return "I couldn't find any contracts yet. Upload one on the Contracts page."
            return "get_contract_details", {"contract_id": match["id"]}
        if calls[-1]["name"] == "get_contract_details":
            return _contract_answer(last)
        return _contract_overview_answer(last)

    if any(word in q for word in ("invoice", "unpaid", "owe", "due", "paid", "customer")):
        if not calls:
            view = "paid" if "paid" in q and "unpaid" not in q else "unpaid"
            if "overdue" in q or "outstanding" in q:
                view = "outstanding"
            return "search_invoices", _invoice_search(view)
        return _invoice_answer(last)

    return (
        "I can help with questions about your contracts and invoices, for example "
        "“Which invoices are unpaid as of today?” or “What risks are in my contracts?”"
    )


def _contract_search() -> dict[str, Any]:
    return {"view": "all", "search": None, "sort": "high_risks", "order": "desc", "limit": 25}


def _invoice_search(view: str) -> dict[str, Any]:
    return {
        "view": view, "search": None, "due_from": None, "due_to": None,
        "sort": "due_date", "order": "asc", "limit": 50,
    }


def _pick_contract(q: str, contracts: list[dict]) -> dict | None:
    words = set(re.findall(r"[a-z]{4,}", q)) - {"contract", "risks", "what", "summarise", "about"}
    for contract in contracts:
        text = " ".join([contract["title"], *contract["parties"]]).lower()
        if any(word in text for word in words):
            return contract
    return contracts[0] if contracts else None


def _day(value: str | None) -> str:
    if not value:
        return "no date"
    d = date.fromisoformat(value)
    return f"{d.day} {d.strftime('%b %Y')}"


def _due_note(days: int | None) -> str:
    if days is None:
        return ""
    if days < 0:
        return f" ({-days} day{'s' if days != -1 else ''} overdue)"
    if days == 0:
        return " (due today)"
    return f" (due in {days} day{'s' if days != 1 else ''})"


def _invoice_answer(result: dict) -> str:
    if result["total"] == 0:
        return "I couldn't find any invoices like that."
    lines = [
        f"You have **{result['total']} invoices** worth **{result['total_amount']}**:",
        "",
        "| Invoice | Customer | Due | Amount | Status |",
        "|---|---|---|---|---|",
    ]
    for inv in result["invoices"]:
        due = _day(inv["due_date"]) + ("" if inv["paid_date"] else _due_note(inv["days_until_due"]))
        lines.append(
            f"| [{inv['invoice_number']}]({inv['link']}) | {inv['customer']} | {due} | "
            f"{inv['amount']} | {inv['status']} |"
        )
    if result["showing"] < result["total"]:
        lines += ["", f"Showing the first {result['showing']}."]
    return "\n".join(lines)


def _contract_answer(c: dict) -> str:
    if c.get("note"):
        return f"[{c['title']}]({c['link']}): {c['note']}"
    lines = [f"**[{c['title']}]({c['link']})** — {c['status']}, ends {_day(c['end_date'])}."]
    if c["risks"]:
        lines += ["", f"It has **{len(c['risks'])} risks**:", ""]
        lines += [f"- **{r['severity'].title()}:** {r['title']}" for r in c["risks"]]
    else:
        lines += ["", "No risks were found in this contract."]
    lines += ["", "This is not legal advice; check important points with an adviser."]
    return "\n".join(lines)


def _contract_overview_answer(o: dict) -> str:
    if not o["has_data"]:
        return "You haven't uploaded any contracts yet."
    counts = o["counts"]
    lines = [
        f"You have **{counts['total']} contracts**: {counts['in_force']} in force and "
        f"{counts['at_risk']} at risk."
    ]
    for c in o["needs_attention"]:
        lines.append(f"- [{c['title']}]({c['link']}): {', '.join(c['at_risk_reasons'])}")
    return "\n".join(lines)
