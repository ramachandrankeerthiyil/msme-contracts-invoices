---
id: CON-003
title: Contract dashboard — design
status: implemented
requirements: ./requirements.md
---

# CON-003 — Design

## Overview

This feature mirrors the invoice dashboard (INV-003). `GET /api/contracts/dashboard` computes
every number in contract-service from the **same filter code as the list** (CON-002). Each card
carries the list filter behind it, so a number and the list it opens always match (AC3).

## API — `GET /api/contracts/dashboard`

```json
{
  "today": "2026-09-25",
  "has_data": true,
  "counts": { "total": 2, "in_force": 2, "at_risk": 1, "expired": 0, "not_started": 0, "no_end_date": 0 },
  "at_risk_breakdown": { "expiring_soon": 1, "high_risk": 1 },
  "by_lifecycle": [
    { "lifecycle": "in_force", "count": 2 }, { "lifecycle": "not_started", "count": 0 },
    { "lifecycle": "no_end_date", "count": 0 }, { "lifecycle": "expired", "count": 0 }
  ],
  "needs_attention": [
    { "id": "…", "title": "Master Services Agreement", "parties": ["Kaveri Agro Foods", "Bluewave Logistics LLP"],
      "end_date": "2026-09-26", "days_until_end": 1, "lifecycle": "in_force",
      "at_risk": true, "at_risk_reasons": ["Expires in 1 day", "3 high risks"] }
  ],
  "unread": { "processing": 0, "failed": 0 },
  "links": {
    "total": { "view": "all" }, "in_force": { "view": "in_force" }, "at_risk": { "view": "at_risk" },
    "expired": { "view": "expired" }, "not_started": { "view": "not_started" },
    "no_end_date": { "view": "no_end_date" }, "processing": { "view": "processing" }, "failed": { "view": "failed" }
  }
}
```

- **Totals (AC2):** `total` counts only contracts with `processing_status = completed`.
  In force + not started + no end date + expired = total. At risk overlaps them.
- **At-risk breakdown (AC1a):** a contract can be both expiring soon and high-risk, so the two
  numbers may add up to more than `at_risk`. The card wording ("1 expiring soon · 1 with high
  risks") makes that natural.
- **Needs attention (AC4):** up to 5. At-risk contracts come first, ordered by end date (soonest
  first, no end date last). Then non-expired contracts with the soonest end dates.
- **No contracts at all** (read or not): `{"today": "…", "has_data": false}` (AC7). If
  contracts exist but none has been read yet, `has_data` is true and the unread note explains it.

## UI — `/contracts/dashboard`

```
Contracts › Dashboard
Contract dashboard                                        [ ⬆ Upload contract ]
Figures as of 25 Sep 2026                                                    (AC8)
ⓘ 1 contract is still being read · 1 contract could not be read  →          (AC6, only when > 0)
┌ Total contracts ┐ ┌ In force ┐ ┌ At risk            ⚠ ┐ ┌ Expired ┐ ┌ Not yet started ┐
│ 2               │ │ 2        │ │ 1                    │ │ 0       │ │ 0               │
│ read so far     │ │          │ │ 1 expiring soon ·    │ │         │ │                 │
│                 │ │          │ │ 1 with high risks    │ │         │ │                 │
Needs review
┌ No end date                                      ⓘ ┐
│ 0 — contracts with no end date found; check they are still wanted │
Needs attention (top 5)                       Contracts by status
 ⚠ Master Services Agreement   ends in 1 day    ✔ In force         ██████ 2
   Kaveri Agro Foods · Bluewave  Expires in 1… ⏱ Not yet started  ░░░░░░ 0
                                               ⓘ No end date      ░░░░░░ 0
                                               ⛔ Expired          ░░░░░░ 0
```

| Element | Behaviour |
|---|---|
| "Figures as of" (AC8) | `today` from the API, formatted "25 Sep 2026" |
| Unread note (AC6) | An info banner, shown only when there are processing or failed contracts. It gives the counts in plain words, with links to the Being read / Could not be read tabs. |
| KPI cards (AC1, AC1a, AC3) | Five `KpiCard`s in a container-query grid, like INV-003. At risk uses the warning variant when > 0, Expired the danger variant when > 0. Each links via `links` to the list. |
| Needs review group (AC1) | Its own heading **Needs review**, with the **No end date** card (info variant) and the hint "Contracts with no end date found — check they are still wanted". |
| Needs attention (AC4) | Like the invoice dashboard's top-5 list: status icon, title, parties, end hint, and at-risk reasons. Each links to the contract's detail page. If the list is empty: "Nothing needs attention right now." |
| By status (AC5) | The same accessible bar-table pattern as INV-003 (`ValueByStatus`), showing counts instead of amounts. It becomes a small shared component, `StatusBars`. |
| Empty (AC7) | "No contracts yet", with an **Upload contract** button, instead of zero cards |

### Home (completes PLT-001 AC5)

The Contracts section on Home shows three headline cards, **In force · At risk · Expired**, from
the same endpoint. It shows the empty state when `has_data = false`, and loads and fails
independently of the Invoices section.

## Code structure

```
contract-service: app/db/dashboard_queries.py, app/api/contracts.py (+ GET /dashboard)
frontend: modules/contracts/pages/ContractDashboardPage.tsx,
          components/ContractKpis.tsx, NeedsAttention.tsx, ContractsOverview.tsx (Home),
          components/common/StatusBars.tsx (refactored from invoices' ValueByStatus)
```

## Testing

| AC | Tests |
|---|---|
| AC1, AC1a, AC2 | API (fixed today): counts only completed contracts; lifecycle partition sums to total; the breakdown counts overlapping contracts in both |
| AC3 | API: for every card, `GET /api/contracts` with its link returns exactly its number. Playwright: click-through equality. |
| AC4 | API: at risk first, then soonest end; limit 5; expired excluded |
| AC5 | Vitest: bar table rows and accessible names |
| AC6 | API + Vitest: unread note only when processing/failed > 0, with correct links |
| AC7 | API `has_data=false`; Vitest empty state |
| AC8 | Vitest: "Figures as of" uses the API's `today` |
| PLT-001 AC5 | Vitest + Playwright: Home shows the contract KPIs |
