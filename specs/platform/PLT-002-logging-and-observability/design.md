---
id: PLT-002
title: Logging and observability — design
status: implemented
requirements: ./requirements.md
---

# PLT-002 — Design

## Overview

PLT-002 is the first feature built, so it also lays the **backend foundation** that every other
feature builds on: Docker Compose, PostgreSQL with one schema per service, the Nginx gateway,
and a FastAPI skeleton for each service. The skeleton includes logging, request IDs, errors,
health and metrics.

```
Browser ──► gateway ──(X-Request-ID)──► invoice-service ──► Postgres (schema invoices)
              │  sets/validates ID          │  RequestContextMiddleware binds ID to logs
              │  JSON access log            │  AccessLogMiddleware + Prometheus metrics
              │  echoes ID in response      │  error handlers put ID in error body
              ▼                             ▼
         stdout (JSON)                stdout (JSON)  ──►  docker compose logs
                                      /metrics      ──►  Prometheus ──► Grafana   (profile: observability)
```

## Repository layout added by this feature

```
docker-compose.yml
db/init/01-schemas.sh                 # creates schemas + one DB user per service
gateway/
  Dockerfile
  nginx.conf
observability/                        # used only with `--profile observability`
  prometheus.yml
  grafana/provisioning/datasources/prometheus.yml
  grafana/provisioning/dashboards/dashboards.yml
  grafana/dashboards/msme-poc.json
services/<name>-service/              # identical skeleton for invoice- and contract-service
  Dockerfile
  pyproject.toml                      # deps managed with uv inside the image
  alembic.ini
  migrations/                         # Alembic env; version table lives in the service schema
  app/
    main.py                           # create_app(): wires middleware, handlers, routers
    config.py                         # pydantic-settings; reads .env
    db.py                             # SQLAlchemy engine/session; search_path = service schema
    core/
      logging.py                      # structlog JSON config (AC1, AC5, AC9)
      request_context.py              # request-ID middleware + contextvar (AC2)
      access_log.py                   # one access line per request (AC3)
      errors.py                       # AppError + exception handlers (AC8)
      metrics.py                      # Prometheus registry + HTTP metrics (AC7)
      health.py                       # /health, /ready (AC6)
    api/                              # feature routers (added by later features)
    domain/                           # business rules (added by later features)
  tests/
    conftest.py                       # app client + Postgres test DB
    core/                             # tests for everything in app/core
```

**Shared code decision:** `app/core/` is duplicated in both services instead of shared as a
library. It is about 250 lines. Duplicating it keeps each service independently buildable and
deployable (architecture rule 4). A test in each service guards the behaviour, so drift is
caught.

## Docker Compose

| Service | Image / build | Ports (host) | Notes |
|---|---|---|---|
| `db` | `postgres:16-alpine` | `5432` (localhost only) | Volume `pgdata`; runs `db/init/*.sh` on first start |
| `invoice-service` | `services/invoice-service` | — | Internal port 8002; runs `alembic upgrade head` before starting uvicorn |
| `contract-service` | `services/contract-service` | — | Internal port 8001; volume `uploads:/data/uploads` |
| `frontend` | `frontend` (PLT-001) | — | Nginx serving the built React app |
| `gateway` | `gateway` | **`8080`** | The only public entry point |
| `prometheus` | `prom/prometheus` | `9090` | `profiles: [observability]` |
| `grafana` | `grafana/grafana` | `3001` (`GRAFANA_PORT`) | `profiles: [observability]`; anonymous viewer access; plugin downloads disabled |

- Every service has a Docker `healthcheck` calling `/health`.
- `gateway` `depends_on` the services with `condition: service_healthy`.
- `invoice-service` also uses the `uploads` volume (it keeps the uploaded Excel files).

**DB users:** `db/init/01-schemas.sh` creates the `invoices` and `contracts` schemas and users
`invoice_svc` / `contract_svc`. Each user owns only its own schema and has no rights on the other.
Passwords come from `.env` (`INVOICE_DB_PASSWORD`, `CONTRACT_DB_PASSWORD`).

## Gateway (Nginx)

```nginx
# Keep a well-formed incoming ID, otherwise use Nginx's own unique $request_id (AC2)
map $http_x_request_id $req_id {
    "~^[A-Za-z0-9._-]{8,64}$"  $http_x_request_id;
    default                    $request_id;
}

log_format json escape=json '{"timestamp":"$time_iso8601","service":"gateway","level":"info",'
  '"event":"http.access","request_id":"$req_id","method":"$request_method","path":"$uri",'
  '"status":$status,"duration_s":$request_time,"bytes":$body_bytes_sent}';
access_log /dev/stdout json;

client_max_body_size 21m;               # 20 MB contracts + multipart overhead

location /api/invoices/  { proxy_pass http://invoice-service:8002;  proxy_set_header X-Request-ID $req_id; }
location /api/contracts/ { proxy_pass http://contract-service:8001; proxy_set_header X-Request-ID $req_id; }
location /               { proxy_pass http://frontend:80; }
add_header X-Request-ID $req_id always;
location = /healthz      { return 200 "ok"; }
```

