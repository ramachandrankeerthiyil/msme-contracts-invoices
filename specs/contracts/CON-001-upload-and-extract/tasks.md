---
id: CON-001
title: Contract upload and AI extraction — tasks
status: approved
design: ./design.md
---

# CON-001 — Tasks

Branch: `feat/CON-001-CON-002-CON-003-contracts` (the three contract features are built together,
like INV-002/003, because they share status and query code).

## A. Backend — data & files

- [ ] 1. Migration `0001_create_contract_tables` + models (contracts, parties, key dates, terms,
       risks) — _AC2, AC5_
- [ ] 2. `file_types.py`: 20 MB cap, PDF/DOCX/legacy-doc/encrypted sniffing — _AC3_
- [ ] 3. `POST /uploads`: SHA-256 duplicate check (409), store file, insert row, schedule job,
       202 — _AC2, AC3, AC3a_

## B. Backend — extraction pipeline

- [ ] 4. `text_extraction.py` (pdfplumber / python-docx, page markers, NO_TEXT, TOO_LONG,
       encrypted PDF) + fixtures built in code — _AC4, AC6_
- [ ] 5. `schema.py` (Pydantic → JSON schema, limits) and `prompt.py` — _AC4, AC10_
- [ ] 6. `claude.py`: AsyncAnthropic, streaming + `get_final_message`, `output_config.format`,
       effort, adaptive thinking, automatic caching, usage → result — _AC4, AC5_
- [ ] 7. `quotes.py`: normalised verbatim match → `source_verified` — _AC10_
- [ ] 8. `pipeline.py`: status transitions, retry-once, one-transaction save, max 2 concurrent,
       stale-job sweep at startup, `FakeExtractor` + `CONTRACT_EXTRACTOR` setting — _AC5–AC7_
- [ ] 9. `POST /{id}/retry` — _AC9_
- [ ] 10. Log events + metrics (no document text) — _AC11_
- [ ] 11. Tests for AC2–AC11 with the fake extractor; opt-in live test (`-m llm`) on both samples.

## C. Frontend

- [ ] 12. `/contracts/upload`: FileDropzone (.pdf/.docx, 20 MB), "What happens next", 202 →
        navigate to detail, 409 → "already uploaded" + link — _AC1, AC3a, AC8_
- [ ] 13. Vitest for the upload page.

## D. Verify

- [ ] 14. Playwright with the fake extractor: upload the sample .docx → progress → detail;
        duplicate → link; failure → Try again. axe.
- [ ] 15. Live check with the real API key on both sample contracts (manual, reviewed with the
        product owner). Update `.env.example` / README. Set statuses to `implemented`.
