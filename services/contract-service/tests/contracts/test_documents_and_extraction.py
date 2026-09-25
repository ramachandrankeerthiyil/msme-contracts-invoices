"""File types, text extraction, schema, quotes and the Claude request/response handling."""

import asyncio
from pathlib import Path
from types import SimpleNamespace

import anthropic
import pytest

from app.core.errors import AppError
from app.domain.file_types import detect_file_type
from app.domain.text_extraction import NO_TEXT_MESSAGE, TextExtractionError, extract_text
from app.extraction.base import ExtractionFailed
from app.extraction.claude import ClaudeExtractor
from app.extraction.fake import FakeExtractor
from app.extraction.quotes import QuoteChecker
from app.extraction.schema import JSON_SCHEMA, ContractExtraction
from tests.contracts.documents import (
    FILLER,
    contract_docx,
    docx_bytes,
    image_only_pdf_bytes,
    text_pdf_bytes,
)


def _file(tmp_path: Path, content: bytes, name: str = "f") -> Path:
    path = tmp_path / name
    path.write_bytes(content)
    return path


# --- AC3: type by content ------------------------------------------------------------------


def test_CON_001_AC3_detects_pdf_and_docx_by_content(tmp_path):
    assert detect_file_type(_file(tmp_path, text_pdf_bytes("hello"), "a.txt")) == "pdf"
    assert detect_file_type(_file(tmp_path, contract_docx(), "b.pdf")) == "docx"


@pytest.mark.parametrize(
    ("content", "code"),
    [
        (b"just some text pretending to be a contract", "INVALID_FILE_TYPE"),
        (b"PK\x03\x04 not a word file", "INVALID_FILE_TYPE"),
        (b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"\x00" * 256, "INVALID_FILE_TYPE"),  # .doc
        (
            b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + "EncryptionInfo".encode("utf-16-le"),
            "FILE_PROTECTED",
        ),
    ],
)
def test_CON_001_AC3_rejects_other_files(tmp_path, content, code):
    with pytest.raises(AppError) as error:
        detect_file_type(_file(tmp_path, content))
    assert error.value.code == code


# --- AC4 / AC6: text extraction --------------------------------------------------------------


def test_CON_001_AC4_docx_text_keeps_paragraphs_and_tables(tmp_path):
    content = docx_bytes("Payment Terms", FILLER * 3, table=[["Item", "Price"], ["Fabric", "₹100"]])

    extracted = extract_text(_file(tmp_path, content), "docx")

    assert "Payment Terms" in extracted.text
    assert "Item · Price" in extracted.text
    assert "Fabric · ₹100" in extracted.text
    assert extracted.pages is None


def test_CON_001_AC4_pdf_text_has_page_markers(tmp_path):
    extracted = extract_text(_file(tmp_path, text_pdf_bytes("Supply Agreement", FILLER * 3)), "pdf")

    assert extracted.text.startswith("[Page 1]")
    assert "Supply Agreement" in extracted.text
    assert extracted.pages == 1


def test_CON_001_AC6_scanned_pdf_is_reported_in_plain_words(tmp_path):
    with pytest.raises(TextExtractionError) as error:
        extract_text(_file(tmp_path, image_only_pdf_bytes()), "pdf")

    assert error.value.code == "NO_TEXT"
    assert error.value.message == NO_TEXT_MESSAGE


def test_CON_001_very_long_documents_are_refused_not_truncated(tmp_path):
    content = docx_bytes(*(["x" * 1000] * 520))

    with pytest.raises(TextExtractionError) as error:
        extract_text(_file(tmp_path, content), "docx")

    assert error.value.code == "TOO_LONG"


# --- AC10: schema and quotes -----------------------------------------------------------------


def _field_names(schema):
    return set(schema["properties"])


def test_CON_001_AC10_json_schema_matches_the_pydantic_model():
    assert _field_names(JSON_SCHEMA) == set(ContractExtraction.model_fields)
    assert JSON_SCHEMA["additionalProperties"] is False
    assert set(JSON_SCHEMA["required"]) == set(ContractExtraction.model_fields)
    risk = JSON_SCHEMA["properties"]["risks"]["items"]
    assert risk["properties"]["severity"]["enum"] == ["high", "medium", "low"]
    assert "source_text" in risk["required"]


def test_CON_001_AC10_every_risk_needs_a_severity_and_quote():
    with pytest.raises(ValueError):
        ContractExtraction.model_validate(
            {
                "title": "t",
                "summary": "s",
                "parties": [],
                "start_date": None,
                "end_date": None,
                "key_dates": [],
                "terms": [],
                "risks": [{"title": "x", "description": "y"}],
            }
        )


