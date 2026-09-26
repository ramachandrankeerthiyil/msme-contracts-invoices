"""The assistant's read-only lookups (AST-001 design "Tools").

Each tool is a strict JSON schema for Claude plus an async executor that calls the invoice or
contract API over the internal network. Executors trim the API response to what the model
needs, add ready-made app links and display amounts, and never raise: any failure becomes an
error result the model can explain (AC5, AC7). Only GET requests are made (AC10).
"""

import asyncio
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any
from urllib.parse import urlencode

import httpx

from app.core.request_context import REQUEST_ID_HEADER

# --- Presentation helpers -------------------------------------------------------------------

INVOICE_STATUS_LABELS = {
    "outstanding": "Outstanding (overdue)",
    "at_risk": "At risk (due soon)",
    "open": "Open",
    "paid": "Paid",
}
CONTRACT_STATUS_LABELS = {
    "in_force": "In force",
    "not_started": "Not yet started",
    "no_end_date": "No end date",
    "expired": "Expired",
    "processing": "Being read",
    "failed": "Could not be read",
}


def format_inr(value: str | Decimal | int | float | None) -> str | None:
    """₹ with Indian digit grouping: 994150.75 → ₹9,94,150.75."""
    if value is None:
        return None
    try:
        amount = Decimal(str(value)).quantize(Decimal("0.01"))
    except InvalidOperation:
        return None
    sign = "-" if amount < 0 else ""
    whole, fraction = f"{abs(amount):.2f}".split(".")
    if len(whole) > 3:
        head, tail = whole[:-3], whole[-3:]
        groups = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        whole = ",".join([*groups, tail])
    return f"{sign}₹{whole}.{fraction}"


def invoice_link(invoice_number: str) -> str:
    return "/invoices?" + urlencode({"view": "all", "q": invoice_number})


def contract_link(contract_id: str) -> str:
    return f"/contracts/{contract_id}"


# --- Tool definitions (sent to Claude; fixed order so the prefix caches) ------------------------

_NULLABLE_TEXT = {"type": ["string", "null"]}
_ORDER = {"type": "string", "enum": ["asc", "desc"]}

INVOICE_VIEWS = ["unpaid", "follow_up", "outstanding", "at_risk", "open", "paid", "all"]
CONTRACT_VIEWS = [
    "all", "in_force", "at_risk", "not_started", "expired", "no_end_date", "processing", "failed",
]

TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "name": "get_invoice_overview",
        "description": (
            "The invoice dashboard: today's date, the current week (7 days from the latest "
            "upload, by due date), value and count due this week, how many invoices need "
            "follow-up (outstanding + at risk), value and count per payment status, the top "
            "invoices to chase, and how many invoices are in each list view. Use it for "
            "summary questions such as 'how are my invoices doing' or 'what is due this week'."
        ),
        "strict": True,
        "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "search_invoices",
        "description": (
            "Find invoices. Statuses: outstanding = unpaid and past the due date; at_risk = "
            "unpaid and due within 5 days; open = unpaid and due later; paid. Views: 'unpaid' = "
            "every invoice not yet paid; 'follow_up' = outstanding + at_risk; the others match "
            "one status; 'all' = everything. 'search' matches invoice number or customer name "
            "(partial, case-insensitive). 'due_from'/'due_to' are YYYY-MM-DD dates (inclusive) "
            "or null. 'limit' is 1-50; 'total' and 'total_amount' always cover every match, "
            "even beyond the limit. days_until_due is negative when overdue."
        ),
        "strict": True,
        "input_schema": {
            "type": "object",
            "properties": {
                "view": {"type": "string", "enum": INVOICE_VIEWS},
                "search": _NULLABLE_TEXT,
                "due_from": _NULLABLE_TEXT,
                "due_to": _NULLABLE_TEXT,
                "sort": {
                    "type": "string",
                    "enum": ["status", "amount", "due_date", "customer_name", "invoice_number"],
                },
                "order": _ORDER,
                "limit": {"type": "integer"},
            },
            "required": ["view", "search", "due_from", "due_to", "sort", "order", "limit"],
            "additionalProperties": False,
        },
    },
    {
        "name": "get_contract_overview",
        "description": (
            "The contract dashboard: counts (total, in force, at risk, expired, not yet "
            "started, no end date), why contracts are at risk (expiring within 3 days, or high "
            "risks), and the contracts that need attention. Use it for summary questions."
        ),
        "strict": True,
        "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "search_contracts",
        "description": (
            "Find contracts and get their ids. A contract is at_risk when it expires within 3 "
            "days or has a high-severity risk (at risk is on top of its status). 'search' "
            "matches the title, file name or a party name (partial, case-insensitive), or null. "
            "'limit' is 1-25; 'total' covers every match. Use get_contract_details with an id "
            "from here to read a contract's risks, terms and dates."
        ),
        "strict": True,
        "input_schema": {
            "type": "object",
            "properties": {
                "view": {"type": "string", "enum": CONTRACT_VIEWS},
                "search": _NULLABLE_TEXT,
                "sort": {
                    "type": "string",
                    "enum": ["end_date", "start_date", "title", "high_risks"],
                },
                "order": _ORDER,
                "limit": {"type": "integer"},
            },
            "required": ["view", "search", "sort", "order", "limit"],
            "additionalProperties": False,
        },
    },
    {
        "name": "get_contract_details",
        "description": (
            "Everything read from one contract: summary, parties, key dates, main terms and "
            "risks (severity, explanation and the exact quote from the document). "
            "'contract_id' must be an id returned by search_contracts or get_contract_overview."
        ),
        "strict": True,
        "input_schema": {
            "type": "object",
            "properties": {"contract_id": {"type": "string"}},
            "required": ["contract_id"],
            "additionalProperties": False,
        },
    },
]

