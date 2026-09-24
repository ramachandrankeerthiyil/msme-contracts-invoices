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

_To be filled in when the services are scaffolded (`docker compose up`, tests, lint, migrations)._