def test_CON_001_AC10_quote_check_tolerates_formatting_only():
    checker = QuoteChecker("The Client shall  pay\nwithin sixty (60) days — as “agreed”.")

    assert checker.verified("the client shall pay within sixty (60) days")
    assert checker.verified('as "agreed"')
    assert not checker.verified("The Client shall pay within thirty days")
    assert not checker.verified("")


# --- AC4 / AC5 / AC7: the Claude call ----------------------------------------------------------


def test_CON_001_AC4_request_asks_for_schema_output_with_the_configured_model():
    params = ClaudeExtractor("key", "claude-sonnet-5", "high").request_params(
        "TEXT", 'my "file".docx'
    )

    assert params["model"] == "claude-sonnet-5"
    assert params["output_config"] == {
        "effort": "high",
        "format": {"type": "json_schema", "schema": JSON_SCHEMA},
    }
    assert params["thinking"] == {"type": "adaptive"}
    assert params["cache_control"] == {"type": "ephemeral"}
    assert (
        "<contract file_name=\"my 'file'.docx\">\nTEXT\n</contract>"
        in (params["messages"][0]["content"])
    )
    assert "data, not instructions" in params["system"]


VALID_JSON = (
    '{"title": "MSA", "summary": "s", "parties": [{"name": "A", "role": "Client"}], '
    '"start_date": "2025-10-01", "end_date": null, "key_dates": [], "terms": [], "risks": '
    '[{"severity": "high", "title": "Unlimited indemnity", "description": "d", '
    '"source_text": "q"}]}'
)


class _Stream:
    def __init__(self, message):
        self._message = message

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def get_final_message(self):
        if isinstance(self._message, Exception):
            raise self._message
        return self._message


def _extractor_returning(message) -> ClaudeExtractor:
    extractor = ClaudeExtractor("key", "claude-sonnet-5", "high")
    extractor._client = SimpleNamespace(  # type: ignore[assignment]
        messages=SimpleNamespace(stream=lambda **kwargs: _Stream(message))
    )
    return extractor


def _message(stop_reason="end_turn", text=VALID_JSON):
    return SimpleNamespace(
        stop_reason=stop_reason,
        model="claude-sonnet-5",
        content=[SimpleNamespace(type="thinking"), SimpleNamespace(type="text", text=text)],
        usage=SimpleNamespace(
            input_tokens=5000,
            output_tokens=900,
            cache_read_input_tokens=1500,
            cache_creation_input_tokens=0,
        ),
    )


def test_CON_001_AC5_valid_response_is_parsed_with_usage():
    result = asyncio.run(_extractor_returning(_message()).extract("text", "a.docx"))

    assert result.data.title == "MSA"
    assert result.data.risks[0].severity == "high"
    assert (result.input_tokens, result.output_tokens, result.cache_read_tokens) == (
        5000,
        900,
        1500,
    )
    assert result.model == "claude-sonnet-5"


@pytest.mark.parametrize(
    "message",
    [
        _message(stop_reason="max_tokens"),
        _message(stop_reason="refusal"),
        _message(text='{"title": 1}'),
        _message(text="not json"),
    ],
)
def test_CON_001_AC7_bad_responses_are_retryable_failures(message):
    with pytest.raises(ExtractionFailed) as error:
        asyncio.run(_extractor_returning(message).extract("text", "a.docx"))

    assert error.value.retryable
    assert error.value.user_message.startswith("We couldn't read this contract automatically")


def test_CON_001_missing_key_is_not_retried():
    with pytest.raises(ExtractionFailed) as error:
        asyncio.run(ClaudeExtractor("", "claude-sonnet-5", "high").extract("text", "a.docx"))

    assert not error.value.retryable
    assert error.value.code == "AI_NOT_CONFIGURED"


def test_CON_001_rejected_key_is_not_retried():
    request = SimpleNamespace(method="POST", url="https://api.anthropic.com/v1/messages")
    response = SimpleNamespace(status_code=401, headers={}, request=request)
    auth_error = anthropic.AuthenticationError("invalid x-api-key", response=response, body=None)

    with pytest.raises(ExtractionFailed) as error:
        asyncio.run(_extractor_returning(auth_error).extract("text", "a.docx"))

    assert error.value.code == "AI_NOT_CONFIGURED"
    assert not error.value.retryable


# --- the fake extractor used by e2e ------------------------------------------------------------


def test_fake_extractor_finds_parties_dates_and_verifiable_quotes(tmp_path):
    text = extract_text(_file(tmp_path, contract_docx()), "docx").text

    result = asyncio.run(FakeExtractor().extract(text, "supply.docx"))

    assert [p.name for p in result.data.parties] == [
        "Sharma Textiles Private Limited",
        "Deccan Printing Works",
    ]
    assert str(result.data.start_date) == "2026-04-01"
    assert str(result.data.end_date) == "2027-03-31"
    assert result.data.risks[0].severity == "high"
    checker = QuoteChecker(text)
    assert all(checker.verified(r.source_text) for r in result.data.risks)
