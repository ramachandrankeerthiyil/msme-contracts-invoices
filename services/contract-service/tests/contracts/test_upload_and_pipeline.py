"""CON-001 API and background pipeline, with a scripted extractor (no real AI calls)."""

import asyncio
import time
from datetime import date

import pytest

from app.domain.text_extraction import NO_TEXT_MESSAGE
from app.extraction.base import ExtractionFailed, ExtractionResult
from app.extraction.schema import ContractExtraction, KeyDate, Party, Risk, Term
from tests.conftest import _execute
from tests.contracts.conftest import detail, upload, wait_for_pipeline
from tests.contracts.documents import PDF, contract_docx, image_only_pdf_bytes, text_pdf_bytes

QUOTE = "The Client shall indemnify the Service Provider against all losses without limit."


def extraction(**overrides) -> ContractExtraction:
    values = {
        "title": "Supply Agreement",
        "summary": "Fabric supply for a year.",
        "parties": [
            Party(name="Sharma Textiles Private Limited", role="Supplier"),
            Party(name="Deccan Printing Works", role="Buyer"),
        ],
        "start_date": date(2026, 4, 1),
        "end_date": date(2027, 3, 31),
        "key_dates": [
            KeyDate(label="End", date=date(2027, 3, 31), source_text="31 March 2027"),
            KeyDate(label="Start", date=date(2026, 4, 1), source_text="1 April 2026"),
        ],
        "terms": [
            Term(
                category="payment",
                summary="30 days",
                source_text="The Buyer shall pay each invoice within thirty days",
            ),
            Term(
                category="confidentiality",
                summary="Invented",
                source_text="This wording is not in the contract",
            ),
        ],
        "risks": [
            Risk(severity="low", title="Minor", description="d", source_text="Reference none"),
            Risk(severity="high", title="Unlimited indemnity", description="d", source_text=QUOTE),
        ],
    }
    values.update(overrides)
    return ContractExtraction(**values)


# --- AC2, AC4, AC5, AC10 --------------------------------------------------------------------


def test_CON_001_AC2_AC5_upload_is_accepted_quickly_then_read_and_saved(
    api, extractor, db_rows, uploads_dir
):
    extractor.on("supply.docx", extraction())

    started = time.perf_counter()
    response = upload(api, contract_docx(), "supply.docx")
    elapsed = time.perf_counter() - started

    assert response.status_code == 202
    assert elapsed < 2
    contract_id = response.json()["id"]
    assert response.json()["processing_status"] == "uploaded"
    assert (uploads_dir / f"{contract_id}.docx").exists()

    wait_for_pipeline(api)
    body = detail(api, contract_id)

    assert body["processing_status"] == "completed"
    assert body["title"] == "Supply Agreement"
    assert [p["name"] for p in body["parties"]] == [
        "Sharma Textiles Private Limited",
        "Deccan Printing Works",
    ]
    assert [k["label"] for k in body["key_dates"]] == ["Start", "End"]  # date order
    assert [r["severity"] for r in body["risks"]] == ["high", "low"]  # high first
    assert body["extraction_model"] == "scripted"
    row = db_rows(
        "SELECT input_tokens, output_tokens, cache_read_tokens, raw_extraction FROM contracts"
    )[0]
    assert (row["input_tokens"], row["output_tokens"], row["cache_read_tokens"]) == (1200, 800, 300)
    assert row["raw_extraction"]["title"] == "Supply Agreement"


def test_CON_001_AC10_quotes_are_checked_against_the_document(api, extractor):
    extractor.on("supply.docx", extraction())
    contract_id = upload(api, contract_docx(), "supply.docx").json()["id"]
    wait_for_pipeline(api)

    body = detail(api, contract_id)

    verified = {t["summary"]: t["source_verified"] for t in body["terms"]}
    assert verified == {"30 days": True, "Invented": False}
    assert body["risks"][0]["source_verified"] is True