- The path is passed through unchanged, so each service mounts its routers under `/api/<module>`.
- `/health`, `/ready` and `/metrics` stay at the service root and are **not** routed through the
  gateway. Only Docker healthchecks and Prometheus reach them, over the internal network.
- `$request_time` is in seconds, so the gateway logs `duration_s` (the services log `duration_ms`).
- The gateway resolves services per request (Docker DNS), so it starts and serves the UI even
  while a service is down. Upstream failures return the standard JSON error with code
  `SERVICE_UNAVAILABLE` (503), and unknown `/api/*` paths return JSON `NOT_FOUND`.
- The gateway hides the services' own `X-Request-ID` header and adds its own, so responses carry exactly one.

## Logging (AC1, AC3, AC4, AC5, AC9)

- **Library:** `structlog`, with the standard `logging` module routed through it. That way
  uvicorn, SQLAlchemy and library logs come out as the same JSON. Uvicorn's own access log is
  disabled and replaced by `AccessLogMiddleware`.
- **Processors:** `merge_contextvars` → add `service`, `level`, `timestamp` (ISO UTC) →
  `redact_sensitive` → `format_exc_info` → `JSONRenderer`.
- **Line shape:**
  ```json
  {"timestamp":"2026-09-24T10:15:02.113Z","level":"info","service":"invoice-service",
   "request_id":"3f1c…","event":"invoice_upload.completed","message":"Invoice upload processed",
   "upload_id":"…","rows_created":100,"rows_updated":15,"rows_overwritten":2,"rows_rejected":3}
  ```
  `event` is a stable, dot-separated machine name. `message` is human-readable.
- **Event naming:** `<noun>.<past-tense-verb>`. Each feature's design lists its events.
  PLT-002 itself defines: `app.started`, `http.access`, `http.unhandled_error`, `db.ready_check_failed`.
- **Redaction (AC5):** `redact_sensitive` drops or masks any key named `api_key`, `authorization`,
  `password`, `document_text`, `raw_extraction`, `rows` or `content`, and truncates any string
  value longer than 500 characters. A unit test feeds it these keys.
- **Log level (AC9):** `LOG_LEVEL` env var (default `INFO`), applied to the root logger at startup.

## Request context (AC2)

`RequestContextMiddleware` (pure ASGI, so it also wraps error responses):
1. Reads `X-Request-ID`. If it is missing or malformed (same regex as the gateway), it generates
   `uuid4().hex`. This matters when a service is called directly, e.g. in tests.
2. Binds `request_id` to structlog contextvars and to `request.state.request_id`.
3. Adds `X-Request-ID` to the response headers.
4. Clears the contextvars at the end of the request.

**Background tasks** (contract extraction, CON-001) explicitly re-bind the originating
`request_id`, plus `contract_id`, so their logs stay traceable to the upload.

## Access log (AC3)

`AccessLogMiddleware` logs `http.access` once per request with `method`, `route` (the route
template, e.g. `/api/invoices/{id}`), `path`, `status`, `duration_ms` (float, 1 decimal) and
`client_ip`. It logs at `warning` for 4xx, `error` for 5xx, and `info` otherwise. `/health`
and `/metrics` are logged at `debug` to avoid noise.

## Errors (AC8)

```python
class AppError(Exception):
    def __init__(self, code: str, message: str, status: int = 400, details: dict | None = None): ...
```

| Exception | HTTP | `code` | `message` (shown to users) |
|---|---|---|---|
| `AppError` | as given | as given | as given |
| `RequestValidationError` | 422 | `VALIDATION_ERROR` | "Some of the information sent was not valid." (field errors in `details`) |
| `StarletteHTTPException` 404 | 404 | `NOT_FOUND` | "We couldn't find what you were looking for." |
| `StarletteHTTPException` 413 | 413 | `FILE_TOO_LARGE` | "This file is too large." |
| Any other `Exception` | 500 | `INTERNAL_ERROR` | "Something went wrong on our side. Please try again." |

Every handler returns the standard body from `architecture.md`, including `request_id`.
Unhandled errors are logged as `http.unhandled_error` with `exc_info`. Stack traces never appear
in the response body.

## Health (AC6)

