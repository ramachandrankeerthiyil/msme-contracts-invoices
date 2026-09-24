---
id: INV-001
title: Invoice Excel upload — design
status: approved
requirements: ./requirements.md
---

# INV-001 — Design

## Overview

```
UploadInvoicesPage ──multipart──► POST /api/invoices/uploads
                                     1. check size & file type          ─► 400/413, nothing saved
                                     2. open first sheet, map headers   ─► 422 MISSING_COLUMNS
                                     3. parse + validate each row       ─► rejections[]
                                     4. resolve in-file duplicates      ─► overwrites[] (last row wins)
                                     5. ONE transaction:
                                          insert invoice_uploads row
                                          upsert invoices (ON CONFLICT … DO UPDATE)
                                        then store the original file
                                     6. log + metrics
                  ◄── 201 UploadSummary ─┘
```

The work is synchronous: 5,000 rows parse and upsert in well under 10s (AC10), so no background
job is needed.

## API

### `POST /api/invoices/uploads`

`multipart/form-data`, field `file`.

**201 Created**
```json
{
  "id": "5b0e…", "file_name": "september.xlsx", "uploaded_at": "2026-09-24T05:12:44Z",
  "status": "completed",
  "rows_total": 120, "rows_created": 100, "rows_updated": 15, "rows_overwritten": 2, "rows_rejected": 3,
  "rejections": [ { "row": 18, "invoice_number": "INV-1017", "reason": "Due Date (01 Sep 2026) is before Date Raised (05 Sep 2026)." } ],
  "overwrites": [ { "row": 42, "replaced_row": 17, "invoice_number": "INV-1001" } ]
}
```
Invariant: `rows_total = rows_created + rows_updated + rows_overwritten + rows_rejected`.
`status` is `completed` when at least one row was saved, and `no_valid_rows` otherwise.

**File-level errors** (nothing is saved — AC2, AC3):

| HTTP | `code` | `message` | `details` |
|---|---|---|---|
| 413 | `FILE_TOO_LARGE` | "This file is larger than 10 MB. Please upload a smaller file." | `{max_bytes}` |
| 400 | `INVALID_FILE_TYPE` | "Please upload an Excel file (.xlsx)." | — |
| 400 | `FILE_PROTECTED` | "This file is password-protected. Please remove the password and try again." | — |
| 422 | `MISSING_COLUMNS` | "Your file is missing these columns: Due Date, Paid Date. Download the template to see the correct layout." | `{missing: [...], found: [...]}` |
| 422 | `NO_DATA_ROWS` | "We couldn't find any invoice rows below the header." | — |
| 422 | `TOO_MANY_ROWS` | "This file has more than 20,000 rows. Please split it into smaller files." | `{max_rows}` |

### `GET /api/invoices/uploads?page=1&page_size=10`

Upload history, newest first. Each item is the same shape as the summary, minus `rejections`
and `overwrites`.

### `GET /api/invoices/template`

Returns `invoice-template.xlsx` (`Content-Disposition: attachment`), built on the fly with
openpyxl:
- **Sheet 1 "Invoices":** the 6 headers (bold, light-blue fill, frozen header row, sensible
  column widths, date columns formatted `DD-MMM-YYYY`) and one example row.
- **Sheet 2 "How to fill this in":** plain-language rules for each column. Only sheet 1 is read
  on upload.

## Data (migration `0001_create_invoice_tables`)

```sql
CREATE TABLE invoices.invoice_uploads (
  id uuid PRIMARY KEY, file_name text NOT NULL, stored_path text,
  uploaded_at timestamptz NOT NULL, status text NOT NULL CHECK (status IN ('completed','no_valid_rows')),
  rows_total int NOT NULL, rows_created int NOT NULL, rows_updated int NOT NULL,
  rows_overwritten int NOT NULL, rows_rejected int NOT NULL,
  rejections jsonb NOT NULL DEFAULT '[]', overwrites jsonb NOT NULL DEFAULT '[]',
  created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE invoices.invoices (
  id uuid PRIMARY KEY,
  invoice_number text NOT NULL,             -- as displayed (trimmed)
  invoice_number_key text NOT NULL UNIQUE,  -- upper(trim(invoice_number)): case-insensitive identity
  customer_name text NOT NULL, date_raised date NOT NULL, due_date date NOT NULL,
  amount numeric(14,2) NOT NULL CHECK (amount > 0), paid_date date,
  record_status text NOT NULL CHECK (record_status IN ('new','updated')),
  record_updated_at timestamptz,
  first_upload_id uuid NOT NULL REFERENCES invoices.invoice_uploads(id),
  last_upload_id  uuid NOT NULL REFERENCES invoices.invoice_uploads(id),
  created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ON invoices.invoices (due_date);
CREATE INDEX ON invoices.invoices (paid_date);
```

## Logic

