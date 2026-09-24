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

**Prerequisites:** Docker Desktop with WSL integration enabled for your distro
(Settings → Resources → WSL integration).

```bash
cp .env.example .env          # then set the passwords and ANTHROPIC_API_KEY
docker compose up -d --build  # first build takes a few minutes
scripts/smoke.sh              # optional: verify the stack end to end
```

Open **http://localhost:8080**.

| What | Where |
|---|---|
| Web app | http://localhost:8080 |
| Invoice API docs | http://localhost:8080/api/invoices/docs |
| Contract API docs | http://localhost:8080/api/contracts/docs |
| Metrics dashboards (optional) | `docker compose --profile observability up -d`, then http://localhost:3001 (`GRAFANA_PORT`) |

Stop with `docker compose down`. To also delete all data: `docker compose down -v`.

## Troubleshooting

Every response carries an `X-Request-ID` header, and error screens show it as a reference
number. Find everything that happened for that request with:

```bash
docker compose logs gateway invoice-service contract-service | grep <request-id>
```
