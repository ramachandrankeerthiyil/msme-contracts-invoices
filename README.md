# MSME Contracts & Invoices (POC)

Upload contracts and invoice spreadsheets, and track what needs attention.

- **Contracts:** upload a PDF or Word contract. The app extracts the parties, key dates, terms and
  risks, and shows totals for in-force, at-risk, expired and no-end-date contracts.
- **Invoices:** upload an Excel sheet of invoices. The app flags outstanding and at-risk invoices
  and shows this week's totals.

## Project layout

| Path | What it holds |
|---|---|
| `specs/` | Product, architecture, UI and feature specs — the source of truth |
| `frontend/` | React web front end |
| `services/contract-service/` | Contract upload, extraction and dashboard API |
| `services/invoice-service/` | Invoice upload, flagging and dashboard API |
| `gateway/` | Nginx config — single entry point for the browser |
| `samples/` | Sample contracts and invoice spreadsheets for testing and demos |

## Getting started

_Run instructions will be added once the services are scaffolded._ Copy `.env.example` to `.env`
and fill in the values before running anything.
