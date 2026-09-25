---
id: CON-003
title: Contract dashboard — tasks
status: implemented
design: ./design.md
---

# CON-003 — Tasks

Branch: shared with CON-001 / CON-002, after CON-002 tasks 1–3.

## A. Backend

- [x] 1. `dashboard_queries.py`: counts (completed only), at-risk breakdown, by lifecycle,
       needs attention (top 5), unread counts, links — all via CON-002 filters — _AC1–AC6_
- [x] 2. `GET /api/contracts/dashboard` (+ `has_data=false`) — _AC2, AC7, AC8_
- [x] 3. API tests, including "each card's link returns exactly its number" — _AC1–AC8_

## B. Frontend

- [x] 4. Refactor invoices' `ValueByStatus` into a shared `StatusBars` (amount or count mode);
       invoice tests stay green.
- [x] 5. `ContractDashboardPage`: "Figures as of", unread note, 5 KPI cards, Needs review group,
       Needs attention list, status bars, empty state — _AC1–AC8_
- [x] 6. Home: contract KPIs (In force · At risk · Expired) — completes PLT-001 AC5.
- [x] 7. Replace the ComingSoon route; Vitest.

## C. Verify

- [x] 8. Playwright: card numbers equal the lists they open; Home shows both modules; axe.
- [x] 9. Set statuses to `implemented`; update module.md and the PLT-001 note.

## Verification (2026-09-25)

- contract-service: 107 tests passed (fake/scripted extractor; fixed today = 25 Sep 2026) plus
  2 opt-in live tests against Claude Sonnet 5 on the sample contracts (both passed; all 34
  quotes verified verbatim). ruff check/format clean; `app/core` identical in both services.
- Frontend: 112 unit tests passed; typecheck, ESLint, design-token check clean.
- End to end: 52 Playwright tests passed (8 contract tests), 0 real AI calls during the run.
- The two sample contracts were uploaded and read by the real AI into the demo data.
