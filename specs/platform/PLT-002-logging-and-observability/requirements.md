---
id: PLT-002
title: Logging and observability
status: draft
depends_on: [ARCHITECTURE]
---

# PLT-002 — Logging and observability

## Goal

When something goes wrong (for example, a contract fails to extract or an Excel row is rejected),
a developer can find out exactly what happened within minutes, starting from the request ID the
user sees on screen.

## User stories

- As a developer, I want every log line for one request tied together, so that I can trace it through the gateway and services.
- As a developer, I want health and metrics endpoints, so that I can see at a glance whether the system is working.
- As a user, I want a reference number when something fails, so that I can report the problem.

## Acceptance criteria

| ID | Criterion |
|---|---|
| PLT-002-AC1 | THE SYSTEM SHALL write all service logs to stdout as JSON with at least: `timestamp` (UTC), `level`, `service`, `request_id`, `event`, `message`. |
| PLT-002-AC2 | WHEN a request enters the gateway THE SYSTEM SHALL assign an `X-Request-ID` (or keep a valid incoming one), pass it to the service, return it in the response header, and include it in every related log line. |
| PLT-002-AC3 | THE SYSTEM SHALL log one access line per API request with method, path, status code and duration in ms. |
| PLT-002-AC4 | THE SYSTEM SHALL log business events with structured fields, at minimum: `invoice_upload.completed` (rows created/updated/rejected), `contract_upload.received`, `contract_extraction.completed` (duration, model, token usage), `contract_extraction.failed` (reason). |
| PLT-002-AC5 | THE SYSTEM SHALL NOT log document text, extracted contract content, full Excel rows, or API keys at INFO level or above. |
| PLT-002-AC6 | THE SYSTEM SHALL expose `/health` (process is up) and `/ready` (the database is reachable, plus the Claude API key is configured for contract-service) on each service. |
| PLT-002-AC7 | THE SYSTEM SHALL expose Prometheus metrics at `/metrics` on each service: request count and latency by route/status, uploads by result, rows rejected, extraction duration and failures. |
| PLT-002-AC8 | WHEN an unexpected error occurs THE SYSTEM SHALL log it with a stack trace and return the standard error body including `request_id`, and the UI SHALL show "Something went wrong. Reference: <request_id>". |
| PLT-002-AC9 | THE SYSTEM SHALL let the log level be set per service via `LOG_LEVEL` without code changes. |
| PLT-002-AC10 | WHERE the `observability` compose profile is enabled THE SYSTEM SHALL run Prometheus and Grafana with a provisioned dashboard showing request rate, error rate, latency and upload/extraction metrics. |
| PLT-002-AC11 | THE SYSTEM SHALL log frontend runtime errors to the browser console with the request ID of the failed call (no remote error collection in the POC). |

## Out of scope

- Distributed tracing (OpenTelemetry), log shipping or aggregation, alerting, uptime monitoring.

## Open questions

- Should OpenTelemetry tracing be added in the POC, or deferred (proposed)?
