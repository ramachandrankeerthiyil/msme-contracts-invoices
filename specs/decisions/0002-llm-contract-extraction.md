---
id: ADR-0002
title: Use an LLM (Claude API) to extract contract data
status: accepted
date: 2026-09-24
---

# ADR-0002 — Use an LLM (Claude API) to extract contract data

## Context

Contracts are free-form documents. We must extract parties, key dates, terms and risks, including
a severity for each risk. Risk assessment requires judgement, which regex and template parsing
cannot provide.

## Decision

1. Extract plain text locally (`pdfplumber` for PDF, `python-docx` for DOCX).
2. Send the text to the Claude API and request output that matches a fixed JSON schema
   (see `contracts/module.md#extraction-schema`).
3. Validate the response with Pydantic before storing it. Store both the normalised fields and
   the raw validated JSON (`raw_extraction`).
4. The model is configurable (`CONTRACT_LLM_MODEL`, default `claude-sonnet-5`).
5. Every extracted item is labelled as AI-extracted in the UI, and the original file is always
   downloadable for verification.

## Alternatives considered

- **Rule-based / regex parsing:** brittle across contract formats and cannot assess risk.
- **Local open-source models:** more setup and lower quality, with no privacy requirement to justify them in a POC.

## Consequences

- Contract text is sent to an external API. That is acceptable for a POC with sample documents;
  revisit before real customer data is used.
- Extraction takes seconds, so it runs as a background task and the UI polls for completion.
- API cost and latency per contract are logged and exposed as metrics.