TOOL_NAMES = [tool["name"] for tool in TOOL_DEFINITIONS]


# --- Execution ------------------------------------------------------------------------------


@dataclass
class ToolOutcome:
    content: dict[str, Any]
    is_error: bool = False
    count: int | None = None  # records found, shown next to the lookup (AC6)
    done_label: str | None = None  # overrides the default "done" label


class ToolFailure(Exception):
    """A lookup that failed; the message is shown to the model (not the user) as the result."""


class Lookups:
    """Runs tools against the invoice and contract APIs for one chat request."""

    def __init__(
        self, client: httpx.AsyncClient, invoice_url: str, contract_url: str, request_id: str
    ) -> None:
        self._client = client
        self._invoice_url = invoice_url.rstrip("/")
        self._contract_url = contract_url.rstrip("/")
        self._request_id = request_id
        self._executors: dict[str, Callable[[dict[str, Any]], Awaitable[ToolOutcome]]] = {
            "get_invoice_overview": self._invoice_overview,
            "search_invoices": self._search_invoices,
            "get_contract_overview": self._contract_overview,
            "search_contracts": self._search_contracts,
            "get_contract_details": self._contract_details,
        }

    async def run(self, name: str, tool_input: dict[str, Any]) -> ToolOutcome:
        executor = self._executors.get(name)
        if executor is None:
            return ToolOutcome({"error": f"Unknown tool {name!r}."}, is_error=True)
        try:
            return await executor(tool_input)
        except ToolFailure as exc:
            return ToolOutcome({"error": str(exc)}, is_error=True)

    # -- HTTP --

    async def _get(self, base: str, what: str, path: str, params: dict[str, Any] | None = None):
        clean = {k: v for k, v in (params or {}).items() if v is not None}
        try:
            response = await self._client.get(
                f"{base}{path}", params=clean, headers={REQUEST_ID_HEADER: self._request_id}
            )
        except httpx.HTTPError as exc:
            raise ToolFailure(f"The {what} service could not be reached.") from exc
        if response.status_code == 404:
            raise ToolFailure(f"Not found in the {what} records.")
        if response.status_code >= 400:
            raise ToolFailure(f"The {what} service returned an error ({response.status_code}).")
        return response.json()

    def _invoices(self, path: str = "", params: dict[str, Any] | None = None):
        return self._get(self._invoice_url, "invoice", f"/api/invoices{path}", params)

    def _contracts(self, path: str = "", params: dict[str, Any] | None = None):
        return self._get(self._contract_url, "contract", f"/api/contracts{path}", params)

    # -- Invoices --

    async def _invoice_overview(self, _: dict[str, Any]) -> ToolOutcome:
        dashboard, page = await asyncio.gather(
            self._invoices("/dashboard"), self._invoices(params={"view": "all", "page_size": 1})
        )
        result: dict[str, Any] = {"today": dashboard["today"], "has_data": dashboard["has_data"]}
        if dashboard["has_data"]:
            result |= {
                "week": {"start": dashboard["week"]["start"], "end": dashboard["week"]["end"]},
                "value_due_this_week": format_inr(dashboard["value_this_week"]),
                "invoices_due_this_week": dashboard["invoices_this_week"],
                "need_follow_up": dashboard["follow_up"],
                "by_status": [
                    {
                        "status": INVOICE_STATUS_LABELS[row["status"]],
                        "count": row["count"],
                        "amount": format_inr(row["amount"]),
                    }
                    for row in dashboard["value_by_status"]
                ],
                "top_to_chase": [_invoice(item) for item in dashboard["top_follow_up"]],
                "invoices_per_view": page["counts"],
                "total_value_all_invoices": format_inr(page["total_amount"]),
            }
        return ToolOutcome(result, count=page["total"])

    async def _search_invoices(self, args: dict[str, Any]) -> ToolOutcome:
        view = args.get("view") or "all"
        if view not in INVOICE_VIEWS:
            raise ToolFailure(f"Unknown view {view!r}.")
        limit = _clamp(args.get("limit"), 1, 50, default=20)
        params = {
            "q": _text(args.get("search")),
            "due_from": _iso_date(args.get("due_from"), "due_from"),
            "due_to": _iso_date(args.get("due_to"), "due_to"),
            "sort": args.get("sort") or "status",
            "order": args.get("order") or "asc",
            "page_size": limit,
        }
        # "unpaid" is not a list view: it is follow-up (outstanding + at risk) plus open.
        views = ["follow_up", "open"] if view == "unpaid" else [view]
        pages = await asyncio.gather(*(self._invoices(params={**params, "view": v}) for v in views))
        items = [item for page in pages for item in page["items"]]
        if len(pages) > 1:
            items = _sort_invoices(items, params["sort"], params["order"])[:limit]
        total = sum(page["total"] for page in pages)
        total_amount = sum(Decimal(str(page["total_amount"])) for page in pages)
        return ToolOutcome(
            {
                "today": pages[0]["today"],
                "total": total,
                "total_amount": format_inr(total_amount),
                "showing": len(items),
                "invoices": [_invoice(item) for item in items],
            },
            count=total,
        )

    # -- Contracts --

    async def _contract_overview(self, _: dict[str, Any]) -> ToolOutcome:
        dashboard = await self._contracts("/dashboard")
        result: dict[str, Any] = {"today": dashboard["today"], "has_data": dashboard["has_data"]}
        if dashboard["has_data"]:
            result |= {
                "counts": dashboard["counts"],
                "at_risk_because": dashboard["at_risk_breakdown"],
                "still_being_read_or_failed": dashboard["unread"],
                "needs_attention": [_contract(item) for item in dashboard["needs_attention"]],
            }
        return ToolOutcome(result, count=(dashboard.get("counts") or {}).get("total", 0))

    async def _search_contracts(self, args: dict[str, Any]) -> ToolOutcome:
        view = args.get("view") or "all"
        if view not in CONTRACT_VIEWS:
            raise ToolFailure(f"Unknown view {view!r}.")
        page = await self._contracts(
            params={
                "view": view,
                "q": _text(args.get("search")),
                "sort": args.get("sort") or "end_date",
                "order": args.get("order") or "asc",
                "page_size": _clamp(args.get("limit"), 1, 25, default=10),
            }
        )
        return ToolOutcome(
            {
                "today": page["today"],
                "total": page["total"],
                "showing": len(page["items"]),
                "contracts": [_contract(item) for item in page["items"]],
            },
            count=page["total"],
        )

    async def _contract_details(self, args: dict[str, Any]) -> ToolOutcome:
        raw_id = str(args.get("contract_id") or "").strip()
        try:
            contract_id = str(uuid.UUID(raw_id))
        except ValueError as exc:
            raise ToolFailure(
                "That is not a contract id. Use an id from search_contracts."
            ) from exc
        c = await self._contracts(f"/{contract_id}")
        result = {
            **_contract(c),
            "today": c["today"],
            "file_name": c["file_name"],
            "summary": c["summary"],
            "parties": [f"{p['name']} ({p['role']})" for p in c["parties"]],
            "key_dates": [
                {"label": k["label"], "date": k["date"], "days_from_today": k["days_from_today"]}
                for k in c["key_dates"]
            ],
            "terms": [{"category": t["category"], "summary": t["summary"]} for t in c["terms"]],
            "risks": [
                {
                    "severity": r["severity"],
                    "title": r["title"],
                    "explanation": r["description"],
                    "quote": r["source_text"],
                }
                for r in c["risks"]
            ],
        }
        if c["processing_status"] == "failed":
            result["note"] = "This contract could not be read, so no details are available."
        elif c["processing_status"] != "completed":
            result["note"] = "This contract is still being read; details are not available yet."
        return ToolOutcome(result, count=len(c["risks"]), done_label=f"Read “{c['title']}”")


