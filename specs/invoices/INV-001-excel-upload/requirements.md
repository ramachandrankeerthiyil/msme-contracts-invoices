---
id: INV-001
title: Invoice Excel upload
status: implemented
depends_on: [INVOICES, PLT-001, PLT-002]
---

# INV-001 — Invoice Excel upload

## Goal

A user uploads their invoice spreadsheet, and the system creates new invoices, updates existing
ones, and clearly reports any rows it couldn't use.

## User stories

- As a business owner, I want to upload my invoice spreadsheet, so that I don't have to type invoices in.
- As a business owner, I want to re-upload an updated sheet (e.g. with paid dates filled in), so that my invoices stay current.
- As a business owner, I want to be told exactly which rows had problems and why, so that I can fix them.

## Acceptance criteria

| ID | Criterion |
|---|---|
| INV-001-AC1 | THE SYSTEM SHALL provide an Upload invoices page with a drop zone, a "Choose file" button, the text "Excel (.xlsx), up to 10 MB", the list of required columns, and a "Download template" link. |
| INV-001-AC2 | IF the file is not a valid `.xlsx` (checked by content) or is over 10 MB THEN THE SYSTEM SHALL reject it with a plain-language message and save nothing. |
| INV-001-AC3 | IF any required header (Invoice Number, Customer Name, Date Raised, Due Date, Amount, Paid Date) is missing from the first sheet THEN THE SYSTEM SHALL reject the whole file, name the missing columns, and save nothing. The optional **Customer Email** header (AC13) may be absent. |
| INV-001-AC4 | THE SYSTEM SHALL validate every row against the rules in `invoices/module.md`. It SHALL reject invalid rows individually (with row number and reason) and still save the valid ones. |
| INV-001-AC5 | WHEN a row's invoice number does not yet exist THE SYSTEM SHALL create the invoice with `record_status = new`. |
| INV-001-AC6 | WHEN a row's invoice number already exists THE SYSTEM SHALL overwrite the invoice's fields with the new values, set `record_status = updated`, and set `record_updated_at` to the upload time. |
| INV-001-AC6a | WHEN the same invoice number appears more than once in one file THE SYSTEM SHALL use the **last** occurrence, overwriting the earlier row(s), mark the invoice `updated` with `record_updated_at` = upload time, and list each overwrite in the summary ("Row 42 replaced row 17 for INV-1001"). |
| INV-001-AC7 | THE SYSTEM SHALL treat a blank Paid Date as unpaid and a valid Paid Date as paid. |
| INV-001-AC8 | THE SYSTEM SHALL record every upload (file name, time, rows read/created/updated/rejected, and rejection reasons). The time of the most recent upload defines the "current week" (INV-003). |
| INV-001-AC9 | WHEN processing finishes THE SYSTEM SHALL show a summary, e.g. "120 rows read · 100 new · 15 updated · 2 replaced by a later row · 3 need fixing", with a table of rejected rows (row, invoice number, reason), a list of in-file overwrites, and a "View invoices" button. |
| INV-001-AC10 | THE SYSTEM SHALL process a 5,000-row file in under 10 seconds. |
| INV-001-AC11 | WHEN the user clicks "Download template" THE SYSTEM SHALL download an `.xlsx` with the correct headers (including the optional Customer Email) and one example row. |
| INV-001-AC12 | THE SYSTEM SHALL save each upload in a single transaction: either all valid rows from the file are saved, or (on an unexpected error) none are. |
| INV-001-AC13 | WHEN the first sheet has an optional **Customer Email** column THE SYSTEM SHALL read it, store each address trimmed and in lower case on the invoice, and let a later row for the same invoice overwrite it like any other field (a blank cell clears it). IF an address is not a valid email address (for example `accounts@` or `no spaces@x.in`) THEN THE SYSTEM SHALL reject that row with a plain-language reason, like any other invalid row. A sheet without the column SHALL still upload exactly as before. The address is used to send payment reminders (INV-004). |

## Out of scope

- `.xls` and `.csv` files; multiple worksheets; column mapping for non-standard headers.

## Open questions

- None. (Resolved: `.xlsx` only; duplicates within a file follow "last row wins".)

## Changelog

- **2026-10-05** — Added AC13 (optional Customer Email column, validated and stored) and updated AC3 and AC11 to match. Needed by INV-004 (email payment reminder) so that each invoice carries its client's address. Re-approved by the product owner together with INV-004.
