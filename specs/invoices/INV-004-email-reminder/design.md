---
id: INV-004
title: Email payment reminder — design
status: implemented
requirements: ./requirements.md
---

# INV-004 — Design

## Overview

```
InvoicesPage → InvoiceTable
   │  row.can_remind (from the service) → "Send email reminder" button
   ▼
ReminderDialog (opened for one invoice)
   │  GET  /api/invoices/{id}/reminder-draft   ──► compose draft from the invoice (nothing is sent)
   │  user reads / edits Subject and Message
   │  POST /api/invoices/{id}/reminders        ──► check still Outstanding + has email
   │        { subject, message }                    send via SMTP  ──► Mailpit (default) / real provider
   │                                                record in invoice_reminders
   ◄── 201 { id, to, sent_at }  →  list is refetched; row shows "Last reminder sent <date>"
```

The page decides nothing. Whether a button appears, who the email goes to, and whether it is still
allowed at send time are all decided by invoice-service (architecture: no business rules in the
UI). Decisions behind the shape of this feature are in **ADR-0004**.

## Data (migration `0002_add_customer_email_and_reminders`)

```
invoices                                 invoice_reminders   (new)
────────                                 ─────────────────
… existing columns …                     id             uuid PK
customer_email   text NULL   (new)        invoice_id     uuid FK → invoices.id  ON DELETE CASCADE
                                          recipient      text         the address the email went to
                                          subject        text
                                          body           text         the message as sent
                                          sent_at        timestamptz
                                          created_at / updated_at
                                         index (invoice_id, sent_at DESC)
```

- `customer_email` comes from the optional **Customer Email** column (INV-001-AC13), stored
  trimmed and lower-case, `NULL` when blank. A later upload row overwrites it like every other
  field ("newest data wins").
- A row is added to `invoice_reminders` **only after** the mail server accepted the message.
  Failures are never stored as reminders.
- The recipient is copied into the reminder row, so the log stays true even if a later upload
  changes the invoice's email.

## Logic

### Remindable

`REMINDABLE_STATUSES = {Status.OUTSTANDING}` in `app/domain/reminders.py`. `can_remind` is
`status in REMINDABLE_STATUSES`, using the same payment-status rule as the list (`invoice_status`),
relative to today (`get_today()`). Changing which statuses can be reminded is a change to that
one constant.

### The draft (AC3)

Composed in `app/domain/reminders.py::compose_draft(invoice, today, sender_name)`, a pure function.
Amount uses the same `en-IN` grouping as the UI (`₹1,25,000.00`), dates use `24 Sep 2026`.
"days" is singular for 1.

**Subject**

```
Payment reminder: invoice INV-2606 (₹1,25,000.00) was due on 15 Aug 2026
```

**Message**

```
Dear Deccan Printing Works,

I hope you are well. This is a friendly reminder that invoice INV-2606 for ₹1,25,000.00,
raised on 16 Jul 2026, was due on 15 Aug 2026 and is now 41 days overdue.

Please arrange payment at your earliest convenience. If you have already paid, please
ignore this message and let us know the payment details so that we can update our records.

If you have any questions about this invoice, please get in touch.

Thank you,
Accounts Team
```

(Each paragraph is one line in the real text; the wrapping above is only for this document.)
The sender name is `REMINDER_SENDER_NAME`, default `Accounts Team`.

### Sending (AC5, AC7, AC10)

`POST /api/invoices/{id}/reminders` runs these steps, stopping at the first failure:

1. Load the invoice → `404 INVOICE_NOT_FOUND`.
2. Status is Outstanding today → else `409 INVOICE_NOT_REMINDABLE` (AC9).
3. `customer_email` is set → else `409 NO_CUSTOMER_EMAIL` (AC6).
4. Body is valid: subject 1–200 characters with no `\r` or `\n`; message 1–5,000 characters;
   **no other fields** (a `to` field is rejected) → `422 VALIDATION_ERROR` (AC4, AC10).
5. Build an `EmailMessage` (plain text, UTF-8): From = `"<sender name>" <SMTP_FROM_ADDRESS>`,
   To = the stored address only, Subject, Date, Message-ID. Send through the `EmailSender`.
   Any `smtplib.SMTPException` or `OSError` (including timeouts) → `424 EMAIL_NOT_SENT` (AC7),
   nothing recorded.
