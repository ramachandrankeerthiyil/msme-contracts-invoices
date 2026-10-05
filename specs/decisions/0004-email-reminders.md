---
id: ADR-0004
title: Payment reminder emails sent by invoice-service over SMTP, with a local mail sink by default
status: accepted
date: 2026-10-05
---

# ADR-0004 — Payment reminder emails sent by invoice-service over SMTP

## Context

INV-004 lets a user email a payment reminder to the client of an overdue invoice. That is the
first time the system sends anything **outside** the Docker network to a third party's inbox, and
the app has no authentication (product.md). We need to decide where the sending lives, how it
talks to a mail server, and how to keep a POC from emailing real clients by accident or being used
to email strangers.

## Decision

1. **invoice-service sends the email.** Reminders are an invoice concern and need the invoice's
   data and the reminder log, so no new service is added. The service-independence rules are
   unchanged: nothing is added between contract-service and invoice-service.
2. **Plain SMTP through Python's standard library** (`smtplib` + `email.message.EmailMessage`),
   run in a worker thread so it never blocks the event loop. No new dependency. Any provider that
   offers SMTP (Gmail app password, SES, SendGrid, Zoho, a company mail server) works by changing
   `SMTP_*` settings.
3. **A local mail sink is the default.** `docker-compose.yml` ships **Mailpit**, a fake SMTP
   server with a web inbox on `http://localhost:8025`. `SMTP_HOST` defaults to it, so out of the
   box a "sent" reminder lands in Mailpit and **nothing reaches a real client**. Going live is a
   deliberate step: set `SMTP_HOST` and its credentials in `.env`.
4. **The recipient is never typed or changed in the UI or API.** The server sends only to the
   `customer_email` stored on the invoice (from the optional **Customer Email** column of the
   uploaded sheet). The send endpoint accepts a subject and message, not an address. Because there
   is no login, a free-form recipient would make the service an open relay for anyone who can
   reach it. If an invoice has no email, the user fixes the sheet and re-uploads.
5. **The draft is composed by a deterministic template**, not by the Claude API. The message is
   short, factual and must be predictable. It involves money owed and goes to a client, so there
   is no value in model variation and a cost and failure mode to avoid. The user can still edit
   the text before sending.
6. **Plain-text email only.** No HTML part, so there is nothing to sanitise and no tracking or
   remote content. Header-injection is prevented by rejecting CR/LF in the subject and by building
   the message with `EmailMessage`, which refuses them in headers.
7. **Every sent reminder is recorded** in `invoices.invoice_reminders` (recipient, subject, body,
   time). It is a business record (who was chased and when). Failures are **not** recorded as
   reminders, only logged and counted.
8. **Nothing about the email goes in logs.** Recipient, subject and body are personal and
   business data. Logs and metrics carry IDs, outcome and duration only.

## Alternatives considered

- **A transactional-email API (SendGrid, SES API, Resend).** Needs an account, a vendor SDK and an
  API key, and ties the POC to one vendor. SMTP is supported by all of them, so we keep the option.
- **A new `notification-service`.** Cleaner if SMS and WhatsApp follow, but one more container,
  its own database and contract for one email template. Revisit when a second channel is added.
- **Letting the user type or edit the recipient.** Friendlier for sheets without emails, but an
  open relay in an app with no authentication. Rejected for the POC.
- **Opening the user's mail client (`mailto:`).** No server work, but it sends nothing from the
  app, can't be recorded, and can't be tested.
- **Drafting with Claude.** See decision 5.

## Consequences

- One more container in the default stack (Mailpit), and eight new optional settings on
  invoice-service.
- Real delivery depends on the user's mail provider: SPF/DKIM for the sender domain, and provider
  rate limits, are the user's concern.
- With no login, **anyone who can open the app can trigger a reminder to a client's stored
  address**. The blast radius is limited to overdue invoices' own clients, one email per click,
  and the Mailpit default. Authentication is a prerequisite before this is used in production.
- Sheets must carry a Customer Email column for the feature to be usable, which changes the
  Excel template (INV-001).