# --- AC3, AC3a ------------------------------------------------------------------------------


def test_CON_001_AC3_wrong_type_is_rejected_and_nothing_is_stored(api, db_rows, uploads_dir):
    response = upload(api, b"plain text, not a contract file", "contract.pdf", PDF)

    assert response.status_code == 400
    assert response.json()["error"]["message"] == "Please upload a PDF or Word (.docx) file."
    assert db_rows("SELECT id FROM contracts") == []
    assert not uploads_dir.exists() or not any(uploads_dir.iterdir())


def test_CON_001_AC3_over_20_mb_is_rejected(api, db_rows):
    response = upload(api, b"%PDF-" + b"0" * (20 * 1024 * 1024), "big.pdf", PDF)

    assert response.status_code == 413
    assert response.json()["error"]["message"] == (
        "This file is larger than 20 MB. Please upload a smaller file."
    )
    assert db_rows("SELECT id FROM contracts") == []


def test_CON_001_AC3a_same_file_twice_links_to_the_first(api, extractor, db_rows):
    extractor.on("supply.docx", extraction())
    content = contract_docx()
    first = upload(api, content, "supply.docx").json()
    wait_for_pipeline(api)

    second = upload(api, content, "renamed copy.docx")

    assert second.status_code == 409
    error = second.json()["error"]
    assert error["code"] == "DUPLICATE_CONTRACT"
    assert error["message"].startswith("This contract was already uploaded on ")
    assert error["details"]["contract_id"] == first["id"]
    assert len(db_rows("SELECT id FROM contracts")) == 1


# --- AC6, AC7, AC9 --------------------------------------------------------------------------


def test_CON_001_AC6_scanned_pdf_fails_without_calling_the_ai(api, extractor):
    contract_id = upload(api, image_only_pdf_bytes(), "scan.pdf", PDF).json()["id"]
    wait_for_pipeline(api)

    body = detail(api, contract_id)

    assert body["processing_status"] == "failed"
    assert body["lifecycle"] == "failed"
    assert body["error_message"] == NO_TEXT_MESSAGE
    assert extractor.calls == []


def test_CON_001_AC7_one_failure_is_retried_automatically(api, extractor):
    extractor.on("supply.docx", ExtractionFailed("overloaded"), extraction())
    contract_id = upload(api, contract_docx(), "supply.docx").json()["id"]
    wait_for_pipeline(api)

    assert detail(api, contract_id)["processing_status"] == "completed"
    assert extractor.calls == ["supply.docx", "supply.docx"]


def test_CON_001_AC7_two_failures_give_a_friendly_message_and_log_the_reason(api, extractor, logs):
    extractor.on("supply.docx", ExtractionFailed("stop_reason=max_tokens"))
    contract_id = upload(api, contract_docx(), "supply.docx").json()["id"]
    wait_for_pipeline(api)

    body = detail(api, contract_id)
    assert body["processing_status"] == "failed"
    assert body["error_message"] == (
        "We couldn't read this contract automatically. Please try again, or check the file."
    )
    assert len(extractor.calls) == 2
    failures = [line for line in logs() if line["event"] == "contract_extraction.failed"]
    assert [f["attempt"] for f in failures] == [1, 2]
    assert failures[0]["reason"] == "stop_reason=max_tokens"
    assert failures[0]["contract_id"] == contract_id


def test_CON_001_AC7_missing_key_fails_at_once_with_setup_message(api, extractor):
    extractor.on(
        "supply.docx", ExtractionFailed("no key", retryable=False, code="AI_NOT_CONFIGURED")
    )
    contract_id = upload(api, contract_docx(), "supply.docx").json()["id"]
    wait_for_pipeline(api)

    assert detail(api, contract_id)["error_message"].startswith("Contract reading isn't set up")
    assert len(extractor.calls) == 1


