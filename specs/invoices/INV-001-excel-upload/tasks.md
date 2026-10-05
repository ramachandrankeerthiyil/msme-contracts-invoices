---
id: INV-001
title: Invoice Excel upload — tasks
status: implemented
design: ./design.md
---

# INV-001 — Tasks

Branch: `feat/INV-001-excel-upload` (after PLT-002 and PLT-001 have merged)

## A. Backend — data

- [x] 1. Migration `0001_create_invoice_tables` + SQLAlchemy models (`invoice_uploads`,
       `invoices` with `invoice_number_key`). — _AC5, AC6, AC8_

## B. Backend — domain (pure, unit-tested)

- [x] 2. `invoice_rules.py`: value parsers (invoice number, text, day-first dates incl. Excel
       serials, INR amounts as `Decimal`) + cross-field rules → row problems. — _AC4, AC7_
- [x] 3. `excel_reader.py`: size cap, content-type sniffing (ZIP / OLE / encrypted), first
       sheet, header normalisation + missing-column check, row iteration skipping blanks,
       max 20,000 rows. — _AC2, AC3_
- [x] 4. In-file duplicate resolution (last valid row wins, `overwrites` list,
       `overwritten_keys`). — _AC6a_
- [x] 5. Unit tests for tasks 2–4 (parametrised tables from the design). — _AC2–AC4, AC6a, AC7_

## C. Backend — persistence & API

- [x] 6. `invoice_repo.py`: single-transaction upload insert + bulk upsert with `RETURNING
       (xmax = 0)`; record status / `record_updated_at` rules; stored-file handling with
       rollback cleanup. — _AC5, AC6, AC6a, AC8, AC12_
- [x] 7. `upload_service.py` orchestration + `invoice_upload.*` log events + metrics. — _AC8, PLT-002 AC4/AC7_
- [x] 8. Routes: `POST /uploads`, `GET /uploads`, `GET /template` (+ `template.py`
       builder); error codes per the design table. — _AC2, AC3, AC9, AC11_
- [x] 9. API tests: AC2, AC3, AC5, AC6, AC6a, AC8, AC11, AC12; 5,000-row performance test. — _AC10_

## D. Frontend

- [x] 10. Shared `FileDropzone` component (drag & drop + Choose file button, accept list,
        client-side type/size check) + Vitest tests. — _AC1_
- [x] 11. `apiUpload` helper using XHR for upload progress (returns `ApiError` like `apiFetch`).
- [x] 12. `modules/invoices/pages/UploadInvoicesPage.tsx`: choose → selected → uploading →
        result states; template download; file-level error alerts. — _AC1, AC9, AC11_
- [x] 13. Result view: summary banner, stat tiles, "Rows that need fixing" table,
        collapsible overwrites list, View invoices / Upload another. — _AC9_
- [x] 14. Recent uploads list. — _AC8_
- [x] 15. Replace the `ComingSoon` route for `/invoices/upload` in the invoices module definition.

## E. Samples & verification

- [x] 16. `scripts/make_samples.py` → `samples/invoices-sample.xlsx` (every status, a few
        invalid rows, one in-file duplicate). Delivered as two files: `invoices-sample.xlsx`
        (all statuses, valid) and `invoices-with-errors.xlsx`, plus two sample `.docx` contracts.
- [x] 17. Playwright: upload the sample, check the summary and tables; upload a file with a missing
        column; keyboard-only upload; axe check. — _AC1, AC3, AC9_
- [x] 18. Set statuses to `implemented`; commit and merge.

## Verification (2026-09-24)

- invoice-service: 89 tests passed (every AC, incl. the 5,000-row performance test at ~1s);
  `ruff check` and `ruff format --check` clean.
- Frontend: 73 unit tests passed; typecheck, ESLint and token check clean.
- End to end: 32 Playwright tests passed. Both sample files were uploaded through the UI, with
  keyboard-only upload, template download, wrong-type refusal and an axe check on the result.
- Implementation notes: duplicate resolution lives in `app/domain/duplicates.py`; parsing and
  file I/O run in a worker thread (`asyncio.to_thread`) to keep the event loop free.

## Amendment (2026-10-05) — AC13, optional Customer Email

Implemented as part of INV-004: see `INV-004-email-reminder/tasks.md`, section A (tasks 1–5).
This feature returns to `implemented` when those tasks are done.
