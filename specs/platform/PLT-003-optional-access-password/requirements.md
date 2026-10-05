---
id: PLT-003
title: Optional access password for public exposure
status: implemented
depends_on: [PLT-001, PLT-002]
---

# PLT-003 — Optional access password for public exposure

## Goal

The owner can put the app on a public URL (for example through a Cloudflare tunnel) without
leaving their invoices, contracts and AI credits open to anyone who finds the link. When
`ACCESS_PASSWORD` is set, the gateway asks for a username and password first. When it isn't, the app
behaves exactly as before.

## User stories

- As the owner, I want to share a public link that only people I give the password to can use, so
  that strangers cannot read my data, upload files or spend my Claude API credits.
- As a developer, I want local use to stay frictionless, so that nothing changes unless I opt in.
- As the owner, I want the tunnel to refuse to start when the password is not in force, so that I
  cannot expose the app by mistake.

## Acceptance criteria

| ID | Criterion |
|---|---|
| PLT-003-AC1 | WHEN `ACCESS_PASSWORD` is set THE SYSTEM SHALL require HTTP Basic credentials (user name `ACCESS_USERNAME`, default `user`, and that password) on every request to the gateway except `/healthz`. A missing or wrong login SHALL get `401` with a `WWW-Authenticate` header, and the request SHALL NOT reach any service. |
| PLT-003-AC2 | WHEN `ACCESS_PASSWORD` is not set THE SYSTEM SHALL behave as before, with no prompt on any path. |
| PLT-003-AC3 | IF `ACCESS_PASSWORD` is set but shorter than 12 characters, or `ACCESS_USERNAME` contains a colon or whitespace, THEN THE SYSTEM SHALL refuse to start the gateway and say why. A weak password on a public address is worse than a clear failure. |
| PLT-003-AC4 | THE SYSTEM SHALL keep the password only in `.env` and, inside the gateway, only as a bcrypt hash. It SHALL NOT appear in logs, the image, or any response, and the access log SHALL record no credentials or user names. |
| PLT-003-AC5 | THE SYSTEM SHALL keep `/healthz` open, so container and load-balancer health checks keep working. |
| PLT-003-AC6 | WHEN a person has entered the password once in their browser THE SYSTEM SHALL let them use the whole app: pages, uploads, downloads and the streamed Talk to Me answers. |
| PLT-003-AC7 | THE SYSTEM SHALL provide `scripts/tunnel.sh`, which starts a public Cloudflare quick tunnel to the gateway **only if** the gateway is answering `401` to an unauthenticated request. Otherwise it SHALL stop with an explanation. |
| PLT-003-AC8 | THE SYSTEM SHALL keep `scripts/e2e.sh` from running while a tunnel is up, and SHALL run the tests with the password off, then restore the configured password afterwards. |
| PLT-003-AC9 | THE SYSTEM SHALL document the settings in `.env.example` and the public-access steps and limits in `CLAUDE.md`. |

## Out of scope

- User accounts, roles, per-user passwords, password reset or sessions. This is one shared password
  at the front door (the product still has no users, per `product.md`).
- Rate limiting or lockout of wrong guesses. A long random password plus Cloudflare's own protection
  covers the POC. Cloudflare Access is the upgrade path for a proper login.
- HTTPS: Cloudflare terminates it. Basic credentials must not be used over plain `http` on a network
  you do not control.
- Managing the Cloudflare account, domain or a permanent named tunnel (steps are in `CLAUDE.md`).

## Open questions

- None. Decided 2026-10-05 with the owner: quick tunnel plus this password gate, because it needs
  no Cloudflare account or domain.
