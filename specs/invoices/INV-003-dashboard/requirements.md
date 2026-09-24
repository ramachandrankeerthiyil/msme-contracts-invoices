---
id: INV-003
title: Invoice dashboard
status: approved
depends_on: [INV-002]
---

# INV-003 — Invoice dashboard

## Goal

In a few seconds, a user sees this week's invoice position and how many invoices need chasing.

## Acceptance criteria

| ID | Criterion |
|---|---|
| INV-003-AC1 | THE SYSTEM SHALL define the current week as the 7 days from the date of the most recent upload, `[U, U + 6 days]`, and show it on screen, e.g. "Week of 24 Sep – 30 Sep 2026 (from your upload on 24 Sep)". |
| INV-003-AC2 | THE SYSTEM SHALL show a KPI card **Total invoice value this week**: the sum of `amount` for invoices in the current week. |
| INV-003-AC3 | THE SYSTEM SHALL show a KPI card **Invoices this week**: the count of invoices in the current week. |
| INV-003-AC4 | THE SYSTEM SHALL show a KPI card **Need follow-up this week**: the count of invoices that are Outstanding (including those overdue since before the week) or At risk, with a due date on or before the end of the current week, with a breakdown "N outstanding · M at risk". |
| INV-003-AC5 | THE SYSTEM SHALL compute all numbers in invoice-service (`GET /api/invoices/dashboard`), counting an invoice as "in the current week" when its **Due Date** falls within the window. |
| INV-003-AC6 | WHEN the user clicks a KPI card THE SYSTEM SHALL open the invoice list filtered to exactly the invoices behind that number. |
| INV-003-AC7 | THE SYSTEM SHALL show a "Top 5 to follow up" list (most overdue first), with customer, amount and due hint, each linking to the filtered list. |
| INV-003-AC8 | THE SYSTEM SHALL show a chart of this week's invoice value by payment status, with an accessible text/table alternative. |
| INV-003-AC9 | IF no invoices have been uploaded THEN THE SYSTEM SHALL show an empty state with an "Upload invoices" button instead of zero-value cards. |

## Out of scope

- Choosing a different week or date range; trends over time; per-customer analytics.

## Open questions

- None. (Resolved: the current week is based on Due Date.)

## Changelog

- 2026-09-25: AC4 clarified (Option B). Invoices overdue from before the week are counted, so the card shows everyone who needs chasing this week.
