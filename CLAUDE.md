# MSME Contracts & Invoices — POC

A proof-of-concept web app that lets small businesses (MSMEs) upload contracts (PDF/Word) and
invoice spreadsheets (Excel), and see the results on two dashboards.

## Spec-driven development — read this first

- `specs/` is the source of truth. Before writing code, read `specs/README.md`, the relevant
  `module.md`, and the feature folder you are working on.
- Only implement a feature whose `requirements.md` **and** `design.md` have `status: approved`.
- Work through the feature's `tasks.md` in order and tick items off as they are completed.
- If the code and a spec disagree, stop and propose a spec change — do not silently diverge.
- Put the feature ID in branch names and commit messages (see `specs/README.md#git-workflow`).

## Architecture (details: `specs/architecture.md`)

```
Browser ──► gateway (Nginx) ──► frontend (React static build)
                             ├─► contract-service (FastAPI) ──► PostgreSQL schema `contracts`
                             └─► invoice-service  (FastAPI) ──► PostgreSQL schema `invoices`
```

- The two services are independent: they never call each other or read each other's schema.
- All business rules (statuses, risk flags, dashboard numbers) live in the services, not the UI.

## Conventions

- **Backend:** Python 3.12, FastAPI, SQLAlchemy 2, Alembic, Pydantic v2, pytest, ruff.
- **Frontend:** TypeScript (strict), React + Vite, Tailwind + shadcn/ui, TanStack Query & Table,
  Recharts, Vitest, Playwright.
- **UI:** every colour, font size and spacing value comes from `specs/ui-design-system.md` tokens.
  No ad-hoc colours or font sizes.
- **Logging:** structured JSON logs with a request ID on every line (`specs/platform/PLT-002`).
- **Secrets:** live in `.env` (never committed). Document every new variable in `.env.example`.

## Commands

Everything runs in Docker (Docker Desktop with WSL integration). Copy `.env.example` to `.env` first.

```bash
docker compose up -d --build                         # whole stack → http://localhost:8080
docker compose --profile observability up -d --build # + Prometheus :9090, Grafana :3001
docker compose logs -f invoice-service               # JSON logs; grep by request_id
scripts/smoke.sh [--observability]                   # end-to-end smoke test (PLT-002)

# Tests / lint for one service (uses the separate <db>_test database)
docker compose run --rm --build invoice-service pytest
docker compose run --rm --build invoice-service ruff check .

# Frontend (Node runs in a container; no local install needed)
docker compose --profile dev up frontend-dev         # Vite hot reload → http://localhost:5173
docker compose run --rm frontend-dev npm test        # unit tests (Vitest)
docker compose run --rm frontend-dev npm run lint    # ESLint + design-token check
docker compose --profile e2e run --rm e2e            # Playwright e2e + axe, against :8080 stack

# Demo data (dates relative to today) → samples/
docker run --rm -u "$(id -u):$(id -g)" -e HOME=/tmp -v "$PWD":/work -w /work python:3.12-slim \
  sh -c "pip install -q --target /tmp/py openpyxl python-docx && PYTHONPATH=/tmp/py python scripts/make_samples.py"

# New migration (after changing models)
docker compose run --rm invoice-service alembic revision --autogenerate -m "describe change"
```

- Service API docs: `http://localhost:8080/api/invoices/docs`, `…/api/contracts/docs`.
- `/health`, `/ready`, `/metrics` are internal only (not routed by the gateway).
- `app/core/` is intentionally duplicated in both services — change both copies together.
- Frontend: new pages plug in via the module registry (`frontend/src/app/modules.ts`) and route
  `handle` (title, crumb, parents, action). Only `src/styles/tokens.css` may contain raw colours
  or px sizes (`scripts/check-tokens.mjs` enforces this).
