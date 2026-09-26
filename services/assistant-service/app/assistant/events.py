"""What the assistant emits while answering, and the model interface it talks to."""

import json
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol

EventType = Literal["status", "text", "done", "error"]


@dataclass(frozen=True)
class Event:
    type: EventType
    data: dict[str, Any]

    def sse(self) -> str:
        """Server-Sent Events wire format (AST-001 design "API")."""
        return f"event: {self.type}\ndata: {json.dumps(self.data, ensure_ascii=False)}\n\n"


@dataclass(frozen=True)
class ToolCall:
    id: str
    name: str
    input: dict[str, Any]


@dataclass
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0

    def add(self, other: "Usage") -> None:
        self.input_tokens += other.input_tokens
        self.output_tokens += other.output_tokens
        self.cache_read_tokens += other.cache_read_tokens
        self.cache_write_tokens += other.cache_write_tokens


@dataclass
class StepResult:
    """One model turn: the content to replay into the conversation, and any lookups requested."""

    content: list[Any]
    stop_reason: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    usage: Usage = field(default_factory=Usage)


class AssistantError(Exception):
    """A failure the user sees as a friendly message; `reason` is for logs only."""

    def __init__(self, code: str, reason: str) -> None:
        super().__init__(reason)
        self.code = code
        self.reason = reason

    @property
    def user_message(self) -> str:
        if self.code == "AI_NOT_CONFIGURED":
            return "Talk to Me isn't set up yet. Please ask your administrator to add the AI key."
        return "Talk to Me couldn't answer that right now. Please try again in a moment."


class Model(Protocol):
    model: str

    def stream_step(
        self, *, system: list[dict[str, Any]], tools: list[dict[str, Any]], messages: list[Any]
    ) -> AsyncIterator[str | StepResult]:
        """Yields answer text as it is written, then exactly one StepResult."""
        ...
