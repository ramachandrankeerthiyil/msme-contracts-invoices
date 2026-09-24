---
id: ADR-0001
title: Technology stack for the POC
status: accepted
date: 2026-09-24
---

# ADR-0001 — Technology stack for the POC

## Context

We need a three-tier, API-driven web app: web front end, business logic in microservices, and a
PostgreSQL database. It is a POC, so there are no scale or concurrency requirements. The work is
heavy on document parsing (PDF, Word, Excel) and AI extraction, and the UI must look professional
and be accessible to users over 60.

## Decision

- **Frontend:** React + TypeScript + Vite, styled with Tailwind CSS and shadcn/ui components,
  plus TanStack Query (server state), TanStack Table (lists) and Recharts (dashboard charts).
- **Gateway:** Nginx as the single entry point, routing to the frontend and the services.
- **Services:** Python 3.12 + FastAPI, one service per module (`contract-service`,
  `invoice-service`), using SQLAlchemy 2 + Alembic.
- **Database:** a single PostgreSQL 16 instance with one schema and one DB user per service.
- **Runtime:** Docker Compose. `docker compose up` runs everything.

## Alternatives considered

- **Node/NestJS services:** a good fit for a single-language stack, but Python's PDF, Word and
  Excel libraries are more mature, which matters most here.
- **Next.js full stack:** it would blur the required tier separation.
- **Separate database per service:** stronger isolation, but unnecessary overhead for a POC.
  Separate schemas and users give the same independence guarantees.
- **Material UI / Ant Design:** heavier and harder to restyle to a custom light-blue design system.

## Consequences

- There are two languages (TypeScript and Python). API types are generated from FastAPI's OpenAPI
  output to keep them in sync.
- Moving to separate databases later is straightforward, because services never cross schemas.
