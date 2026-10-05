"""One streamed Claude step for the assistant (AST-001 design "Claude request").

Answer text is yielded as it arrives; the final message (including thinking and tool_use
blocks, which must be replayed unchanged) comes last as a StepResult. Tool inputs are small and
strict-schema, so eager input streaming is left off and the server validates them.
Transient API errors are retried by the SDK (max_retries) before the stream starts.
"""

from collections.abc import AsyncIterator
from typing import Any

import anthropic

from app.assistant.events import AssistantError, StepResult, ToolCall, Usage

MAX_TOKENS = 4_000
TIMEOUT_SECONDS = 120.0


class ClaudeModel:
    def __init__(self, api_key: str, model: str, effort: str) -> None:
        self.model = model
        self._effort = effort
        self._client = (
            anthropic.AsyncAnthropic(api_key=api_key, timeout=TIMEOUT_SECONDS, max_retries=2)
            if api_key
            else None
        )

    def request_params(
        self, *, system: list[dict[str, Any]], tools: list[dict[str, Any]], messages: list[Any]
    ) -> dict[str, Any]:
        """Everything sent to the API (kept separate so tests can check it without a call)."""
        params: dict[str, Any] = {
            "model": self.model,
            "max_tokens": MAX_TOKENS,
            "thinking": {"type": "adaptive"},
            "output_config": {"effort": self._effort},
            "cache_control": {"type": "ephemeral"},
            "system": system,
            "messages": messages,
        }
        if tools:  # questions about the app use no lookups (AST-002)
            params["tools"] = tools
        return params

    async def stream_step(
        self, *, system: list[dict[str, Any]], tools: list[dict[str, Any]], messages: list[Any]
    ) -> AsyncIterator[str | StepResult]:
        if self._client is None:
            raise AssistantError("AI_NOT_CONFIGURED", "ANTHROPIC_API_KEY is not set")
        params = self.request_params(system=system, tools=tools, messages=messages)
        try:
            async with self._client.messages.stream(**params) as stream:
                async for event in stream:
                    if event.type == "text" and event.text:
                        yield event.text
                message = await stream.get_final_message()
        except anthropic.AuthenticationError as exc:
            reason = f"authentication failed: {exc.message}"
            raise AssistantError("AI_NOT_CONFIGURED", reason) from exc
        except anthropic.APIError as exc:  # bad request, rate limits, overload, network, timeouts
            raise AssistantError("ASSISTANT_FAILED", f"{type(exc).__name__}: {exc}") from exc

        if message.stop_reason == "refusal":
            raise AssistantError("ASSISTANT_FAILED", "stop_reason=refusal")
        tool_calls = [
            ToolCall(id=block.id, name=block.name, input=dict(block.input or {}))
            for block in message.content
            if block.type == "tool_use"
        ]
        if tool_calls and message.stop_reason == "max_tokens":
            # A tool input cut off mid-way must not be run.
            raise AssistantError("ASSISTANT_FAILED", "tool input truncated at max_tokens")
        usage = message.usage
        yield StepResult(
            content=list(message.content),
            stop_reason=message.stop_reason or "end_turn",
            tool_calls=tool_calls,
            usage=Usage(
                input_tokens=usage.input_tokens or 0,
                output_tokens=usage.output_tokens or 0,
                cache_read_tokens=usage.cache_read_input_tokens or 0,
                cache_write_tokens=usage.cache_creation_input_tokens or 0,
            ),
        )
