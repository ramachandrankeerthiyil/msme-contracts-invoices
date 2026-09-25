"""Contract extraction with Claude (ADR-0002, CON-001 design "AI extraction").

One streamed Messages API call with a JSON-schema output format, adaptive thinking and automatic
prompt caching. The response is validated again with Pydantic. Transient API errors are retried
by the SDK itself (max_retries); anything else surfaces as ExtractionFailed for the pipeline.
"""

from typing import Any

import anthropic
from pydantic import ValidationError

from app.extraction.base import ExtractionFailed, ExtractionResult
from app.extraction.prompt import SYSTEM_PROMPT, build_user_message
from app.extraction.schema import JSON_SCHEMA, ContractExtraction

MAX_TOKENS = 32_000
TIMEOUT_SECONDS = 600.0


class ClaudeExtractor:
    def __init__(self, api_key: str, model: str, effort: str) -> None:
        self.model = model
        self._effort = effort
        self._client = (
            anthropic.AsyncAnthropic(api_key=api_key, timeout=TIMEOUT_SECONDS, max_retries=2)
            if api_key
            else None
        )

    def request_params(self, contract_text: str, file_name: str) -> dict[str, Any]:
        """Everything sent to the API (kept separate so tests can check it without a call)."""
        return {
            "model": self.model,
            "max_tokens": MAX_TOKENS,
            "thinking": {"type": "adaptive"},
            "output_config": {
                "effort": self._effort,
                "format": {"type": "json_schema", "schema": JSON_SCHEMA},
            },
            "cache_control": {"type": "ephemeral"},
            "system": SYSTEM_PROMPT,
            "messages": [{"role": "user", "content": build_user_message(contract_text, file_name)}],
        }

    async def extract(self, contract_text: str, file_name: str) -> ExtractionResult:
        if self._client is None:
            raise ExtractionFailed(
                "ANTHROPIC_API_KEY is not set", retryable=False, code="AI_NOT_CONFIGURED"
            )
        try:
            async with self._client.messages.stream(
                **self.request_params(contract_text, file_name)
            ) as stream:
                message = await stream.get_final_message()
        except anthropic.AuthenticationError as exc:
            raise ExtractionFailed(
                f"authentication failed: {exc.message}", retryable=False, code="AI_NOT_CONFIGURED"
            ) from exc
        except (
            anthropic.BadRequestError,
            anthropic.PermissionDeniedError,
            anthropic.NotFoundError,
        ) as exc:
            # Our request or account is wrong; retrying the same request will not help.
            raise ExtractionFailed(f"{type(exc).__name__}: {exc.message}", retryable=False) from exc
        except anthropic.APIError as exc:  # rate limits, overload, network, timeouts
            raise ExtractionFailed(f"{type(exc).__name__}: {exc}") from exc

        if message.stop_reason != "end_turn":
            raise ExtractionFailed(f"stop_reason={message.stop_reason}")
        text = next((block.text for block in message.content if block.type == "text"), None)
        if text is None:
            raise ExtractionFailed("response had no text block")
        try:
            data = ContractExtraction.model_validate_json(text)
        except ValidationError as exc:
            raise ExtractionFailed(f"invalid extraction: {exc.error_count()} errors") from exc

        usage = message.usage
        return ExtractionResult(
            data=data,
            model=message.model,
            input_tokens=usage.input_tokens or 0,
            output_tokens=usage.output_tokens or 0,
            cache_read_tokens=usage.cache_read_input_tokens or 0,
            cache_write_tokens=usage.cache_creation_input_tokens or 0,
        )
