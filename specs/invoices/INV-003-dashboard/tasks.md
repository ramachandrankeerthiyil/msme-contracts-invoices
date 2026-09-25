---
id: INV-003
title: Invoice dashboard — tasks
status: implemented
design: ./design.md
---

# INV-003 — Tasks

Branch: shared with INV-002 (`feat/INV-002-INV-003-invoice-list-dashboard`), after INV-002 tasks 1–4.

## A. Backend

- [x] 1. `dashboard_queries.py`: anchor U (latest completed upload, IST date), week bounds,
       aggregates with `FILTER`, follow-up set (Option B), value by status
       (always 4 rows), top 5 — reusing INV-002 filters — _AC1–AC5, AC7, AC8_
- [x] 2. `GET /api/invoices/dashboard` + schemas, including `links` and `has_data=false` — _AC5, AC6, AC9_
- [x] 3. API tests with fixed `today`, including "each card's link returns exactly its number" — _AC1–AC9_

## B. Frontend

- [x] 4. `InvoiceDashboardPage`: week line, 3 KPI cards linking via `links` — _AC1–AC4, AC6_
- [x] 5. Top 5 to follow up list + "see all" link — _AC7_
- [x] 6. Value-by-status bar table (CSS bars on status tokens, table semantics) — _AC8_
- [x] 7. Empty state + loading skeletons — _AC9_
- [x] 8. Home: invoice section shows 3 headline KPIs from the same endpoint (completes PLT-001 AC5)
- [x] 9. Replace the `/invoices/dashboard` ComingSoon route; Vitest tests.

## C. Verify

- [x] 10. Playwright: after the sample upload, the dashboard numbers match the lists behind each
        card; empty state on a fresh database is covered by the API/unit tests; axe.
- [x] 11. Set statuses to `implemented`; update module.md and the PLT-001 AC5 note.

## Verification (2026-09-25)

- invoice-service: 132 tests passed (fixed "today" = 25 Sep 2026); ruff check/format clean.
- Frontend: 97 unit tests passed; typecheck, ESLint, design-token check clean.
- End to end: 44 Playwright tests passed, including: each dashboard card's number equals the
  list it opens; follow-up includes invoices overdue before the week; the table fits 1280px;
  axe on list and dashboard. `scripts/e2e.sh` regenerates the date-relative samples first.
