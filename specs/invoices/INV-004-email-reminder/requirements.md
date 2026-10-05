---
id: INV-004
title: Email payment reminder
status: implemented
depends_on: [INV-001, INV-002, PLT-002]
---

# INV-004 — Email payment reminder

## Goal

From the All invoices page, a user can send a polite payment reminder by email to the client of
any overdue invoice, in a few clicks: the system writes the message, the user checks it, and it
goes to the client.

## User stories

- As a business owner, I want a "Send email reminder" button on each overdue invoice, so that I
  can chase payment without writing the same email again and again.
- As a business owner, I want to read and change the message before it is sent, so that I stay in
  control of what my client receives.
- As a business owner, I want to see which invoices I have already reminded, and when, so that I
  don't chase the same client twice by accident.
- As a business owner, I want a clear message when an email can't be sent, so that I know nothing
  went out and what to do.

## Acceptance criteria

Use of "overdue" below means payment status **Outstanding** (`invoices/module.md`): unpaid and
past its due date.

| ID | Criterion |
|---|---|
| INV-004-AC1 | THE SYSTEM SHALL show a **Send email reminder** button in the All invoices table on every row whose invoice is Outstanding. Rows that are Paid, At risk or Open SHALL NOT show it. Whether a row can be reminded is decided by the service, not the page. |
| INV-004-AC2 | WHEN the user clicks the button THE SYSTEM SHALL open a dialog titled "Send email reminder" with a summary of the invoice (number, customer, amount, days overdue) and a composed draft: **To** (the client's email address), **Subject** and **Message**. Opening the dialog SHALL NOT send anything. |
| INV-004-AC3 | THE SYSTEM SHALL compose the draft in plain, polite language from the invoice's own data: customer name, invoice number, amount (INR, `en-IN`), date raised, due date, days overdue, and the sender name. The draft is plain text. |
| INV-004-AC4 | THE SYSTEM SHALL let the user edit the Subject and the Message before sending, and SHALL show the recipient but not let it be changed. The subject must be 1–200 characters on one line, and the message 1–5,000 characters; otherwise the system SHALL say so next to the field and not send. |
| INV-004-AC5 | WHEN the user clicks **Send reminder** in the dialog THE SYSTEM SHALL send the email to the client's address from the sender address configured for the app, and then confirm it in the dialog, naming the address ("Reminder sent to accounts@deccanprinting.in"). The dialog SHALL stay open until the user closes it. |
| INV-004-AC6 | IF the invoice has no customer email THEN THE SYSTEM SHALL say so in the dialog ("We don't have an email address for <customer>. Add it in the Customer Email column of your sheet and upload it again."), link to the Upload invoices page, and SHALL NOT allow sending. |
| INV-004-AC7 | IF the email cannot be sent (the mail server is unreachable, refuses the message, or is not set up) THEN THE SYSTEM SHALL keep the dialog open with the user's edits, say in plain language that nothing was sent and what to do, SHALL NOT record a reminder, and SHALL let the user try again. |
| INV-004-AC8 | WHEN a reminder is sent THE SYSTEM SHALL record it (invoice, recipient, subject, message, time) and show **Last reminder sent <date>** under the button on that invoice's row. IF a reminder was already sent THEN the dialog SHALL warn "A reminder for this invoice was already sent on <date>." but still allow sending another. |
| INV-004-AC9 | IF the invoice is no longer Outstanding when the user opens the dialog or clicks Send (for example, a re-upload marked it paid) THEN THE SYSTEM SHALL send nothing, say "This invoice is no longer overdue, so no reminder was sent.", and refresh the list. |
| INV-004-AC10 | THE SYSTEM SHALL send only the subject and message the user approved, to the address stored on the invoice. It SHALL NOT accept a recipient from the browser, and SHALL reject a subject that contains a line break. |
| INV-004-AC11 | WHILE a reminder is being sent THE SYSTEM SHALL disable the Send button and show "Sending…", so a double click cannot send two emails. |
| INV-004-AC12 | THE SYSTEM SHALL NOT write the recipient address, subject or message text to the logs. Logs and metrics SHALL record only the invoice ID, the reminder ID, the outcome and the duration. |
| INV-004-AC13 | THE SYSTEM SHALL be fully usable by keyboard and screen reader: the dialog takes focus when it opens, Escape closes it, focus returns to the button that opened it, every field has a visible label, and results and errors are announced. Each row's button has an accessible name that includes the invoice number. |
| INV-004-AC14 | THE SYSTEM SHALL read its mail settings from environment variables, documented in `.env.example`, and SHALL default to a local mail sink (Mailpit) so that nothing reaches a real client until real SMTP settings are configured. |
| INV-004-AC15 | THE SYSTEM SHALL keep the All invoices table readable on a 1280px laptop screen with the Reminder column added, without sideways scrolling (INV-002 design, "As built"). |

## Out of scope

- Reminders for At risk or Open invoices (only Outstanding), and bulk or automatic reminders.
- Typing, changing or saving a recipient in the UI. The address comes from the sheet (ADR-0004).
- Several recipients, CC/BCC, attachments, an HTML or branded email, or the invoice as a PDF.
- Tone choices, translations, or AI-written drafts.
- Delivery tracking (opened, bounced), unsubscribe handling, and a reminder history screen.
- SMS and WhatsApp.
- Authentication. Anyone who can open the app can send a reminder (ADR-0004, Consequences).

## Open questions

- None. Resolved on 2026-10-05:
  - "Outstanding invoice" means the status **Outstanding**, as defined in `module.md`. Extending
    the button to At risk is a one-line change to the service's remindable statuses, plus a
    wording variant for "due soon" — a new request.
  - The recipient comes from a new optional **Customer Email** column (INV-001, AC13), and is not
    editable (ADR-0004).
  - The user sees and may edit the draft before sending (one extra click, because the email goes
    to a client and cannot be recalled).
