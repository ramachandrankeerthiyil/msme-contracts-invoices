---
id: INV-003
title: Invoice dashboard — design
status: implemented
requirements: ./requirements.md
---

# INV-003 — Design

## Overview

```
InvoiceDashboardPage ──► GET /api/invoices/dashboard ──► invoice-service
                                                           anchor U = latest 'completed' upload date (IST)
                                                           week = [U, U+6]; today = get_today()
                                                           aggregates in one SQL round trip
KPI card click ──► /invoices?view=…&due_from=…&due_to=…   (INV-002 list, same filters as the SQL)
Home (PLT-001 AC5) ──► same endpoint, 3 headline cards
```

It reuses INV-002's status expression, `get_today()` and list filters. A dashboard number and the
list it links to are **computed by the same filter code**, so they can never disagree (AC6).

## Definitions

- **U (anchor):** the date, in Asia/Kolkata, of the most recent `invoice_uploads` row with
  `status = 'completed'` (module.md "Current week").
- **Current week:** `[U, U + 6 days]`, inclusive.
- **In the current week:** `U ≤ due_date ≤ U + 6` (AC5, product decision: Due Date).
- **Value this week (AC2):** sum of `amount` for invoices in the current week, whatever their status.
- **Invoices this week (AC3):** count of the same invoices.

### Need follow-up this week (AC4): decided, Option B

Read literally, AC4 counts invoices that are **in the current week _and_ (Outstanding or At risk)**.
Because the week starts on the upload date, **invoices that were already overdue at upload fall
before the week and are never counted**. On upload day this card would show only at-risk
invoices, and it would miss the most urgent ones: a customer 40 days late would not appear.

| Option | Rule | With today's sample data (uploaded 24 Sep, viewed 25 Sep) |
|---|---|---|
| **A: literal** | due in `[U, U+6]` **and** status ∈ {outstanding, at_risk} | 5: INV-2610 (due 24 Sep, now 1 day overdue) + 4 at risk |
| **B: recommended** | status ∈ {outstanding, at_risk} **and** `due_date ≤ U + 6`. That is: everything overdue so far (including carried over from before the week) plus everything at risk that is due by the end of the week. | 9: 4 overdue from before the week + INV-2610 + 4 at risk |

Option B matches the brief's wording ("invoices that are at risk or unpaid") and the purpose of the
card: *who do I need to chase this week?* The breakdown line makes the carry-over explicit, e.g.
"5 outstanding · 4 at risk". **Decision (product owner, 2026-09-25): Option B.** It is exactly
the list filter `view=follow_up&due_to=<U+6>`.

## API — `GET /api/invoices/dashboard`

**200, when there is data**
```json
{
  "today": "2026-09-25",
  "has_data": true,
  "week": { "start": "2026-09-24", "end": "2026-09-30", "anchor_uploaded_at": "2026-09-24T17:11:02Z" },
  "value_this_week": "557250.00",
  "invoices_this_week": 6,
  "follow_up": { "total": 9, "outstanding": 5, "at_risk": 4 },
  "value_by_status": [
    { "status": "outstanding", "amount": "142000.00", "count": 1 },
    { "status": "at_risk",     "amount": "396750.00", "count": 4 },
    { "status": "open",        "amount": "0.00",      "count": 0 },
    { "status": "paid",        "amount": "18500.00",  "count": 1 }
  ],
  "top_follow_up": [
    { "id": "…", "invoice_number": "INV-2606", "customer_name": "Deccan Printing Works",
      "amount": "125000.00", "due_date": "2026-08-15", "days_until_due": -41, "status": "outstanding" }
  ],
  "links": {
    "this_week": { "view": "all", "due_from": "2026-09-24", "due_to": "2026-09-30" },
    "follow_up": { "view": "follow_up", "due_to": "2026-09-30" }
  }
}
```
- `value_by_status` always lists all four statuses in rank order, including zeros, so the chart is stable.
- `top_follow_up` holds up to 5 invoices from the follow-up set, sorted by status rank then
  `due_date` ascending (most overdue first) (AC7).
- `links` holds the exact list filters behind each card. The UI turns them into `/invoices?…` URLs
  and never rebuilds the rules itself (AC6).
- **No completed upload yet:** `{"today": "…", "has_data": false}` only (AC9).

## Code structure

```
app/db/dashboard_queries.py    # anchor, week aggregates, follow-up set, top 5 — reuses invoice_queries filters
app/api/dashboard.py           # GET /dashboard
app/api/schemas.py             # + Dashboard models
```

