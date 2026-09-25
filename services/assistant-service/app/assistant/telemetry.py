"""Assistant metrics (AST-001 AC14). Registered on the service's single registry."""

from prometheus_client import Counter, Histogram

from app.core.metrics import REGISTRY

CHATS = Counter(
    "assistant_chats_total",
    "Questions answered, by result (completed, failed, cancelled, rejected)",
    ["result"],
    registry=REGISTRY,
)
TOOL_CALLS = Counter(
    "assistant_tool_calls_total", "Lookups run by the assistant", ["tool", "ok"], registry=REGISTRY
)
FIRST_TEXT_SECONDS = Histogram(
    "assistant_first_text_seconds",
    "Time from question to the first words of the answer",
    registry=REGISTRY,
    buckets=(0.5, 1, 2, 3, 5, 8, 12, 20, 30, 60),
)
LLM_TOKENS = Counter(
    "llm_tokens_total", "Claude tokens used", ["model", "direction"], registry=REGISTRY
)
