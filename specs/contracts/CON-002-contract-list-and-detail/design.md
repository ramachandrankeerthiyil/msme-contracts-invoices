---
id: CON-002
title: Contract list and detail — design
status: implemented
requirements: ./requirements.md
---

# CON-002 — Design

## Overview

The contract list and detail pages follow the same pattern as the invoice list (INV-002).
Statuses are **computed per request against today** (Asia/Kolkata) in contract-service, all list
state lives in the URL, and the same filter code later powers the dashboard (CON-003).

## Status rules (module.md, implemented once in `app/domain/contract_status.py`)

**Lifecycle**, evaluated in this order:

| Order | Condition | Lifecycle | Badge |
|---|---|---|---|
| 1 | `processing_status` ∈ uploaded / extracting_text / analysing | `processing`: "Being read" | neutral |
| 2 | `processing_status = failed` | `failed`: "Could not be read" | danger |
| 3 | `start_date > today` | `not_started`: "Not yet started" | neutral |
| 4 | `end_date` is null | `no_end_date`: "No end date" | info |
| 5 | `end_date < today` | `expired`: "Expired" | danger |
| 6 | otherwise | `in_force`: "In force" | success |

(A missing start date counts as started, per module.md.)

**At risk** (completed contracts only, never expired). This is a flag on top of the lifecycle:
- **Expiring soon:** `today ≤ end_date ≤ today + CONTRACT_AT_RISK_DAYS` (3). Reason text:
  "Expires today", "Expires in 1 day", "Expires in 3 days".
- **High risks:** at least 1 risk with severity `high`. Reason text: "1 high risk", "2 high risks".

Both can apply; the badge shows the reasons joined by " · ". Implementation: an SQL CASE
expression plus a `high_risk_count` subquery, with a Python twin kept in step by unit tests,
exactly like INV-002's `invoice_status.py`.

## API

### `GET /api/contracts`

| Param | Values | Default |
|---|---|---|
| `view` | `all` (every **read** contract), `in_force`, `at_risk`, `not_started`, `expired`, `no_end_date`, `processing`, `failed` | `all` |
| `q` | case-insensitive contains on title, **or any party name**, or file name | — |
| `sort` | `end_date`, `start_date`, `title`, `status`, `high_risks`, `uploaded_at` | `end_date` |
| `order` | `asc` / `desc` (nulls always last) | `asc` |
| `page`, `page_size` | ≤ 100 | 1, 25 |

- **"All" means every contract that has been read** (`completed`). Contracts still being read, or
  that failed, have their own tabs. This keeps "All" equal to the dashboard's **Total contracts**
  (CON-003 AC2/AC3).
- The response has the same shape as the invoice list: `{today, items, total, page, page_size,
  counts}`. `counts` holds per-view counts that respect `q` but not `view`.
- Each item: `id`, `title` (falls back to the file name while unread), `file_name`, `parties`
  (list of names), `start_date`, `end_date`, `days_until_end`, `lifecycle`, `at_risk` (bool),
  `at_risk_reasons` (list of strings), `high_risk_count`, `uploaded_at`, `processing_status`.

### `GET /api/contracts/{id}`

The full detail: every contract field above, plus `summary`, `parties[{name, role}]`,
`key_dates[{label, date, days_from_today, source_text, source_verified}]` sorted by date,
`terms[{category, summary, source_text, source_verified}]` grouped in the fixed category order,
`risks[…]` ordered high → medium → low, and `processing_status`, `error_message`,
`extraction_model`, `processed_at`. Unknown id → 404.

### `GET /api/contracts/{id}/file` (AC7)

Streams the stored original with its real content type and
`Content-Disposition: attachment; filename="<original name>"`.

## UI — `/contracts` ("All contracts")

The layout matches the invoice list, for consistency:
- **Tabs** with counts: All · In force · At risk · Not yet started · Expired · No end date ·
  Being read · Could not be read (AC2).
- **Search:** "Search contract title or party" (AC2).
- **A note** when anything is still being read: "2 contracts are still being read", linking to
  that tab.
- **Table (AC1): 6 columns, so it fits a laptop screen:**

| Column | Content |
|---|---|
| Contract | **Title** (link to detail), with the parties beneath ("Kaveri Agro Foods · Bluewave Logistics LLP") |
| Start | date or "—" |
| End | date, with a hint beneath: "in 12 days" / "ends today" / "ended 3 days ago" / "No end date" |
| Status | lifecycle badge; an **At risk** warning badge with its reasons beneath when flagged |
| High risks | count, right-aligned, shown red when > 0 |
| Uploaded | date |

