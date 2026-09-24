---
id: INV-001
title: Invoice Excel upload — tasks
status: approved
design: ./design.md
---

# INV-001 — Tasks

Branch: `feat/INV-001-excel-upload` (after PLT-002 and PLT-001 have merged)

## A. Backend — data

- [ ] 1. Migration `0001_create_invoice_tables` + SQLAlchemy models (`invoice_uploads`,
       `invoices` with `invoice_number_key`). — _AC5, AC6, AC8_

## B. Backend — domain (pure, unit-tested)

- [ ] 2. `invoice_rules.py`: value parsers (invoice number, text, day-first dates incl. Excel
       serials, INR amounts as `Decimal`) + cross-field rules → row problems. — _AC4, AC7_
- [ ] 3. `excel_reader.py`: size cap, content-type sniffing (ZIP / OLE / encrypted), first
       sheet, header normalisation + missing-column check, row iteration skipping blanks,
       max 20,000 rows. — _AC2, AC3_
- [ ] 4. In-file duplicate resolution (last valid row wins, `overwrites` list,
       `overwritten_keys`). — _AC6a_
- [ ] 5. Unit tests for tasks 2–4 (parametrised tables from the design). — _AC2–AC4, AC6a, AC7_

## C. Backend — persistence & API

- [ ] 6. `invoice_repo.py`: single-transaction upload insert + bulk upsert with `RETURNING
       (xmax = 0)`; record status / `record_updated_at` rules; stored-file handling with
       rollback cleanup. — _AC5, AC6, AC6a, AC8, AC12_
- [ ] 7. `upload_service.py` orchestration + `invoice_upload.*` log events + metrics. — _AC8, PLT-002 AC4/AC7_
- [ ] 8. Routes: `POST /uploads`, `GET /uploads`, `GET /template` (+ `template.py`
       builder); error codes per the design table. — _AC2, AC3, AC9, AC11_
- [ ] 9. API tests: AC2, AC3, AC5, AC6, AC6a, AC8, AC11, AC12; 5,000-row performance test. — _AC10_

## D. Frontend

- [ ] 10. Shared `FileDropzone` component (drag & drop + Choose file button, accept list,
        client-side type/size check) + Vitest tests. — _AC1_
- [ ] 11. `apiUpload` helper using XHR for upload progress (returns `ApiError` like `apiFetch`).
- [ ] 12. `modules/invoices/pages/UploadInvoicesPage.tsx`: choose → selected → uploading →
        result states; template download; file-level error alerts. — _AC1, AC9, AC11_
- [ ] 13. Result view: summary banner, stat tiles, "Rows that need fixing" table,
        collapsible overwrites list, View invoices / Upload another. — _AC9_
- [ ] 14. Recent uploads list. — _AC8_
- [ ] 15. Replace the `ComingSoon` route for `/invoices/upload` in the invoices module definition.

## E. Samples & verification

- [ ] 16. `scripts/make_samples.py` → `samples/invoices-sample.xlsx` (every status, a few
        invalid rows, one in-file duplicate).
- [ ] 17. Playwright: upload the sample, check the summary and tables; upload a file with a missing
        column; keyboard-only upload; axe check. — _AC1, AC3, AC9_
- [ ] 18. Set statuses to `implemented`; commit and merge.
