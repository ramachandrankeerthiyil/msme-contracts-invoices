---
id: CON-002
title: Contract list and detail — tasks
status: implemented
design: ./design.md
---

# CON-002 — Tasks

Branch: shared with CON-001 / CON-003.

## A. Backend

- [x] 1. `clock.py` + `contract_status.py`: lifecycle and at-risk as SQL CASE expressions +
       Python twin, reason texts; boundary unit tests — _AC4_
- [x] 2. `contract_queries.py`: views, search (title / party / file name), counts, sorts with
       nulls last, paging — _AC1–AC3_
- [x] 3. `GET /api/contracts`, `GET /{id}` (ordered sections), `GET /{id}/file` — _AC1–AC8_
- [x] 4. API tests with a fixed today and seeded contracts (via the fake extractor or direct
       inserts).

## B. Frontend

- [x] 5. `api.ts`, `query.ts` (URL state), `status.ts` (badges, reasons, end hints)
- [x] 6. `ContractsPage`: tabs with counts, search, being-read note, 6-column table, sorting,
       paging, empty states — _AC1–AC3, AC9_
- [x] 7. `ContractDetailPage`: header + download, AI notice, status, summary, parties, key dates,
       risks (High → Low), terms by category, quotes with the unverified note, date-sanity
       note — _AC4–AC7_
- [x] 8. Processing card (poll every 2 s, swap in place, focus h1) and failed state with Try
       again — _AC8_
- [x] 9. Replace the ComingSoon routes; Vitest.

## C. Verify

- [x] 10. Playwright: list fits 1280px; filters/sort in URL; detail sections; download; axe.
- [x] 11. Set statuses to `implemented`.

## Verification (2026-09-25)

- contract-service: 107 tests passed (fake/scripted extractor; fixed today = 25 Sep 2026) plus
  2 opt-in live tests against Claude Sonnet 5 on the sample contracts (both passed; all 34
  quotes verified verbatim). ruff check/format clean; `app/core` identical in both services.
- Frontend: 112 unit tests passed; typecheck, ESLint, design-token check clean.
- End to end: 52 Playwright tests passed (8 contract tests), 0 real AI calls during the run.
- The two sample contracts were uploaded and read by the real AI into the demo data.