# --- Trimming -------------------------------------------------------------------------------


def _invoice(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "invoice_number": item["invoice_number"],
        "customer": item["customer_name"],
        "date_raised": item.get("date_raised"),
        "due_date": item["due_date"],
        "amount": format_inr(item["amount"]),
        "paid_date": item.get("paid_date"),
        "status": INVOICE_STATUS_LABELS[item["status"]],
        "days_until_due": item["days_until_due"],
        "link": invoice_link(item["invoice_number"]),
    }


def _contract(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(item["id"]),
        "title": item["title"],
        "parties": [p if isinstance(p, str) else p["name"] for p in item["parties"]],
        "start_date": item["start_date"],
        "end_date": item["end_date"],
        "days_until_end": item["days_until_end"],
        "status": CONTRACT_STATUS_LABELS.get(item["lifecycle"], item["lifecycle"]),
        "at_risk": item["at_risk"],
        "at_risk_reasons": item["at_risk_reasons"],
        "high_risk_count": item["high_risk_count"],
        "link": contract_link(str(item["id"])),
    }


_STATUS_RANK = {"outstanding": 0, "at_risk": 1, "open": 2, "paid": 3}


def _sort_invoices(items: list[dict[str, Any]], sort: str, order: str) -> list[dict[str, Any]]:
    def key(item: dict[str, Any]) -> Any:
        match sort:
            case "amount":
                return Decimal(str(item["amount"]))
            case "status":
                return (_STATUS_RANK[item["status"]], item["due_date"])
            case "customer_name":
                return item["customer_name"].casefold()
            case _:
                return item[sort]

    return sorted(items, key=key, reverse=order == "desc")