### 1. File checks (AC2)
- Stream the upload to a temp file, aborting once it passes 10 MB (`FILE_TOO_LARGE`).
- **Type by content:** the file must be a ZIP (`PK\x03\x04`) containing `xl/workbook.xml`.
  An OLE compound file (`D0 CF 11 E0`) is either a legacy `.xls` or an encrypted `.xlsx`:
  if it contains an `EncryptionInfo` stream it is `FILE_PROTECTED`, otherwise `INVALID_FILE_TYPE`.
- Open with `openpyxl.load_workbook(read_only=True, data_only=True)`. Read the **first
  worksheet** (`wb.worksheets[0]`).

### 2. Headers (AC3)
- Row 1. Normalise each header: trim, collapse inner whitespace, lowercase.
- Required: `invoice number`, `customer name`, `date raised`, `due date`, `amount`, `paid date`.
  Extra columns are ignored, and column order doesn't matter.
- Any missing header → `MISSING_COLUMNS`, listing names in their display form.

### 3. Rows (AC4, AC7)
- Data rows start at row 2. Fully blank rows are skipped and not counted. `row` in messages is
  the Excel row number the user sees.
- Each row is parsed into a `ParsedInvoice` or a list of problems. All of a row's problems are
  reported together in one reason, joined with "; ".

| Field | Accepts | Rejects with |
|---|---|---|
| Invoice Number | text; whole numbers (`1001.0` → `"1001"`); trimmed; ≤ 50 chars | "Invoice Number is missing." / "…is too long (max 50 characters)." |
| Customer Name | text, trimmed, ≤ 200 chars | "Customer Name is missing." |
| Date Raised / Due Date / Paid Date | Excel date cells; Excel serial numbers; text in `YYYY-MM-DD`, `DD-MM-YYYY`, `DD/MM/YYYY`, `DD-Mon-YYYY`, `DD Mon YYYY` (**day first**, Indian convention) | "Due Date '31/13/2026' is not a valid date." |
| Amount | numbers; text with `₹`, `,` and spaces stripped; `Decimal`, > 0, ≤ 2 decimals, < 10¹² | "Amount must be greater than zero." / "Amount can have at most 2 decimal places." |
| Cross-field | `due_date ≥ date_raised`; `paid_date ≥ date_raised` (if present) | "Due Date (01 Sep 2026) is before Date Raised (05 Sep 2026)." |

- Blank Paid Date → unpaid; a valid Paid Date → paid (AC7).
- A formula cell with no cached value reads as empty. The row is rejected with "<Column> contains
  a formula with no saved value. Open the file in Excel, save it, and upload again."

### 4. In-file duplicates (AC6a)
- Process valid rows top to bottom into `dict[invoice_number_key → (ParsedInvoice, row)]`.
  A later row replaces an earlier one, and `overwrites` records `{row, replaced_row, invoice_number}`.
- **Invalid rows never overwrite.** If row 42 duplicates row 17 but row 42 is invalid, row 17 is
  kept and row 42 appears in `rejections`.
- Keys that were overwritten within the file are in `overwritten_keys`.

### 5. Persist (AC5, AC6, AC6a, AC8, AC12)

One transaction (`async with session.begin()`):
1. Insert the `invoice_uploads` row (counts filled in at the end of the transaction).
2. Bulk upsert the surviving rows:
   ```sql
   INSERT INTO invoices.invoices (id, invoice_number, invoice_number_key, customer_name, date_raised,
          due_date, amount, paid_date, record_status, record_updated_at, first_upload_id, last_upload_id)
   VALUES (…)                      -- record_status = 'updated' + record_updated_at = now IF key ∈ overwritten_keys
                                   -- else 'new' + NULL
   ON CONFLICT (invoice_number_key) DO UPDATE SET
          invoice_number = EXCLUDED.invoice_number, customer_name = EXCLUDED.customer_name,
          date_raised = EXCLUDED.date_raised, due_date = EXCLUDED.due_date, amount = EXCLUDED.amount,
          paid_date = EXCLUDED.paid_date, record_status = 'updated', record_updated_at = :now,
          last_upload_id = EXCLUDED.last_upload_id, updated_at = :now
   RETURNING (xmax = 0) AS inserted;
   ```
   `rows_created` = count of `inserted`; `rows_updated` = the rest.
3. Update the upload row's counts and `status`.
4. Copy the temp file to `/data/uploads/invoices/<upload_id>.xlsx` and set `stored_path`.
   If the copy fails, the transaction rolls back.

On any unexpected exception the transaction rolls back and the stored file (if written) is
deleted, so nothing is saved (AC12). The client gets `INTERNAL_ERROR` with the request ID.

**Current week (for INV-003):** "the most recent upload" = the latest `invoice_uploads` row with
`status = 'completed'`. An upload where every row was rejected does not move the current week.

### Code structure

```
app/api/uploads.py            # routes: POST/GET uploads, GET template
app/domain/invoice_rules.py   # value parsing/validation (pure functions, no I/O)
app/domain/excel_reader.py    # file checks, header mapping, row iteration
app/domain/upload_service.py  # orchestration: read → validate → dedupe → persist → log/metrics
app/domain/template.py        # template workbook builder
app/db/models.py, app/db/invoice_repo.py
```