6. Insert the `invoice_reminders` row, commit, return `201`. If this insert itself fails after a
   successful send, the error is logged (`invoice_reminder.record_failed`) and the call still
   returns `201`: the email *did* go, and telling the user otherwise would invite a duplicate.

`EmailSender` is a small protocol (`send(message) -> None`, raises `EmailSendError`). The real
one is `SmtpEmailSender` (stdlib `smtplib`, run with `asyncio.to_thread`, `SMTP_TIMEOUT_SECONDS`
default 10). It is provided through a FastAPI dependency, `get_email_sender`, so tests replace it
with a recorder and never open a socket.

### Settings (AC14)

All optional, all on invoice-service only, documented in `.env.example`:

| Variable | Default | Meaning |
|---|---|---|
| `SMTP_HOST` | `mailpit` | Mail server. The default is the local sink. |
| `SMTP_PORT` | `1025` | Mailpit's port. Real providers use `587` (STARTTLS) or `465`. |
| `SMTP_USERNAME` | empty | Login, if the server needs one. |
| `SMTP_PASSWORD` | empty | Password or app password. Secret: never logged, never returned. |
| `SMTP_STARTTLS` | `false` | Upgrade the connection to TLS. Set `true` for real providers on 587. |
| `SMTP_FROM_ADDRESS` | `accounts@msme-poc.local` | The From address. Use a real mailbox you own when going live. |
| `REMINDER_SENDER_NAME` | `Accounts Team` | Display name in From and the signature. |
| `SMTP_TIMEOUT_SECONDS` | `10` | Connect and send timeout. |

`docker-compose.yml` adds the **Mailpit** service (`axllent/mailpit`, web inbox on
`127.0.0.1:8025`) and passes these variables to invoice-service. `scripts/e2e.sh` refuses to run
if `SMTP_HOST` is not `mailpit`, the same way it refuses to run against the real AI.

## API

### `GET /api/invoices/{invoice_id}/reminder-draft`

Builds the draft. Sends nothing, stores nothing.

**200**
```json
{
  "invoice_id": "…",
  "invoice_number": "INV-2606",
  "customer_name": "Deccan Printing Works",
  "to": "accounts@deccanprinting.example",
  "subject": "Payment reminder: invoice INV-2606 (₹1,25,000.00) was due on 15 Aug 2026",
  "message": "Dear Deccan Printing Works,\n\n…",
  "last_reminder_at": "2026-09-30T09:12:44Z"
}
```
`to` is `null` when the invoice has no email (the UI then shows AC6 and the draft is unused).
`last_reminder_at` is `null` when no reminder has been sent.

Errors: `404 INVOICE_NOT_FOUND`, `409 INVOICE_NOT_REMINDABLE`.

### `POST /api/invoices/{invoice_id}/reminders`

Request `{ "subject": "…", "message": "…" }` (exactly these two fields).

**201**
```json
{ "id": "…", "invoice_id": "…", "to": "accounts@deccanprinting.example", "sent_at": "2026-10-05T09:12:44Z" }
```

| Status | Code | Message shown to the user |
|---|---|---|
| 404 | `INVOICE_NOT_FOUND` | We couldn't find that invoice. |
| 409 | `INVOICE_NOT_REMINDABLE` | This invoice is no longer overdue, so no reminder was sent. |
| 409 | `NO_CUSTOMER_EMAIL` | We don't have an email address for <customer>. Add it in the Customer Email column of your sheet and upload it again. |
| 422 | `VALIDATION_ERROR` | Standard validation body, with the field names |
| 424 | `EMAIL_NOT_SENT` | We couldn't send this email, so nothing was sent. Please try again in a minute. |

`424` is used instead of `502`/`503`/`504` on purpose: the gateway turns those into "this part of
the app isn't responding", which would be the wrong message.

### `GET /api/invoices` (INV-002) — three new fields per item

| Field | Meaning |
|---|---|
| `customer_email` | The stored address, or `null`. |
| `can_remind` | `true` when the invoice is Outstanding (see Remindable). |
| `last_reminder_at` | Time of the most recent reminder, or `null`. A correlated `MAX(sent_at)` subquery. |

