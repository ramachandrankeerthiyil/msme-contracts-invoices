---
id: INV-002
title: Invoice list with status flags — tasks
status: implemented
design: ./design.md
---

# INV-002 — Tasks

Branch: `feat/INV-002-INV-003-invoice-list-dashboard` (built together with INV-003, which reuses
the same status and filter code).

## A. Backend — domain

- [x] 1. `clock.py`: `get_today()` dependency (APP_TIMEZONE) — _AC2_
- [x] 2. `invoice_status.py`: SQL CASE expression, rank, views, Python twin + boundary unit
       tests — _AC2, AC3, AC4_

## B. Backend — queries & API

- [x] 3. `invoice_queries.py`: filters (view, q with escaped LIKE, updated, due range), counts per
       view, total + total_amount, sort with tie-breaker, paging — _AC3–AC6_
- [x] 4. `GET /api/invoices` + schemas; validation (due_from ≤ due_to, page_size ≤ 100) — _AC1–AC6_
- [x] 5. `export.py` + `GET /api/invoices/export` (same filters, 20k cap, xlsx) + log event — _AC9_
- [x] 6. API tests with a fixed `today` for every AC above.

## C. Frontend

- [x] 7. `api.ts`: list/export types, `useInvoiceSearchParams()` (read/write URL state with defaults
       omitted) — _AC7_
- [x] 8. Status helpers: status → badge variant/label; due hint from `days_until_due` — _AC1, AC2_
- [x] 9. `InvoicesPage`: tabs with counts, search (debounced), updated-only checkbox, due-range
       chip, total line, export link — _AC3, AC5, AC6, AC9_
- [x] 10. `InvoiceTable`: columns, badges, due hints, record status, sortable headers with
        `aria-sort`, paging, dimmed stale rows while loading — _AC1, AC1a, AC4_
- [x] 11. Empty states (no invoices / no match + Clear filters) — _AC8_
- [x] 12. Replace the `/invoices` ComingSoon route; Vitest tests — _AC1–AC8_

## D. Verify

- [x] 13. `scripts/e2e.sh`: regenerate samples, then run Playwright.
- [x] 14. Playwright: sample → follow-up order, tabs, search, sort, bookmark + Back, export; axe.
- [x] 15. Set statuses to `implemented`; update module.md.

## Verification (2026-09-25)

- invoice-service: 132 tests passed (fixed "today" = 25 Sep 2026); ruff check/format clean.
- Frontend: 97 unit tests passed; typecheck, ESLint, design-token check clean.
- End to end: 44 Playwright tests passed, including: each dashboard card's number equals the
  list it opens; follow-up includes invoices overdue before the week; the table fits 1280px;
  axe on list and dashboard. `scripts/e2e.sh` regenerates the date-relative samples first.

## Amendment (2026-10-05) — Reminder column

The list gains three fields and a Reminder column as part of INV-004: see
`INV-004-email-reminder/tasks.md`, tasks 10, 12 and 20. This feature returns to `implemented`
when those tasks are done.