- **Sorting (AC3):** every column except the combined parties line sorts. Default: end date
  soonest first, with contracts without an end date last.
- **Empty (AC9):** "No contracts yet" with an **Upload contract** button. A filter that matches
  nothing shows "No contracts match…" with **Clear filters**.

## UI — `/contracts/:id` (detail)

```
Contracts › All contracts › Master Services Agreement
Master Services Agreement                                   [ ⬇ Download original ]
[✔ In force] [⚠ At risk: Expires in 2 days · 3 high risks]
┌ ⓘ Extracted by AI — please check against the original document. ──────────────┐
Summary ……………………………………………………………… (plain paragraph)

Parties                               Key dates
 Kaveri Agro Foods — Client            1 Oct 2025  Start                 "…commences on 1 October 2025…"
 Bluewave Logistics LLP — Provider     26 Sep 2026 End · in 2 days ⚠     "…in force until 26 September…"
                                       28 Jun 2026 Notice deadline · 90 days ago

Risks  (3 high · 2 medium · 1 low)
 HIGH ─ Unlimited indemnity
        You must cover all the provider's losses, without limit.
        From the contract: "The Client shall indemnify the Service Provider against all losses…"
 …
Terms
 Payment · Termination · Renewal · Liability · Confidentiality · Governing law · Other
File: contract-msa-bluewave.docx · uploaded 25 Sep 2026 · read by claude-sonnet-5 on 25 Sep 2026
```

| Element | Behaviour |
|---|---|
| Header (AC5, AC7) | The contract title is the h1 and the last breadcrumb. **Download original** is the primary action (a link to `/file`). |
| AI notice (AC7) | An info banner at the top, always shown on completed contracts |
| Status (AC4) | Lifecycle badge plus the at-risk badge with its reasons |
| Parties, key dates (AC5) | Key dates are listed in date order with the relative hint ("in N days" / "N days ago"). Dates within the at-risk window get a warning icon. |
| Risks (AC5) | Grouped **High → Medium → Low** with count chips. Each risk shows title, "why it matters", and the quote. |
| Terms (AC5) | Grouped by category in a fixed order; empty categories are hidden |
| Quotes (AC6) | Shown in a quote block, "From the contract: “…”". If `source_verified = false`, a muted note is added: "We couldn't find this exact wording in the file — please check the original." |
| Date sanity | If end < start, a warning note: "Please check these dates against the original." |
| **Processing (CON-001 AC8)** | Instead of the content: a progress card with three steps (Uploaded ✓ · Reading the document · Finding parties, dates, terms and risks), the active step spinning, and "This usually takes under a minute. You can leave this page — we'll keep going." The page polls every 2 s; when complete, the content replaces the card in place and focus moves to the h1 (announced politely). |
| **Failed (AC8, CON-001 AC9)** | `ErrorAlert` with the stored user-facing message and a **Try again** button (POST retry → back to processing). **Download original** stays available. |
| Not found | "We couldn't find that contract", with a link to All contracts |

## Code structure

```
contract-service
  app/domain/clock.py, contract_status.py      # like invoice-service (duplicated on purpose, per service)
  app/db/contract_queries.py                   # filters, counts, sort, paging — shared with CON-003
  app/api/contracts.py                         # GET /, GET /{id}, GET /{id}/file
frontend/src/modules/contracts/
  api.ts, query.ts, status.ts                  # URL state + badge/label mapping
  pages/ContractsPage.tsx, ContractDetailPage.tsx
  components/ContractTable.tsx, ContractTabs.tsx, ProcessingCard.tsx, RiskList.tsx,
             TermList.tsx, KeyDates.tsx, Quote.tsx
```

## Testing

| AC | Tests |
|---|---|
| AC1–AC3 | API (fixed today): columns, every view's membership and counts, search by party, sorts with nulls last. Vitest: table, tabs, URL state. Playwright: fits 1280px, sort + Back. |
| AC4 | Unit: lifecycle/at-risk boundaries (end = today+3 → at risk; today+4 → not; expired never at risk; high risk alone → at risk). SQL vs Python agree. |
| AC5–AC7 | API: detail ordering (dates by date, risks high → low, terms by category). Vitest: sections, quotes, unverified note, AI notice, download link. |
| AC8 | Vitest: processing card polls and swaps to content; failed shows the message + Try again. Playwright with the fake extractor. |
| AC9 | Vitest + API: empty states |

## As built (2026-09-25)

- **Sort by status:** ties are broken by the soonest end date (like the invoice list).
- **Shared UI parts:** `FilterTabs`, `SearchField`, `SortableTh` and `StatusBars` were extracted
  into `components/` and are now used by both the invoice and contract lists.
