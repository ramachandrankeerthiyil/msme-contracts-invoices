---
id: INVOICES
title: Invoices module
status: approved
---

# Invoices module

**Service:** `services/invoice-service` · **DB schema:** `invoices` · **API base:** `/api/invoices`

Lets a user upload an Excel sheet of invoices and see which ones are outstanding, which are at
risk, and this week's totals. Independent of the Contracts module.

## Features

| ID | Feature | Status |
|---|---|---|
| INV-001 | Excel upload (create / update invoices) | implemented |
| INV-002 | Invoice list with status flags | requirements approved |
| INV-003 | Invoice dashboard | requirements approved |

## Excel input format

- **File type:** `.xlsx` only. The first worksheet is read. Row 1 holds headers.
- **Headers:** matched case-insensitively with surrounding spaces trimmed. Column order does not matter.

| Column | Required | Type | Rule |
|---|---|---|---|
| Invoice Number | Yes | text | Unique business key. Trimmed; compared case-insensitively. |
| Customer Name | Yes | text | Trimmed |
| Date Raised | Yes | date | |
| Due Date | Yes | date | Must be ≥ Date Raised |
| Amount | Yes | number | Must be > 0, at most 2 decimals |
| Paid Date | No | date | Blank = unpaid. Must be ≥ Date Raised. |

A downloadable template (`GET /api/invoices/template`) has these exact headers.

## Entities

```
invoice_uploads                          invoices
───────────────                          ────────
id              uuid PK                  id               uuid PK
file_name       text                     invoice_number   text  (as displayed)
stored_path     text                     invoice_number_key text UNIQUE  (upper + trimmed)
uploaded_at     timestamptz              customer_name    text
status          text 'completed' |       date_raised      date
                     'no_valid_rows'     due_date         date
rows_total      int                      amount           numeric(14,2)
rows_created    int                      paid_date        date NULL
rows_updated    int                      record_status    text  'new' | 'updated'
rows_overwritten int                     record_updated_at timestamptz NULL  (set when overwritten)
rows_rejected   int                      first_upload_id  uuid FK → invoice_uploads
rejections      jsonb [{row, invoice_number, reason}]   last_upload_id uuid FK → invoice_uploads
overwrites      jsonb [{row, replaced_row, invoice_number}]   created_at / updated_at
```

## Business rules

All rules are computed by the service at read time, relative to **today**. The thresholds are
configurable (`INVOICE_AT_RISK_DAYS`, default 5).

### Payment status

Mutually exclusive. Every invoice has exactly one.

| Status | Rule | Badge |
|---|---|---|
| **Paid** | `paid_date` is set | Success |
| **Outstanding** | unpaid **and** `due_date < today` | Danger — "12 days overdue" |
| **At risk** | unpaid **and** `today ≤ due_date ≤ today + 5 days` | Warning — "due in 3 days" / "due today" |
| **Open** | unpaid **and** `due_date > today + 5 days` | Neutral — "due in 21 days" |

**Needs follow-up** = Outstanding **or** At risk.

### Record status (re-uploads)

**The newest data always wins.** Rows are processed top to bottom, and a later row overwrites
an earlier one with the same invoice number.

| Case | Result |
|---|---|
| Invoice number not seen before | Create the invoice; `record_status = 'new'` |
| Invoice number already exists (from an earlier upload) | Overwrite all fields from the new row; `record_status = 'updated'`; `record_updated_at` = upload time; `last_upload_id` = this upload |
| Same invoice number more than once in one file | The **last** occurrence in the file wins and overwrites the earlier row(s). The invoice is marked `record_status = 'updated'` with `record_updated_at` = upload time. The upload summary counts these as `rows_overwritten` and lists them ("Row 42 replaced row 17 for INV-1001"). |

- Every later overwrite refreshes `record_updated_at`. An invoice never goes back to "new".
- The UI shows record status as **"New"** or **"Updated on 24 Sep 2026"**.

Record status is independent of payment status. An invoice can be both "Updated" and "Outstanding".

### Current week

The **current week** is the 7-day window `[U, U + 6 days]`, where **U = the date of the most
recent successful invoice upload** (in Asia/Kolkata). An upload is successful when it saved at
least one row (`status = 'completed'`).

An invoice is **in the current week** when its **Due Date** falls inside the window, because the
week's metrics are about collection and follow-up.

### Currency

All amounts are **INR**, formatted `en-IN` with lakh/crore grouping: `₹4,25,000.00`.

## API

| Method | Path | Purpose | Feature |
|---|---|---|---|
| POST | `/api/invoices/uploads` | Upload `.xlsx` → returns an upload summary | INV-001 |
| GET | `/api/invoices/uploads` | Upload history (newest first) | INV-001 |
| GET | `/api/invoices/template` | Download the blank Excel template | INV-001 |
| GET | `/api/invoices` | List with `status`, `follow_up`, `record_status`, `q`, sort, paging | INV-002 |
| GET | `/api/invoices/dashboard` | KPI numbers for the current week | INV-003 |
| GET | `/health`, `/ready`, `/metrics` | Operations | PLT-002 |

## Decisions

| Question | Decision |
|---|---|
| Which date puts an invoice in the current week? | Due Date |
| Duplicate invoice numbers in one file | Last row wins (overwrite); marked "Updated on <date>" |
| Currency | INR, single currency, `en-IN` formatting |
| File formats | `.xlsx` only (no `.xls` or `.csv`) |
| Does "updated" ever reset? | No. The date refreshes on each later overwrite. |

## Open questions

- None.
