---
id: ADR-0002
title: Use an LLM (Claude API) to extract contract data
status: accepted   # revision 2 (2026-09-25); revision 1 accepted 2026-09-24
date: 2026-09-25
---

# ADR-0002 — Use an LLM (Claude API) to extract contract data

## Context

Contracts are free-form documents. We must extract parties, key dates, terms and risks, including
a severity for each risk. Risk assessment requires judgement, which regex and template parsing
cannot provide.

## Decision

1. **Extract plain text locally** (`pdfplumber` for PDF, `python-docx` for DOCX) and send the
   text, not the file. Word files cannot be sent to the API natively. One text pipeline serves
   both formats. We need the text locally anyway, to detect scanned PDFs and to verify the AI's
   quotes against the document.
2. **Guaranteed-shape output.** Call the Messages API with `output_config.format` (JSON schema
   generated from our Pydantic models), so the response is always schema-valid JSON. Validate it
   again with Pydantic and check every quote against the document text.
3. **Model: `claude-sonnet-5`** (`CONTRACT_LLM_MODEL`), **chosen by the product owner on
   2026-09-25** for cost, after comparing it with `claude-opus-5`. It runs with adaptive thinking
   and `effort: high` (`CONTRACT_LLM_EFFORT`). Switching to Opus 5 is a one-line `.env` edit.
4. **Reliability:**
   - Streaming with `get_final_message()` (no HTTP timeouts on long outputs).
   - The SDK's built-in retries for 429/5xx, plus one application-level retry for invalid
     results (CON-001 AC7).
   - A refusal (`stop_reason = refusal`) is treated like any other failed attempt: retried once,
     then shown as "Could not be read" with Try again. (Server-side refusal fallbacks were
     considered for Opus 5; they are not used with Sonnet 5.)
5. **Automatic prompt caching** on the fixed system prompt and schema.
6. Every extracted item is labelled as AI-extracted in the UI, and the original file is always
   downloadable for verification.

## Alternatives considered

- **Rule-based / regex parsing:** brittle across contract formats and cannot assess risk.
- **Sending the PDF as a document block:** better layout understanding, but it doesn't work for
  DOCX, and it would still need local text for quote checks. Revisit if tables in PDFs extract
  poorly.
- **`claude-opus-5`:** the more careful model for nuanced risk judgement, at about 2.5× the
  per-token price. It remains a supported setting.
- **Local open-source models:** more setup and lower quality, with no privacy requirement to justify them in a POC.

## Consequences

- **Contract text is sent to an external API.** That is acceptable for a POC with sample
  documents; revisit before real customer data is used.
- **Approximate cost per contract** (10 pages ≈ 8k input tokens; output + thinking ≈ 5–10k tokens):
  **claude-opus-5 ≈ $0.15–0.30** (about ₹13–25); **claude-sonnet-5 ≈ $0.06–0.12**. Actual usage
  is logged per contract and graphed (`llm_tokens_total`).
- Extraction takes tens of seconds, so it runs as a background job and the UI shows progress.
- Automated tests never call the API (a fake extractor is used). One opt-in live test runs the
  sample contracts.
