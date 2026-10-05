---
id: INV-002
title: Invoice list with status flags — design
status: implemented
requirements: ./requirements.md
---

# INV-002 — Design

## Overview

```
InvoicesPage (/invoices?view=follow_up&q=acme&sort=due_date&order=asc&page=2)
   │  URL search params are the only UI state (AC7)
   ▼
GET /api/invoices?…        ──► invoice-service
                                 status computed in SQL relative to "today" (Asia/Kolkata) (AC2)
                                 filter · count per view · total amount · sort · page
   ◄── { items, total, total_amount, counts, today, … }
GET /api/invoices/export?… ──► same filters, all rows, .xlsx (AC9)
```

Payment status is **never stored**. It is a SQL `CASE` expression evaluated per request against
today's date, so an invoice becomes "At risk" or "Outstanding" as days pass without re-uploading.

## "Today"

`app/domain/clock.py` provides a FastAPI dependency, `get_today()`, which returns the current date
in `APP_TIMEZONE`. Every endpoint that computes statuses takes `today` from this dependency. Tests
override it through `app.dependency_overrides` to pin the date. The date used is echoed in every
response (`today`), so the UI never relies on the browser's clock.

## Status expression (module.md "Payment status")

```sql
CASE
  WHEN paid_date IS NOT NULL             THEN 'paid'
  WHEN due_date <  :today                THEN 'outstanding'
  WHEN due_date <= :today + :at_risk_days THEN 'at_risk'      -- INVOICE_AT_RISK_DAYS, default 5
  ELSE 'open'
END
```

- **Status rank** (used for the default sort and for sorting by status): outstanding 0, at_risk 1,
  open 2, paid 3.
- **Views** (the tabs): `follow_up` = outstanding + at_risk, plus `outstanding`, `at_risk`,
  `open`, `paid` and `all`.
- `days_until_due` = `due_date − today`. It is negative when overdue and `null` when paid.

The expression lives in `app/domain/invoice_status.py`, where one function builds the SQLAlchemy
expression and another computes the same rule in Python. A unit test checks both agree for every
boundary.

## API

### `GET /api/invoices`

| Param | Values | Default |
|---|---|---|
| `view` | `follow_up`, `outstanding`, `at_risk`, `open`, `paid`, `all` | `follow_up` |
| `q` | text; case-insensitive *contains* match on invoice number or customer name | — |
| `updated` | `true` → only `record_status = 'updated'` | — |
| `due_from`, `due_to` | ISO dates, inclusive (used by dashboard links, INV-003) | — |
| `sort` | `status`, `invoice_number`, `customer_name`, `date_raised`, `due_date`, `amount`, `paid_date` | `status` |
| `order` | `asc`, `desc` | `asc` |
| `page`, `page_size` | ≥ 1; `page_size` ≤ 100 | 1, 25 |

- **Default order (AC4):** `sort=status&order=asc` sorts by status rank, then `due_date` ascending,
  then `invoice_number`. That puts outstanding invoices first, most overdue at the top, then at-risk
  invoices, soonest due first. Every other sort uses `invoice_number` as a tie-breaker, so paging
  is stable.
- Invalid parameters return the standard 422 `VALIDATION_ERROR`.

**200**
```json
{
  "today": "2026-09-25",
  "items": [
    {
      "id": "…", "invoice_number": "INV-2606", "customer_name": "Deccan Printing Works",
      "date_raised": "2026-07-16", "due_date": "2026-08-15", "amount": "125000.00",
      "paid_date": null, "status": "outstanding", "days_until_due": -41,
      "record_status": "new", "record_updated_at": null,
      "customer_email": "accounts@deccanprinting.example", "can_remind": true,
      "last_reminder_at": null
    }
  ],
  "total": 9, "page": 1, "page_size": 25,
  "total_amount": "994150.75",
  "counts": { "follow_up": 9, "outstanding": 5, "at_risk": 4, "open": 3, "paid": 5, "all": 17 }
}
```
- `customer_email`, `can_remind` and `last_reminder_at` support the email reminder (INV-004):
  the address on file (or `null`), whether the invoice may be reminded (true when Outstanding),
  and the time of the latest reminder (or `null`). They do not affect filters or sorting.
- `total` and `total_amount` cover **every row matching the filters**, not just the current page
  (AC6).
- `counts` apply `q`, `updated` and the due-date range, but **not** `view`. That way each tab's
  count shows what that tab would contain (AC3).

### `GET /api/invoices/export`

Takes the same filter and sort parameters, without paging. It returns
`invoices-<today>.xlsx` (`Content-Disposition: attachment`) with these columns: Invoice Number,
Customer Name, Date Raised, Due Date, Amount, Paid Date, Status, Due, Record status. Dates and
amounts are formatted as in the template. The header row is frozen. Export is capped at 20,000
rows, the same as the upload limit.

## Code structure (invoice-service)

```
app/domain/clock.py            # get_today() dependency
app/domain/invoice_status.py   # status CASE expr, rank, views, python twin
app/db/invoice_queries.py      # build filtered query, counts, total, page
app/domain/export.py           # xlsx writer for the current view
app/api/invoices.py            # GET /  and GET /export
app/api/schemas.py             # + InvoiceItem, InvoicePage, ViewCounts
```

The `/uploads`, `/template`, `/dashboard` and `/export` routes are registered **before** any
`/{id}`-style route, so they can never be captured by a path parameter.

## UI — `/invoices` ("All invoices")

