---
id: CON-002
title: Contract list and detail — tasks
status: approved
design: ./design.md
---

# CON-002 — Tasks

Branch: shared with CON-001 / CON-003.

## A. Backend

- [ ] 1. `clock.py` + `contract_status.py`: lifecycle and at-risk as SQL CASE expressions +
       Python twin, reason texts; boundary unit tests — _AC4_
- [ ] 2. `contract_queries.py`: views, search (title / party / file name), counts, sorts with
       nulls last, paging — _AC1–AC3_
- [ ] 3. `GET /api/contracts`, `GET /{id}` (ordered sections), `GET /{id}/file` — _AC1–AC8_
- [ ] 4. API tests with a fixed today and seeded contracts (via the fake extractor or direct
       inserts).

## B. Frontend

- [ ] 5. `api.ts`, `query.ts` (URL state), `status.ts` (badges, reasons, end hints)
- [ ] 6. `ContractsPage`: tabs with counts, search, being-read note, 6-column table, sorting,
       paging, empty states — _AC1–AC3, AC9_
- [ ] 7. `ContractDetailPage`: header + download, AI notice, status, summary, parties, key dates,
       risks (High → Low), terms by category, quotes with the unverified note, date-sanity
       note — _AC4–AC7_
- [ ] 8. Processing card (poll every 2 s, swap in place, focus h1) and failed state with Try
       again — _AC8_
- [ ] 9. Replace the ComingSoon routes; Vitest.

## C. Verify

- [ ] 10. Playwright: list fits 1280px; filters/sort in URL; detail sections; download; axe.
- [ ] 11. Set statuses to `implemented`.