def test_CON_001_AC9_try_again_reruns_a_failed_contract(api, extractor):
    extractor.on("supply.docx", ExtractionFailed("down"), ExtractionFailed("down"), extraction())
    contract_id = upload(api, contract_docx(), "supply.docx").json()["id"]
    wait_for_pipeline(api)
    assert detail(api, contract_id)["processing_status"] == "failed"

    response = api.post(f"/api/contracts/{contract_id}/retry")
    assert response.status_code == 202
    wait_for_pipeline(api)

    body = detail(api, contract_id)
    assert body["processing_status"] == "completed"
    assert body["error_message"] is None


def test_CON_001_AC9_only_failed_contracts_can_be_retried(api, extractor):
    extractor.on("supply.docx", extraction())
    contract_id = upload(api, contract_docx(), "supply.docx").json()["id"]
    wait_for_pipeline(api)

    response = api.post(f"/api/contracts/{contract_id}/retry")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "NOT_RETRYABLE"


def test_CON_001_contract_removed_while_being_read_is_handled_quietly(
    settings, api, extractor, logs
):
    class DeletesDuringRead:
        model = "deleting"

        async def extract(self, contract_text, file_name):
            await _execute(settings, f'DELETE FROM "{settings.db_schema}".contracts')
            return ExtractionResult(data=extraction(), model=self.model)

    api.app.state.pipeline._extractor = DeletesDuringRead()
    upload(api, contract_docx(), "supply.docx")
    wait_for_pipeline(api)

    events = [line["event"] for line in logs()]
    assert "contract_extraction.discarded" in events
    assert not any(line.get("error_code") == "INTERNAL" for line in logs())


def test_CON_001_interrupted_contracts_are_marked_failed_at_startup(settings, api, extractor):
    extractor.on("supply.docx", extraction())
    contract_id = upload(api, contract_docx(), "supply.docx").json()["id"]
    wait_for_pipeline(api)
    asyncio.run(
        _execute(
            settings,
            f"UPDATE \"{settings.db_schema}\".contracts SET processing_status = 'analysing'",
        )
    )

    count = api.portal.call(api.app.state.pipeline.mark_interrupted)

    assert count == 1
    assert detail(api, contract_id)["error_message"] == "Reading was interrupted. Please try again."


# --- AC11 and file download -----------------------------------------------------------------


def test_CON_001_AC11_completed_log_has_usage_but_no_document_text(api, extractor, logs):
    extractor.on("supply.docx", extraction())
    upload(api, contract_docx(), "supply.docx")
    wait_for_pipeline(api)

    lines = logs()
    done = next(line for line in lines if line["event"] == "contract_extraction.completed")
    assert (done["input_tokens"], done["output_tokens"], done["risks"]) == (1200, 800, 2)
    assert done["unverified_quotes"] == 1
    everything = str(lines)
    assert "indemnify" not in everything
    assert "Sharma Textiles" not in everything


def test_CON_002_AC7_original_file_downloads_with_its_name(api, extractor):
    extractor.on("Supply Agreement.pdf", extraction())
    content = text_pdf_bytes("Supply Agreement", QUOTE, "More text " * 40)
    contract_id = upload(api, content, "Supply Agreement.pdf", PDF).json()["id"]
    wait_for_pipeline(api)

    response = api.get(f"/api/contracts/{contract_id}/file")

    assert response.status_code == 200
    assert response.content == content
    assert response.headers["content-type"] == "application/pdf"
    # Names with spaces are sent RFC 5987-encoded; browsers show "Supply Agreement.pdf".
    assert response.headers["content-disposition"] == (
        "attachment; filename*=utf-8''Supply%20Agreement.pdf"
    )


@pytest.mark.parametrize(
    "path", ["/api/contracts/not-a-uuid", "/api/contracts/00000000-0000-0000-0000-000000000000"]
)
def test_CON_002_unknown_contract_is_a_friendly_404(api, path):
    response = api.get(path)

    assert response.status_code == 404
    assert response.json()["error"]["message"] == "We couldn't find that contract."