The export (`/export`) and dashboard are unchanged.

## Code structure (invoice-service)

```
app/domain/reminders.py     # REMINDABLE_STATUSES, compose_draft(), format_inr(), limits
app/domain/email_sender.py  # EmailSender protocol, SmtpEmailSender, EmailSendError, get_email_sender
app/db/reminder_repo.py     # find invoice + last reminder, insert reminder
app/db/models.py            # + Invoice.customer_email, InvoiceReminder
app/api/reminders.py        # the two endpoints (registered in app/api/__init__.py)
app/api/schemas.py          # + ReminderDraftOut, SendReminderIn (extra=forbid), ReminderOut; InvoiceItem fields
app/config.py               # SMTP_* and REMINDER_SENDER_NAME
migrations/versions/0002_add_customer_email_and_reminders.py
```

The new routes have an extra path segment (`/{id}/reminders`), so they cannot be captured by, or
capture, the fixed routes `/uploads`, `/template`, `/dashboard`, `/export`.

## UI

### Table (INV-002 changes)

A **Reminder** column (not sortable) is added after Status. To keep the table within 1280px
(AC15), the Record status moved under the invoice number, so the table stays at six columns:

| Row | Cell |
|---|---|
| `can_remind` | Secondary button **Send email reminder** with a mail icon, 48px tall, label allowed to wrap onto two lines so the column stays narrow. `aria-label="Send email reminder for INV-2606"`. |
| `last_reminder_at` set | Muted text under the button (or alone on non-remindable rows): **Last reminder sent 30 Sep 2026**. |
| otherwise | Empty. |

With the Record status as a seventh column the table overflowed 1280px by 83px, so it now sits
under "Raised <date>" in the Invoice cell, as the Raised date already does. What it shows ("New",
or the "Updated on <date>" badge) is unchanged.

### Dialog (new `components/ui/dialog.tsx` on Radix Dialog, `modules/invoices/components/ReminderDialog.tsx`)

```
┌ Send email reminder ───────────────────────────────────────────────┐
│ INV-2606 · Deccan Printing Works · ₹1,25,000.00 · 41 days overdue  │
│                                                                    │
│ ⚠ A reminder for this invoice was already sent on 30 Sep 2026.     │  only if last_reminder_at
│                                                                    │
│ To       accounts@deccanprinting.example      (read only)          │
│ Subject  [ Payment reminder: invoice INV-2606 (₹1,25,000.00) … ]   │
│ Message  [ Dear Deccan Printing Works,                           ] │
│          [ …                                                     ] │
│                                                                    │
│                         [ ✉ Send reminder ]   [ Cancel ]           │
└────────────────────────────────────────────────────────────────────┘
```

The draft is fetched each time the dialog opens (never cached) so the days overdue are current.

| State | What the user sees |
|---|---|
| Loading the draft | Skeletons shaped like the form |
| Draft failed | Error alert with the message and **Try again**; `INVOICE_NOT_REMINDABLE` shows its message, refreshes the list and offers only **Close** (AC9) |
| No email (AC6) | Info alert with the AC6 sentence and a **Upload invoices** link. No form, no Send button. |
| Ready | The form above. Subject and Message editable, To read-only. Inline errors next to a field when empty or too long, shown on Send, and Send does nothing until fixed (AC4). |
| Sending (AC11) | Send button disabled and reads "Sending…"; the fields become read-only |
| Send failed (AC7) | Error alert at the top of the dialog (`role="alert"`) with the server's message. The form and the user's edits stay; Send is available again. |
| Sent (AC5) | The form is replaced by a success alert (`role="status"`): "Reminder sent to accounts@deccanprinting.example", and one **Close** button. It does not auto-dismiss. The list is refetched, so the row shows "Last reminder sent <today>". |

Accessibility (AC13): Radix Dialog supplies the focus trap, Escape to close and return of focus
to the opening button. Fields use visible `<label>`s. Alerts use the existing alert styling with
an icon and text, never colour alone. Button text stays at 18px, all spacing from tokens.

The design system's Components table gets a **Dialog** row.

## Observability (AC12)

