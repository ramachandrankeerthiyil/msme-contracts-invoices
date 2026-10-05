---
id: PRODUCT
title: Product overview
status: approved
---

# Product overview

## Problem

Small businesses (MSMEs) keep contracts as PDF/Word files and track invoices in spreadsheets.
Nobody notices a contract is about to expire, or an invoice is about to fall overdue, until it
is too late.

## Vision

One simple web app where a small-business owner uploads their contracts and invoice sheet and
immediately sees **what needs attention this week**.

## Users

- **Anyone may use the system.** There are no user accounts, logins or roles in the POC.
- **Design for older users.** Many users are over 60 and not technical. Every screen must be
  readable, calm and obvious (see `ui-design-system.md`).

## POC scope

### In scope

| Module | Capability |
|---|---|
| Contracts | Upload a PDF or Word contract; extract parties, key dates, terms and risks; store them in PostgreSQL; list/detail view; dashboard |
| Invoices | Upload an Excel invoice sheet; create or update invoices; flag outstanding and at-risk invoices; list view; dashboard; email a payment reminder to the client of an overdue invoice |
| Assistant | "Talk to Me": ask questions about contracts and invoices in plain English; answers use only the user's data and link to each record (read-only) |
| Platform | Professional, consistent app shell and navigation; logging and observability |

The Contracts and Invoices modules are **fully independent** of each other. The Assistant reads
from both but changes nothing (ADR-0003).

### Out of scope (POC)

- User accounts, authentication, roles, multi-tenancy
- Linking invoices to contracts
- Editing extracted contract data or invoices in the UI; deleting contracts
- Legacy `.doc` / `.xls` files
- Multiple currencies (all amounts are INR)
- Reminders other than the one-at-a-time email for an Outstanding invoice (INV-004): no bulk or
  automatic reminders, no SMS or WhatsApp
- Payments, tax, accounting integrations
- OCR of scanned (image-only) documents
- Scale, high availability, concurrency tuning

## Glossary

| Term | Meaning |
|---|---|
| **Contract** | An uploaded PDF/Word agreement plus the data extracted from it |
| **Party** | An organisation or person bound by a contract (e.g. client, supplier) |
| **Key date** | A date that matters in a contract: start, end, renewal, notice deadline, etc. |
| **Term** | An important clause summarised in plain language (payment, termination, renewal, …) |
| **Risk** | A clause or omission that could hurt the business, rated High / Medium / Low |
| **In force** | A contract whose start date ≤ today ≤ end date |
| **Expired** | A contract whose end date < today |
| **No end date** | A contract with no end date found; shown separately on the dashboard |
| **Not yet started** | A contract whose start date is in the future |
| **Contract at risk** | Expiring within 3 days **or** has a high-severity risk (see `contracts/module.md`) |
| **Invoice** | One row of an uploaded invoice spreadsheet, identified by its invoice number |
| **Paid** | An invoice with a Paid Date |
| **Unpaid** | An invoice without a Paid Date |
| **Outstanding** | Unpaid **and** past its due date |
| **Invoice at risk** | Unpaid **and** due within the next 5 days |
| **Needs follow-up** | Outstanding **or** at risk |
| **Reminder** | A polite payment-request email sent to the client of an Outstanding invoice, to the address in the sheet's Customer Email column (INV-004) |
| **Current week** | The 7 days starting on the date of the most recent invoice upload; an invoice is in it when its Due Date falls inside |
| **Updated on <date>** | Record status of an invoice that was overwritten by a later row (in a later upload or later in the same file) |
