---
id: CON-003
title: Contract dashboard — tasks
status: approved
design: ./design.md
---

# CON-003 — Tasks

Branch: shared with CON-001 / CON-002, after CON-002 tasks 1–3.

## A. Backend

- [ ] 1. `dashboard_queries.py`: counts (completed only), at-risk breakdown, by lifecycle,
       needs attention (top 5), unread counts, links — all via CON-002 filters — _AC1–AC6_
- [ ] 2. `GET /api/contracts/dashboard` (+ `has_data=false`) — _AC2, AC7, AC8_
- [ ] 3. API tests, including "each card's link returns exactly its number" — _AC1–AC8_

## B. Frontend

- [ ] 4. Refactor invoices' `ValueByStatus` into a shared `StatusBars` (amount or count mode);
       invoice tests stay green.
- [ ] 5. `ContractDashboardPage`: "Figures as of", unread note, 5 KPI cards, Needs review group,
       Needs attention list, status bars, empty state — _AC1–AC8_
- [ ] 6. Home: contract KPIs (In force · At risk · Expired) — completes PLT-001 AC5.
- [ ] 7. Replace the ComingSoon route; Vitest.

## C. Verify

- [ ] 8. Playwright: card numbers equal the lists they open; Home shows both modules; axe.
- [ ] 9. Set statuses to `implemented`; update module.md and the PLT-001 note.