| Event | Level | Fields |
|---|---|---|
| `invoice_reminder.sent` | INFO | `invoice_id`, `reminder_id`, `duration_ms` |
| `invoice_reminder.failed` | WARNING | `invoice_id`, `reason` (exception class name, e.g. `ConnectionRefusedError`), `duration_ms` |
| `invoice_reminder.record_failed` | ERROR | `invoice_id` |

Never logged: recipient, subject, message, SMTP username or password. Metric:
`invoice_reminders_total{result="sent|failed"}`. An operator seeing `invoice_reminder.failed`
checks that `SMTP_HOST`/credentials are right and that the mail server is reachable from the
container; with the default setup, that Mailpit is running.

## Edge cases & errors

| Case | Behaviour |
|---|---|
| Invoice paid by a re-upload while the dialog is open | Send returns `409 INVOICE_NOT_REMINDABLE`; the dialog says so and the list refreshes (AC9) |
| Re-upload changes the email while the dialog is open | The send uses the address stored at send time; the success message shows the address actually used |
| Subject contains a line break (pasted text, or a crafted request) | `422`; nothing sent (AC10). The UI also blocks it before sending |
| Request body includes `to`, `cc`, `bcc` or anything else | `422 VALIDATION_ERROR` (`extra = forbid`); nothing sent |
| Mail server down, wrong password, or the connection times out | `424 EMAIL_NOT_SENT`, nothing recorded; the user can retry (AC7) |
| Mail server accepted the message but recording it failed | `201`; error logged; the row shows no "Last reminder" |
| Double click on Send | The button is disabled after the first click, so one request is made (AC11) |
| Customer name or invoice number contains odd characters | Used only in the plain-text body and the subject, which is single-line-checked; no HTML is produced |
| Invoice has no email | AC6 panel; the API also refuses with `409 NO_CUSTOMER_EMAIL` |
| Unknown or malformed invoice ID | `404` / `422` standard errors |

## Testing

Every AC needs at least one automated test whose name contains its ID.

| AC | Tests |
|---|---|
| AC1 | API: list `can_remind` is true only for Outstanding (paid, at risk, open are false). Vitest: button on the outstanding row only. Playwright: Outstanding tab shows one button per row. |
| AC2 | API: draft endpoint returns to / subject / message and sends nothing. Vitest: clicking the button opens the dialog with the summary and draft, and the send call is not made. |
| AC3 | Unit: `compose_draft` exact subject and message (1 day vs many, INR grouping, long names, sender name). API: draft matches. |
| AC4 | API: 422 for empty or over-length subject or message, a subject with a line break. Vitest: read-only To, inline field errors, no request until valid. |
| AC5 | API: POST sends exactly one message with the right From, To, Subject and body, returns 201. Vitest: success alert names the address and stays. Playwright: the message arrives in Mailpit. |
| AC6 | API: `to` is null in the draft and POST gives `409 NO_CUSTOMER_EMAIL`, nothing sent. Vitest: panel, Upload link, no Send button. |
| AC7 | Unit: SMTP errors and timeouts become `EmailSendError`. API: a failing sender gives `424`, no reminder row. Vitest: error shown, edits kept, retry succeeds. |
| AC8 | API: reminder row stored; list and draft show `last_reminder_at`. Vitest: warning in the dialog and "Last reminder sent" on the row. Playwright: row text after a send. |
| AC9 | API: paid or not-overdue invoice → `409` on both endpoints, nothing sent. Vitest: message shown, list refetched. |
| AC10 | API: extra fields (`to`, `cc`) and newline subjects → 422; the recorded message has a single To equal to the stored address. Unit: header built by `EmailMessage`. |
| AC11 | Vitest: button disabled and "Sending…" while pending; a double click makes one request. |
| AC12 | API: capture logs during a send and a failure; assert events and fields, and that the address, subject and body never appear. Metrics counter increments. |
| AC13 | Vitest: dialog role, labelled fields, accessible button name, alerts. Playwright: keyboard open, Escape, focus returns; axe on the dialog. |
| AC14 | Unit: settings defaults point at Mailpit; password is a `SecretStr`. Task checklist: every variable in `.env.example`; `e2e.sh` guard. |
| AC15 | Playwright: the existing "table fits at 1280px" test, with the Reminder column present. |
| INV-001-AC13 | See INV-001 design: unit tests for parsing and validation, upload API tests, template test. |