def _clamp(value: Any, low: int, high: int, default: int) -> int:
    try:
        return max(low, min(high, int(value)))
    except (TypeError, ValueError):
        return default


def _text(value: Any) -> str | None:
    text = str(value).strip()[:100] if value is not None else ""
    return text or None


def _iso_date(value: Any, field: str) -> str | None:
    if value is None or str(value).strip() == "":
        return None
    try:
        return date.fromisoformat(str(value).strip()).isoformat()
    except ValueError as exc:
        raise ToolFailure(f"{field} must be a date like 2026-09-24.") from exc


# --- Lookup labels shown to the user (AC6) ---------------------------------------------------

_INVOICE_VIEW_WORDS = {
    "unpaid": "unpaid invoices",
    "follow_up": "invoices that need follow-up",
    "outstanding": "overdue invoices",
    "at_risk": "invoices at risk",
    "open": "open invoices",
    "paid": "paid invoices",
    "all": "invoices",
}
_CONTRACT_VIEW_WORDS = {
    "all": "contracts",
    "in_force": "contracts in force",
    "at_risk": "contracts at risk",
    "not_started": "contracts not yet started",
    "expired": "expired contracts",
    "no_end_date": "contracts with no end date",
    "processing": "contracts being read",
    "failed": "contracts that could not be read",
}


def lookup_labels(name: str, tool_input: dict[str, Any]) -> tuple[str, str]:
    """(running, done) labels for a lookup. Fixed wording; never written by the model."""
    match name:
        case "get_invoice_overview":
            subject = "the invoice dashboard"
        case "get_contract_overview":
            subject = "the contract dashboard"
        case "search_invoices":
            subject = _INVOICE_VIEW_WORDS.get(tool_input.get("view", ""), "invoices")
            if _text(tool_input.get("search")):
                subject += f" matching “{_text(tool_input.get('search'))}”"
        case "search_contracts":
            subject = _CONTRACT_VIEW_WORDS.get(tool_input.get("view", ""), "contracts")
            if _text(tool_input.get("search")):
                subject += f" matching “{_text(tool_input.get('search'))}”"
        case "get_contract_details":
            return "Reading the contract", "Read the contract"
        case _:
            subject = "your records"
    return f"Checking {subject}", f"Checked {subject}"