## UI — `/invoices/upload`

Page header: **Upload invoices** (breadcrumb Invoices › Upload).

**1. Choose file (card)**
- `FileDropzone` (new shared component in `components/common/`, reused by CON-001): a large
  dashed `--color-border` area on `--color-surface`, a cloud-upload icon, "Drag your Excel file
  here", **or** a "Choose file" secondary button. `accept=".xlsx"`.
- Helper text: "Excel (.xlsx), up to 10 MB." Required columns are shown as a list:
  Invoice Number · Customer Name · Date Raised · Due Date · Amount · Paid Date (leave blank if unpaid).
- A "Download template" link-button with a download icon.
- The client checks extension and size before upload and shows the same messages as the API.

**2. Selected**
- File name + size, a primary **Upload invoices** button, and a "Choose a different file" link.

**3. Uploading**
- A progress bar driven by XHR upload progress, then "Checking your invoices…" with a spinner.
  The button is disabled; the page never auto-navigates away.

**4. Result**
- A success banner, e.g. **"Upload complete."** "120 rows read · 100 new · 15 updated · 2
  replaced by a later row · 3 need fixing." If `no_valid_rows`, a warning banner instead:
  "No invoices were saved. Please fix the rows below and upload again."
- Four stat tiles: New · Updated · Replaced in file · Need fixing (the last is a warning variant if > 0).
- **"Rows that need fixing"** table: Row · Invoice number · What's wrong. Shown when there are rejections.
- **"Rows replaced by a later row"**: collapsible list, e.g. "Row 42 replaced row 17 (INV-1001)".
- Actions: primary **View invoices** (`/invoices`) and secondary **Upload another file**.

**File-level error:** `ErrorAlert` with the API message. For `MISSING_COLUMNS` it also lists the
missing columns and shows the template link. The file stays selected so the user can retry.

**Recent uploads** (below the card): the last 5 uploads (date/time, file name, summary counts)
from `GET /uploads`.

## Observability

| Event | Level | Fields |
|---|---|---|
| `invoice_upload.received` | info | `size_bytes`, `file_name` |
| `invoice_upload.rejected` | warning | `code` (e.g. `MISSING_COLUMNS`), `missing` |
| `invoice_upload.completed` | info | `upload_id`, `status`, `rows_total/created/updated/overwritten/rejected`, `duration_ms` |
| `invoice_upload.failed` | error | `exc_info` (rolled back) |

Metrics: `invoice_uploads_total{result}` and `invoice_rows_total{outcome}` (see PLT-002).
Row contents are never logged.

## Edge cases & errors

| Case | Behaviour |
|---|---|
| Header row only | `NO_DATA_ROWS` |
| Blank rows in the middle | Skipped silently, not counted |
| Hidden first sheet | Still read (it is the first worksheet). The instructions say to put invoices on the first sheet. |
| Merged cells | Only the top-left cell holds a value; other cells read as empty and are validated normally |
| Same invoice number with different case/spacing (`inv-1` vs ` INV-1 `) | Treated as the same invoice (`invoice_number_key`) |
| Negative amount (credit note) | Rejected: "Amount must be greater than zero." |
| Paid Date in the future | Accepted and treated as paid (the rule only requires ≥ Date Raised) |
| Re-uploading exactly the same file | Every row updates; all invoices become "Updated on <today>" (per the product decision) |
| Two uploads at the same moment | Out of scope for the POC. The unique key still prevents duplicate invoices. |

## Testing

Test workbooks are built in code with openpyxl fixtures, so no binary files live in `tests/`.
`scripts/make_samples.py` generates `samples/invoices-sample.xlsx` (about 60 rows spanning every
status) for demos.

| AC | Tests |
|---|---|
| AC2 | `.xls` bytes, `.pdf` renamed to `.xlsx`, encrypted xlsx, 10 MB + 1 byte → correct code; no DB rows, no stored file |
| AC3 | Each required header missing (parametrised); extra columns ignored; shuffled column order and case/space variants accepted |
| AC4 | Parametrised row validation table (every rule in the Rows table); valid rows saved alongside invalid ones |
| AC5, AC6 | First upload creates `new`; a second upload with changed amount → `updated`, `record_updated_at` set, fields overwritten |
| AC6a | Duplicate in file → last wins, `overwrites` entry, status `updated`; invalid later duplicate does not overwrite |
| AC7 | Blank vs. filled Paid Date |
| AC8 | Upload row counts; `status = no_valid_rows` when all rows are rejected; current-week anchor ignores it |
| AC9 | Playwright: upload the sample → summary line, rejected-rows table, View invoices button |
| AC10 | Performance test: a generated 5,000-row file completes in < 10s (marked `slow`) |
| AC11 | Template endpoint returns a workbook whose sheet 1 headers match the spec exactly; uploading the template succeeds with 1 row created |
| AC12 | DB failure injected mid-upsert → no invoices, no upload row, no stored file |
| PLT-002 | `invoice_upload.completed` log fields; metrics counters increment |
