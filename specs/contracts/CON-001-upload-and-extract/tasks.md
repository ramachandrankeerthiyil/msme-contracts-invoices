---
id: CON-001
title: Contract upload and AI extraction — tasks
status: implemented
design: ./design.md
---

# CON-001 — Tasks

Branch: `feat/CON-001-CON-002-CON-003-contracts` (the three contract features are built together,
like INV-002/003, because they share status and query code).

## A. Backend — data & files

- [x] 1. Migration `0001_create_contract_tables` + models (contracts, parties, key dates, terms,
       risks) — _AC2, AC5_
- [x] 2. `file_types.py`: 20 MB cap, PDF/DOCX/legacy-doc/encrypted sniffing — _AC3_
- [x] 3. `POST /uploads`: SHA-256 duplicate check (409), store file, insert row, schedule job,
       202 — _AC2, AC3, AC3a_

## B. Backend — extraction pipeline

- [x] 4. `text_extraction.py` (pdfplumber / python-docx, page markers, NO_TEXT, TOO_LONG,
       encrypted PDF) + fixtures built in code — _AC4, AC6_
- [x] 5. `schema.py` (Pydantic → JSON schema, limits) and `prompt.py` — _AC4, AC10_
- [x] 6. `claude.py`: AsyncAnthropic, streaming + `get_final_message`, `output_config.format`,
       effort, adaptive thinking, automatic caching, usage → result — _AC4, AC5_
- [x] 7. `quotes.py`: normalised verbatim match → `source_verified` — _AC10_
- [x] 8. `pipeline.py`: status transitions, retry-once, one-transaction save, max 2 concurrent,
       stale-job sweep at startup, `FakeExtractor` + `CONTRACT_EXTRACTOR` setting — _AC5–AC7_
- [x] 9. `POST /{id}/retry` — _AC9_
- [x] 10. Log events + metrics (no document text) — _AC11_
- [x] 11. Tests for AC2–AC11 with the fake extractor; opt-in live test (`-m llm`) on both samples.

## C. Frontend

- [x] 12. `/contracts/upload`: FileDropzone (.pdf/.docx, 20 MB), "What happens next", 202 →
        navigate to detail, 409 → "already uploaded" + link — _AC1, AC3a, AC8_
- [x] 13. Vitest for the upload page.

## D. Verify

- [x] 14. Playwright with the fake extractor: upload the sample .docx → progress → detail;
        duplicate → link; failure → Try again. axe.
- [x] 15. Live check with the real API key on both sample contracts (manual, reviewed with the
        product owner). Update `.env.example` / README. Set statuses to `implemented`.

## Verification (2026-09-25)

- contract-service: 107 tests passed (fake/scripted extractor; fixed today = 25 Sep 2026) plus
  2 opt-in live tests against Claude Sonnet 5 on the sample contracts (both passed; all 34
  quotes verified verbatim). ruff check/format clean; `app/core` identical in both services.
- Frontend: 112 unit tests passed; typecheck, ESLint, design-token check clean.
- End to end: 52 Playwright tests passed (8 contract tests), 0 real AI calls during the run.
- The two sample contracts were uploaded and read by the real AI into the demo data.
