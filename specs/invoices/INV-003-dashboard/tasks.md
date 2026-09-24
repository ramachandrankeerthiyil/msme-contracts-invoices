---
id: INV-003
title: Invoice dashboard — tasks
status: approved
design: ./design.md
---

# INV-003 — Tasks

Branch: shared with INV-002 (`feat/INV-002-INV-003-invoice-list-dashboard`), after INV-002 tasks 1–4.

## A. Backend

- [ ] 1. `dashboard_queries.py`: anchor U (latest completed upload, IST date), week bounds,
       aggregates with `FILTER`, follow-up set (Option B), value by status
       (always 4 rows), top 5 — reusing INV-002 filters — _AC1–AC5, AC7, AC8_
- [ ] 2. `GET /api/invoices/dashboard` + schemas, including `links` and `has_data=false` — _AC5, AC6, AC9_
- [ ] 3. API tests with fixed `today`, including "each card's link returns exactly its number" — _AC1–AC9_

## B. Frontend

- [ ] 4. `InvoiceDashboardPage`: week line, 3 KPI cards linking via `links` — _AC1–AC4, AC6_
- [ ] 5. Top 5 to follow up list + "see all" link — _AC7_
- [ ] 6. Value-by-status bar table (CSS bars on status tokens, table semantics) — _AC8_
- [ ] 7. Empty state + loading skeletons — _AC9_
- [ ] 8. Home: invoice section shows 3 headline KPIs from the same endpoint (completes PLT-001 AC5)
- [ ] 9. Replace the `/invoices/dashboard` ComingSoon route; Vitest tests.

## C. Verify

- [ ] 10. Playwright: after the sample upload, the dashboard numbers match the lists behind each
        card; empty state on a fresh database is covered by the API/unit tests; axe.
- [ ] 11. Set statuses to `implemented`; update module.md and the PLT-001 AC5 note.
