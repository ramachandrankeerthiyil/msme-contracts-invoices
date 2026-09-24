---
id: PLT-002
title: Logging and observability — tasks
status: approved
design: ./design.md
---

# PLT-002 — Tasks

Branch: `feat/PLT-002-observability-foundation`

**Prerequisite:** Docker Desktop, with WSL integration enabled for the Ubuntu distro. All Python
runs inside containers, so no local Python 3.12 is needed. Tests run with
`docker compose run --rm <service> pytest`.

## A. Foundation

- [ ] 1. `docker-compose.yml` with `db`, both services, `gateway`, and a `frontend` placeholder;
       volumes `pgdata` and `uploads`; healthchecks; only 8080 (and 5432 on localhost) exposed.
- [ ] 2. `db/init/01-schemas.sh`: create the `invoices` and `contracts` schemas and the
       `invoice_svc` / `contract_svc` users, each owning only its own schema.
       Add the new variables to `.env.example`.
- [ ] 3. invoice-service skeleton: `Dockerfile` (python:3.12-slim + uv), `pyproject.toml`,
       `app/main.py` with `create_app()`, `config.py`, `db.py` (search_path = `invoices`), and an
       Alembic env with the version table in the `invoices` schema; the entrypoint runs
       `alembic upgrade head` and then uvicorn.
- [ ] 4. Test harness: `tests/conftest.py` with an app client and a per-run throwaway schema;
       ruff config; a `make`-style script or README commands for test/lint.

## B. Observability core (invoice-service first)

- [ ] 5. `core/logging.py`: structlog JSON config, stdlib bridging, `LOG_LEVEL`, and the
       redaction processor. — _AC1, AC5, AC9_
- [ ] 6. `core/request_context.py`: request-ID middleware (validate / generate / bind / echo / clear). — _AC2_
- [ ] 7. `core/access_log.py`: one `http.access` line per request, with level by status. — _AC3_
- [ ] 8. `core/errors.py`: `AppError` plus handlers producing the standard error body. — _AC8_
- [ ] 9. `core/metrics.py`: registry, HTTP counter + histogram (route-template label), and `/metrics`. — _AC7_
- [ ] 10. `core/health.py`: `/health` and `/ready` (DB check with a 2s timeout). — _AC6_
- [ ] 11. Tests for tasks 5–10 (see the design's Testing table). Names include the AC IDs. — _AC1–AC3, AC5–AC9_

## C. contract-service

- [ ] 12. Copy the skeleton and `app/core/` to contract-service (port 8001, schema `contracts`).
       `/ready` also checks that `ANTHROPIC_API_KEY` is set. Copy the tests. — _AC6_

## D. Gateway

- [ ] 13. `gateway/nginx.conf` + `Dockerfile`: request-ID map, JSON access log, routes, 21 MB
       body limit, `/healthz`, and the `X-Request-ID` response header. — _AC2, AC3_

## E. Observability profile

- [ ] 14. `observability/prometheus.yml` scraping both services; add `prometheus` and `grafana`
       under `profiles: [observability]`. — _AC10_
- [ ] 15. Grafana provisioning (datasource + dashboard JSON with the 6 panels from the design). — _AC10_

## F. Verify & document

- [ ] 16. `scripts/smoke.sh`: bring the stack up, call `/api/invoices/…` through the gateway,
       assert the `X-Request-ID` echo and the matching service log line, and check that the
       Prometheus targets are up. — _AC2, AC10_
- [ ] 17. Fill in the `CLAUDE.md` "Commands" section and the README "Getting started" section.
- [ ] 18. Set `status: implemented` on the requirements, design and tasks; commit and merge.

The business events in AC4 are delivered with their features (INV-001, CON-001). This feature
provides the logging mechanism and the event-naming convention.