```
Invoices › All invoices
All invoices                                            [ ⬆ Upload invoices ]
────────────────────────────────────────────────────────────────────────────
[ Needs follow-up 9 ] [ Outstanding 5 ] [ At risk 4 ] [ Open 3 ] [ Paid 5 ] [ All 17 ]

 🔍 Search invoice number or customer [__________]   ☐ Only updated invoices   [ ⬇ Export ]
 Due 24 Sep – 30 Sep 2026  [✕ Clear]            ← only when due_from/due_to are set

 Total: ₹9,94,150.75 across 9 invoices

 Invoice ▲▼ | Customer | Raised | Due              | Amount    | Paid | Status        | Record
 INV-2606   | Deccan…  | 16 Jul | 15 Aug 2026      | ₹1,25,000 |  —   | ⛔ Outstanding | New
            |          |        | 41 days overdue  |           |      |               |
 …
 Showing 1–9 of 9                                              [‹ Previous] [Next ›]
```

| Element | Behaviour |
|---|---|
| **Tabs (AC3)** | A `nav` labelled "Filter by status" containing links, with `aria-current="page"` on the active one. Each shows its count from `counts`. They are 48px tall, with an icon + label + count. Switching tabs resets `page`. |
| **Search (AC5)** | A labelled input ("Search invoice number or customer"). The URL updates 300ms after typing stops, and pressing Enter applies it immediately. A clear (✕) button appears when there is text. |
| **Updated only (AC5)** | A checkbox, "Only show updated invoices", mapped to `updated=true`. |
| **Due range chip** | Shown when `due_from`/`due_to` are set (from dashboard links), as "Due 24 Sep – 30 Sep 2026", with a "Clear" button. |
| **Total (AC6)** | "Total: ₹X across N invoices", using `total_amount` and `total`. |
| **Table (AC1, AC1a)** | Built from the `Table` primitives. The Due column shows the date with the due hint underneath: "due in 3 days" / "due today" / "12 days overdue", or "paid on 20 Sep 2026" when paid. The Status column shows a `StatusBadge` (Paid → success, Outstanding → danger, At risk → warning, Open → neutral). Record shows "New" as plain muted text, or an info badge "Updated on 24 Sep 2026". Amount is right-aligned in INR. |
| **Sorting (AC4)** | Each sortable header is a `<button>` inside the `<th>`. The `<th>` carries `aria-sort`, and a visible ▲/▼ arrow shows the direction. Clicking the active column flips the order; clicking another column sorts it ascending. The Status column sorts by rank. |
| **Paging** | "Showing 1–25 of 140" with Previous/Next buttons (disabled at either end). Both update `page` in the URL. |
| **Export (AC9)** | A secondary button linking to `/api/invoices/export?<current filters>` with the `download` attribute. |
| **Loading** | Skeleton rows on first load. On later filter changes the previous rows stay visible, dimmed, until the new data arrives, so the page doesn't jump. |
| **Empty (AC8)** | If `counts.all = 0` and no filters are set: an `EmptyState` saying "No invoices yet" with an **Upload invoices** button. If filters match nothing: "No invoices match these filters" with a **Clear filters** button, which resets `q`, `updated`, the due range and `view=all`. |

All state lives in URL search params (AC7), so Back and Forward restore the exact view. Defaults
are omitted from the URL to keep it short.

### As built: table fits a laptop screen

The 8-column table was 168px wider than a 1280px laptop's content area, which forced sideways
scrolling and hid Status and Record. It now has **6 columns**: Invoice (number, with "Raised <date>"
beneath), Customer, Due (date + hint; paid invoices show "paid on <date>"), Amount, Status,
Record. Every field from AC1 is still shown. Sortable columns: Invoice, Customer, Due, Amount,
Status (the API still accepts `date_raised` / `paid_date` sorts). A Playwright test checks
that the table fits at 1280px.

**INV-004 adds a Reminder column** (the "Send email reminder" button and "Last reminder sent
<date>"), described in `INV-004-email-reminder/design.md`. Seven columns overflowed a 1280px screen
by 83px, so the **Record status moved under the invoice number** (below "Raised <date>"); the table
is again six columns: Invoice, Customer, Due, Amount, Status, Reminder. The Playwright fit test
keeps guarding it.

## Observability

No new log events; access logs cover reads. Export logs `invoice_export.completed` with
`rows` (a count only).

## Edge cases

| Case | Behaviour |
|---|---|
| Invoice due today, unpaid | At risk, hint "due today" |
| Invoice paid after its due date | Paid (payment status ignores lateness) |
| `page` beyond the last page | Empty `items` with the correct `total`; UI shows "No invoices on this page" and a link to page 1 |
| Search with `%` or `_` | Escaped, so it is treated literally |
| `due_from` > `due_to` | 422 `VALIDATION_ERROR` |

## Testing

| AC | Tests |
|---|---|
| AC2 | Unit: SQL expression vs Python twin at boundaries (today−1, today, today+5, today+6, paid) |
| AC3 | API: counts per view with a fixed `today`; counts respect `q` / `updated`, not `view` |
| AC4 | API: default order = outstanding (most overdue first) → at risk (soonest first) → …; each sort key asc/desc with a stable tie-breaker |
| AC5 | API: `q` matches number or customer, case-insensitive; `updated=true` |
| AC6 | API: `total_amount` sums all filtered rows across pages |
| AC9 | API: export rows = filtered rows; headers; statuses |
| AC1, AC1a, AC3–AC8 | Vitest: page renders badges, hints and record status; tab/search/sort/paging update the URL; empty states |
| AC7 | Playwright: bookmark a filtered URL, reload, and Back restores the view |
| All | Playwright: with the sample data, the Needs follow-up tab shows outstanding before at-risk, and export downloads; axe on the page |
