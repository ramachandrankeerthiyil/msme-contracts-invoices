---
id: PLT-003
title: Optional access password for public exposure — design
status: implemented
requirements: ./requirements.md
---

# PLT-003 — Design

## Overview

```
Internet ──HTTPS──► Cloudflare ──tunnel──► cloudflared (this machine) ──http──► gateway :8080
                                                                               │  ACCESS_PASSWORD set?
                                                                               │   yes: Basic auth on everything but /healthz
                                                                               │   no:  open, as before
                                                                               ▼
                                                                  frontend · /api/* services
```

The check lives in the **gateway** (Nginx), the single entry point (`architecture.md`), so the
services, their tests and the frontend are untouched, and every path (pages, `/api/*`, uploads,
downloads, the streamed assistant) is covered by one rule.

## Gateway changes

- `gateway/Dockerfile` adds `apache2-utils` (for `htpasswd`) and a start-up script,
  `gateway/40-access-password.sh`, copied to `/docker-entrypoint.d/` (the official Nginx image runs
  these before starting Nginx). It also ships a default `/etc/nginx/access.conf` containing
  `auth_basic off;`, so the include below always resolves.
- `gateway/nginx.conf`: in the `server` block, `include /etc/nginx/access.conf;` (so it applies to
  every location), and `auth_basic off;` inside `location = /healthz` (AC5).
- **`40-access-password.sh`** runs as root at start:
  1. If `ACCESS_PASSWORD` is empty: leave the default `auth_basic off;` and exit (AC2).
  2. Validate (AC3): the password is at least 12 characters; the user name (default `user`) has no
     `:` or whitespace. Otherwise print `ACCESS_PASSWORD must be at least 12 characters…` (or the
     user-name message) to stderr and exit 1, so the container stops instead of starting weak.
  3. `htpasswd -nbB "$user" "$password" > /etc/nginx/htpasswd` (bcrypt) and write
     `/etc/nginx/access.conf` as `auth_basic "MSME Contracts & Invoices";` +
     `auth_basic_user_file /etc/nginx/htpasswd;` (AC1, AC4).
  The password is never echoed.
- The JSON access log already records no headers and no `$remote_user` (PLT-002 AC3), so no login
  or user name reaches it (AC4). Nginx's error log names the user on a failed attempt but never the
  password.
- `docker-compose.yml`: the gateway receives `ACCESS_USERNAME` (default `user`) and
  `ACCESS_PASSWORD` (default empty). `.env.example` documents both and how to make a good password.

## Browser behaviour (AC6)

A `401` with `WWW-Authenticate: Basic` makes the browser show its own sign-in box once. It then
sends the credentials with every request to the same address: page loads, `fetch` calls, uploads,
file downloads and the assistant's streamed `fetch`. No change to the frontend is needed.

## Public access (AC7)

`scripts/tunnel.sh`:

1. Finds `cloudflared` (on `PATH`, or `~/bin/cloudflared`); otherwise explains how to install it.
2. Requests `http://localhost:8080/` **without credentials**. If the answer is not `401` it stops:
   "The gateway is not asking for a password. Set ACCESS_PASSWORD in .env and run
   `docker compose up -d gateway`." Nothing is exposed.
3. Runs `cloudflared tunnel --no-autoupdate --url http://localhost:8080`, which prints a
   `https://<random>.trycloudflare.com` address. It runs until stopped (Ctrl+C), and the address
   stops working then. A new run gives a new address.

`scripts/e2e.sh` (AC8): refuses to start if a `cloudflared` process is running (it recreates the
gateway without the password for the run, which would open a public link); exports
`ACCESS_PASSWORD=` for the run; and, in its cleanup, recreates the gateway with the `.env` values
again. `scripts/smoke.sh` sends the login when `ACCESS_PASSWORD` is in its environment.

### Going further (not built here)

- **A permanent address:** create a *named* tunnel in the Cloudflare dashboard on a domain you
  own and route it to `http://localhost:8080`. Run it with `cloudflared tunnel run <name>`.
- **A real login instead of a shared password:** put **Cloudflare Access** (Zero Trust) in front
  of that hostname, with an email one-time-code policy. Free for small teams. Then the gateway
  password can stay on as a second lock or be removed.

## Edge cases

| Case | Behaviour |
|---|---|
| Password set, wrong or no login | `401`, `WWW-Authenticate`, nothing proxied |
| Password shorter than 12 characters | Gateway exits at start with a clear message |
| User name with a colon (`a:b`) | Gateway exits at start with a clear message |
| Password containing `$`, quotes or spaces | Passed to `htpasswd` as an argument (no shell expansion), so it works |
| Gateway restarted | The hash is rebuilt from the environment at every start |
| Service down while password is set | Unauthenticated callers still get `401`, not a `503`, so nothing about the stack leaks |
| `/healthz` | Always `200 ok` |
| Tunnel started with no password in force | `tunnel.sh` stops before exposing anything |
| Password changed in `.env` | Takes effect after `docker compose up -d gateway` |

## Testing

The gateway starts without its upstream services (it resolves them per request), so it is tested
on its own, with real HTTP, by `scripts/gateway-access-test.sh`. It builds the gateway image and
runs it three ways: no password, a good password, and bad configuration. Each check prints its AC
ID.

| AC | Check |
|---|---|
| AC1 | With a password: `/`, `/api/invoices` and `/api/assistant/chat` answer `401` with `WWW-Authenticate: Basic`; a wrong password and a wrong user name answer `401`; the right login is not `401` (it passes through; with no upstream it is the gateway's own `503`) |
| AC2 | Without a password: `/` and `/api/invoices` are not `401` |
| AC3 | Passwords of 11 characters, a user name `a:b` and one with a space: the container exits non-zero with the message; 12 characters starts |
| AC4 | The password is not in the container's environment dump of the image layers (`docker history`), not in `docker logs`, and `/etc/nginx/htpasswd` holds a `$2y$` bcrypt hash and not the password; the access log lines for a login contain no `Authorization` value or user name |
| AC5 | `/healthz` is `200 ok` with and without a login |
| AC6 | Manual, on the live tunnel: the browser prompts once, then pages, an upload and a streamed Talk to Me answer work. Plus a scripted `curl -u` over the tunnel for a page and an API call |
| AC7 | `tunnel.sh` with the gateway open: exits non-zero, starts no `cloudflared`. With the password on: starts and prints a `trycloudflare.com` address |
| AC8 | `e2e.sh` with a fake `cloudflared` process running: aborts. A normal e2e run still passes, and the gateway asks for the password again afterwards |
| AC9 | `.env.example` has both variables; `CLAUDE.md` has the steps |
