---
id: INV-004
title: Email payment reminder — tasks
status: implemented
design: ./design.md
---

# INV-004 — Tasks

Branch: `feat/INV-004-email-reminder`. Commit prefix: `feat(invoices): … [INV-004]`.
Specs were written first (ADR-0004, INV-004, INV-001 AC13, module/product/architecture updates).
Tests for each task are written with it; test names contain the AC ID.

## A. Customer email on invoices (INV-001-AC13)

- [x] 1. `invoice_rules.py`: optional `Customer Email` column, `parse_customer_email` (trim,
       lower-case, format, ≤ 254 chars), `ParsedInvoice.customer_email`, row validation — _INV-001-AC13_
- [x] 2. `excel_reader.py`: read the optional column when present; sheets without it still load —
       _INV-001-AC3, AC13_
- [x] 3. `template.py`: add the column, example and help text — _INV-001-AC11_
- [x] 4. Migration `0002`: `invoices.customer_email`; model; `invoice_repo.upsert_invoices` writes
       it on insert and overwrite — _INV-001-AC6, AC13_
- [x] 5. Tests: unit (valid, invalid, blank, upper-case, too long); upload API (stored, lower-cased,
       overwritten by a later upload, rejected row reason, file without the column) —
       _INV-001-AC13_

## B. Backend — reminders

- [x] 6. Migration `0002` also creates `invoice_reminders`; `InvoiceReminder` model; update
       `conftest.clean_tables` — _AC8_
- [x] 7. `config.py`: SMTP and sender settings with Mailpit defaults — _AC14_
- [x] 8. `domain/reminders.py`: `REMINDABLE_STATUSES`, `format_inr`, `compose_draft` — _AC1, AC3_
- [x] 9. `domain/email_sender.py`: `EmailSender`, `SmtpEmailSender` (stdlib, thread, STARTTLS,
       login, timeout), `EmailSendError`, `get_email_sender` — _AC5, AC7, AC10_
- [x] 10. `db/reminder_repo.py` and `db/invoice_queries.py`: last-reminder subquery on the list —
        _AC8_
- [x] 11. `api/schemas.py` + `api/reminders.py`: draft and send endpoints, error codes, `extra =
        forbid`, subject line-break check; register the router — _AC2, AC4–AC10_
- [x] 12. `GET /api/invoices`: `customer_email`, `can_remind`, `last_reminder_at` — _AC1, AC8_
- [x] 13. Logging and metric (`invoice_reminders_total`), nothing personal in logs — _AC12_
- [x] 14. Tests: unit (`format_inr`, `compose_draft`, SMTP error mapping with a fake `smtplib`,
        settings defaults); API with a recording sender for AC1–AC12 as listed in design

## C. Infrastructure

- [x] 15. `docker-compose.yml`: Mailpit service, pass `SMTP_*` to invoice-service; `.env.example`
        documents every variable; `CLAUDE.md` mentions Mailpit — _AC14_
- [x] 16. `scripts/make_samples.py`: add the Customer Email column (one Outstanding invoice
        without an address, to show AC6); `scripts/e2e.sh`: refuse to run unless `SMTP_HOST` is
        `mailpit`, and pass `MAILPIT_URL` to the e2e container — _AC14_

## D. Frontend

- [x] 17. `api.ts`: new `InvoiceItem` fields, `ReminderDraft`, `getReminderDraft`,
        `sendReminder`, keys; list the optional column on the upload page — _AC1, AC2, AC5_
- [x] 18. `components/ui/dialog.tsx` (Radix) and the design-system Dialog row — _AC13_
- [x] 19. `ReminderDialog.tsx` with every state in the design — _AC2, AC4–AC9, AC11, AC13_
- [x] 20. `InvoiceTable.tsx`: Reminder column, button, "Last reminder sent"; keep the table within
        1280px — _AC1, AC8, AC15_
- [x] 21. `testData.ts` fixtures; Vitest tests for AC1, AC2, AC4–AC9, AC11, AC13

## E. Verify

- [x] 22. Playwright `invoice-reminder.spec.ts`: Outstanding rows have the button; open, edit,
        send; the message arrives in Mailpit; the row shows "Last reminder sent"; the no-email
        case; keyboard and axe on the dialog; the 1280px fit — _AC1, AC5, AC6, AC8, AC13, AC15_
- [x] 23. Run `docker compose run --rm --build invoice-service pytest` and `ruff check .`;
        frontend `npm test`, `npm run lint`, typecheck; `scripts/e2e.sh`
- [x] 24. `module.md` was updated with the specs (features, entities, API, rules). INV-004,
        INV-001 and INV-002 are now `implemented`; Verification is below

## Verification (2026-10-05)

- invoice-service: 238 tests passed; `ruff check` and `ruff format --check` clean. New tests cover
  INV-004 AC1–AC12 and AC14 (unit and API, with a recording stand-in for the mail server) and
  INV-001-AC13.
- Frontend: 167 unit tests passed; typecheck, ESLint and the design-token check clean. AC1, AC2,
  AC4–AC9, AC11 and AC13 are covered in `InvoiceReminder.test.tsx`.
- End to end: 64 Playwright tests passed (`scripts/e2e.sh`, mail forced to Mailpit): the button
  appears on Outstanding rows only; the edited reminder arrives in Mailpit; the row shows "Last
  reminder sent"; the no-email case; keyboard use, focus return and axe on the dialog; and the
  table fits 1280px.
- Found and fixed while testing: (1) a successful send could return 500 when saving the reminder
  record failed, because the invoice object was expired after the rollback; (2) focus went to the
  page instead of the opening button when the dialog closed.
- Layout decision: seven columns overflowed 1280px by 83px, so the Record status moved under the
  invoice number (INV-002 AC1 reworded, AC1a unchanged).
- Not run: a real SMTP provider. Delivery to a real inbox depends on the provider settings in
  `.env` (ADR-0004).