| Endpoint | Behaviour |
|---|---|
| `GET /health` | Always `200 {"status":"ok","service":"…","version":"…"}`. No dependencies are checked. |
| `GET /ready` | Runs `SELECT 1` with a 2s timeout. contract-service also checks that `ANTHROPIC_API_KEY` is non-empty (no network call). Returns `200 {"status":"ready","checks":{"database":"ok",…}}`, or `503` with the failing checks set to `"fail"`, and logs `db.ready_check_failed`. |

## Metrics (AC7)

`prometheus_client` with one service-level `CollectorRegistry` (module-level, so metrics are
registered once even when tests create several app instances), exposed at `GET /metrics`.

| Metric | Type | Labels | Defined by |
|---|---|---|---|
| `http_requests_total` | Counter | `method`, `route`, `status` | PLT-002 |
| `http_request_duration_seconds` | Histogram | `method`, `route` | PLT-002 |
| `invoice_uploads_total` | Counter | `result` = `success` \| `rejected` \| `error` | INV-001 |
| `invoice_rows_total` | Counter | `outcome` = `created` \| `updated` \| `overwritten` \| `rejected` | INV-001 |
| `contract_uploads_total` | Counter | `result` | CON-001 |
| `contract_extraction_duration_seconds` | Histogram | `model` | CON-001 |
| `contract_extractions_total` | Counter | `result` = `completed` \| `failed` | CON-001 |
| `llm_tokens_total` | Counter | `model`, `direction` = `input` \| `output` | CON-001 |

The `route` label uses the route template, not the raw path, to keep cardinality bounded.
Unmatched paths are labelled `route="unmatched"`.

## Grafana dashboard (AC10)

The dashboard is provisioned from `observability/grafana/dashboards/msme-poc.json` and has
these panels:
1. Requests/s by service
2. Error rate (5xx %) by service
3. p50/p95 latency by route
4. Invoice uploads by result, and rows by outcome
5. Contract extractions by result, and p95 extraction duration
6. LLM tokens per hour

Prometheus scrapes `invoice-service:8002/metrics` and `contract-service:8001/metrics` every 15s.

## Frontend (AC8 UI part, AC11)

This is implemented as part of PLT-001, since that feature scaffolds the frontend:
- The API client turns every non-2xx response into an `ApiError { status, code, message, requestId }`.
- It logs `console.error('[api]', { method, path, status, code, requestId })`.
- `<ErrorAlert>` shows `error.message`. For `INTERNAL_ERROR` or network failures, it shows
  "Something went wrong. Reference: <requestId>".
- A top-level React `ErrorBoundary` logs to the console and shows the same message.

## Configuration

| Variable | Service | Default |
|---|---|---|
| `LOG_LEVEL` | both | `INFO` |
| `SERVICE_VERSION` | both | set at build (`git describe`) |
| `DATABASE_URL` | both | built from `POSTGRES_*` + service user |
| `INVOICE_DB_PASSWORD` / `CONTRACT_DB_PASSWORD` | db, each service | — (required) |
| `GRAFANA_ADMIN_PASSWORD` | grafana | — (required only with the profile) |

## Edge cases & errors

| Case | Behaviour |
|---|---|
| Incoming `X-Request-ID` contains spaces, quotes, or is 500 characters long | Replaced with a fresh ID (gateway and service), preventing log injection |
| DB down at service start | Container keeps retrying migrations with backoff; `/ready` returns 503; gateway returns 502 → UI shows the service-unavailable message (PLT-001-AC10) |
| Exception inside a background task | Caught, logged with the bound `request_id`, and never crashes the worker |
| Very large log value (e.g. a long error from a library) | Truncated to 500 characters by the redaction processor |

## Testing

| AC | Test |
|---|---|
| AC1 | Capture log output; parse each line as JSON; assert the required keys are present |
| AC2 | Request with a valid ID keeps it; missing or malformed ID gets a generated one; the ID appears in the response header, the logs, and the error body |
| AC3 | One `http.access` line per request with status and duration |
| AC5 | Redaction unit test with sensitive keys and long strings |
| AC6 | `/health` 200; `/ready` 200 with DB up; 503 with the DB URL pointed at a closed port |
| AC7 | Hit a route, scrape `/metrics`, assert the counter incremented with the route-template label |
| AC8 | Route raising `RuntimeError` → 500 with standard body + `request_id`, no stack trace in body, `exc_info` in log |
| AC9 | `LOG_LEVEL=WARNING` suppresses info lines |
| AC2 + AC10 | Smoke script `scripts/smoke.sh`: `docker compose up`, call through the gateway, assert the header echo, and check Prometheus targets are `up` |

The test database is the compose `db` service. `pytest` creates a throwaway schema per test run
and drops it afterwards.
