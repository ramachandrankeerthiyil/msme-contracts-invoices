---
id: INV-002
title: Invoice list with status flags
status: implemented
depends_on: [INV-001]
---

# INV-002 — Invoice list with status flags

## Goal

A user sees their invoices with outstanding and at-risk ones clearly flagged, so that they know
whom to chase first.

## Acceptance criteria

| ID | Criterion |
|---|---|
| INV-002-AC1 | THE SYSTEM SHALL list invoices in a table with: invoice number, customer name, date raised, due date, amount, paid date, payment status badge, due hint ("due in 3 days", "12 days overdue", "paid on 20 Sep 2026"), and a **Record status** column. |
| INV-002-AC1a | THE SYSTEM SHALL show Record status as "New", or as an Info badge reading "Updated on <date>" (from `record_updated_at`, e.g. "Updated on 24 Sep 2026"). |
| INV-002-AC2 | THE SYSTEM SHALL compute payment status (Paid, Outstanding, At risk, Open) using the rules in `invoices/module.md`, relative to today. |
| INV-002-AC3 | THE SYSTEM SHALL show quick-filter tabs with counts: **Needs follow-up** (default), Outstanding, At risk, Open, Paid, All. |
| INV-002-AC4 | THE SYSTEM SHALL sort the default view Outstanding first (most overdue first), then At risk (soonest due first), and let the user sort by any column. |
| INV-002-AC5 | THE SYSTEM SHALL let the user search by invoice number or customer name, and filter to "Updated" invoices only. |
| INV-002-AC6 | THE SYSTEM SHALL show the total amount of the invoices currently shown, e.g. "Total: ₹4,25,000.00 across 18 invoices". |
| INV-002-AC7 | THE SYSTEM SHALL keep filters, search and sort in the URL, so that a filtered view can be bookmarked and the Back button restores it. |
| INV-002-AC8 | IF there are no invoices THEN THE SYSTEM SHALL show an empty state with an "Upload invoices" button. IF a filter matches nothing THEN it SHALL say so and offer "Clear filters". |
| INV-002-AC9 | THE SYSTEM SHALL let the user export the current view to `.xlsx`. |

## Out of scope

- Editing invoices or marking them paid in the UI (re-upload the sheet instead).
- Sending reminders.

## Open questions

- None. (Resolved: INR with `en-IN` formatting.)
