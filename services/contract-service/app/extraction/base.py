"""What the pipeline needs from an extractor. The real one calls Claude; tests use a fake."""

from dataclasses import dataclass
from typing import Protocol

from app.extraction.schema import ContractExtraction

AI_FAILED_MESSAGE = (
    "We couldn't read this contract automatically. Please try again, or check the file."
)
AI_NOT_CONFIGURED_MESSAGE = (
    "Contract reading isn't set up yet. Please ask your administrator to add the AI key."
)


@dataclass(frozen=True)
class ExtractionResult:
    data: ContractExtraction
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0


class ExtractionFailed(Exception):
    """An attempt failed. `retryable` attempts are tried once more (CON-001 AC7)."""

    def __init__(self, reason: str, *, retryable: bool = True, code: str = "AI_FAILED") -> None:
        super().__init__(reason)
        self.reason = reason  # technical, for logs only
        self.retryable = retryable
        self.code = code

    @property
    def user_message(self) -> str:
        return AI_NOT_CONFIGURED_MESSAGE if self.code == "AI_NOT_CONFIGURED" else AI_FAILED_MESSAGE


class Extractor(Protocol):
    model: str

    async def extract(self, contract_text: str, file_name: str) -> ExtractionResult: ...