All aggregates come from one query using `FILTER (WHERE …)` clauses, plus one query for the top 5.

## UI — `/invoices/dashboard`

```
Invoices › Dashboard
Invoice dashboard                                           [ ⬆ Upload invoices ]
Week of 24 Sep – 30 Sep 2026 (from your upload on 24 Sep)
─────────────────────────────────────────────────────────────────────────────
┌ Total invoice value ─┐ ┌ Invoices this week ──┐ ┌ Need follow-up ───────────┐
│ ₹5,57,250.00         │ │ 6                    │ │ 9                    ⚠    │
│ due this week        │ │ due this week        │ │ 5 outstanding · 4 at risk │
│ View list →          │ │ View list →          │ │ View list →               │
└──────────────────────┘ └──────────────────────┘ └───────────────────────────┘

Top 5 to follow up                        This week's value by status
 ⛔ Deccan Printing Works  ₹1,25,000        ⛔ Outstanding ████░░░░░ ₹1,42,000 · 1
    INV-2606 · 41 days overdue  →          ⚠ At risk     █████████ ₹3,96,750 · 4
 ⛔ Sunrise Pharma …                        ⏱ Open        ░░░░░░░░░ ₹0 · 0
 …                                         ✔ Paid        █░░░░░░░░ ₹18,500 · 1
 See all invoices needing follow-up →
```

| Element | Behaviour |
|---|---|
| **Week line (AC1)** | "Week of {start} – {end} (from your upload on {anchor date})". Short dates, with the year only on the end date. |
| **KPI cards (AC2–AC4, AC6)** | Three `KpiCard`s (PLT-001). The follow-up card uses the warning variant when above 0, and the success variant with the hint "Nothing to chase this week" at 0. Each card links to `/invoices?` + its `links` entry. |
| **Top 5 (AC7)** | An ordered list of links. Each row shows a status icon + customer (bold), the amount (right), and "INV-… · 41 days overdue" beneath. Each links to `/invoices?view=follow_up&q=<invoice_number>`. A footer link, "See all invoices needing follow-up", uses the follow-up filter. If the list is empty: "No invoices need follow-up. Well done." |
| **Value by status (AC8)** | Built as a **table that is also the chart**: each row has a status badge, a horizontal bar (width = share of the week's value, drawn with CSS using the status colour token), the amount and the count. Screen readers get a normal table with a caption. This replaces a Recharts graphic, because with four categories a labelled bar table is clearer for older users and fully accessible without a separate alternative. |
| **Card layout (as built)** | CSS container queries: 1 column in narrow spaces (Home), 2 + 1 medium, and 3 across (3fr 2fr 2fr, value card widest) from 48rem, so ₹ amounts never overflow. |
| **Loading / error** | Card-shaped skeletons, then `QueryBoundary` error with Try again (PLT-001). |
| **Empty (AC9)** | When `has_data = false`: `EmptyState` "No invoices yet" with an **Upload invoices** button. No zero-value cards. |

### Home page (completes PLT-001 AC5)

The Invoices section on Home calls the same endpoint and shows three headline `KpiCard`s (Value
this week · Need follow-up · Invoices this week) with the same links. With `has_data = false` it
keeps today's empty state. The Contracts section is unchanged until CON-003.

## Testing

| AC | Tests |
|---|---|
| AC1 | API: anchor = latest *completed* upload (a later `no_valid_rows` upload is ignored); week bounds |
| AC2, AC3 | API with fixed `today`: value/count include only due dates inside `[U, U+6]`, all statuses |
| AC4 | API: follow-up = Option B set; breakdown sums to total; an invoice overdue from before the week is counted |
| AC5 | API: every number comes from the endpoint |
| AC6 | API: for each card, calling `GET /api/invoices` with its `links` returns exactly that count/total |
| AC7 | API: top 5 order and limit |
| AC8 | API: value_by_status always has 4 entries in rank order; Vitest: bar widths and table semantics |
| AC9 | API: `has_data=false` with no uploads; Vitest: empty state instead of cards |
| PLT-001 AC5 | Vitest: Home shows the 3 invoice KPIs; the invoice section errors independently |
| All | Playwright: after uploading the regenerated sample, dashboard numbers match the list behind each card; axe |

**E2E and dates:** the sample file's dates are relative to the day it is generated, so the e2e
run regenerates `samples/` first (`scripts/e2e.sh`). The expected statuses then hold on any day.
