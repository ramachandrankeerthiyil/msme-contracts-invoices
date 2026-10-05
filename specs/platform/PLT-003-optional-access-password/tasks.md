---
id: PLT-003
title: Optional access password for public exposure — tasks
status: implemented
design: ./design.md
---

# PLT-003 — Tasks

Branch: `feat/PLT-003-optional-access-password`. Commit prefix: `feat(platform): … [PLT-003]`.

- [x] 1. `gateway/40-access-password.sh`, `Dockerfile` (htpasswd, script, default `access.conf`),
       `nginx.conf` include and open `/healthz` — _AC1–AC5_
- [x] 2. `docker-compose.yml` gateway environment; `.env.example` — _AC1, AC9_
- [x] 3. `scripts/gateway-access-test.sh` (real HTTP against the gateway image, three setups) —
       _AC1–AC5_
- [x] 4. `scripts/tunnel.sh` (refuses unless the gateway answers 401; starts the quick tunnel) —
       _AC7_
- [x] 5. `scripts/e2e.sh`: abort while a tunnel is up, force the password off, restore it after;
       `scripts/smoke.sh` sends the login — _AC8_
- [x] 6. `CLAUDE.md` and `architecture.md` (security) — _AC9_
- [x] 7. Run `gateway-access-test.sh`; run `e2e.sh`; start the tunnel and check it from outside
       (`curl`, then the browser) — _AC1, AC6, AC7, AC8_
- [x] 8. Set statuses to `implemented`; fill in Verification

## Verification (2026-10-05)

- `scripts/gateway-access-test.sh`: 22 checks passed (AC1–AC5): 401 and a Basic challenge for
  missing, wrong-password and wrong-user logins on `/`, `/api/invoices` and `/api/assistant/chat`;
  the right login passes through; `/healthz` stays open; only a bcrypt hash is stored and the
  password is in no log line, no image layer and not in the access log; an 11-character password
  and a user name with a colon or a space stop the gateway at start; 12 characters is accepted.
- `scripts/e2e.sh`: 68 Playwright tests passed with the password forced off, and the gateway asked
  for the password again afterwards. With a process named `cloudflared` running, `e2e.sh` aborted
  with a non-zero exit (AC8). Its guard uses `ps`, not `pgrep`, which did not see running processes
  under this WSL.
- Live tunnel (AC6, AC7): `scripts/tunnel.sh` started only after the gateway answered 401. Over the
  public address: no login or a wrong password gives 401 on the page, the API and Talk to Me; the
  right login gives 200 for the page and the API; Mailpit is not reachable; a streamed Talk to Me
  question came back through the tunnel (declined by the real guard model).
- **Not done:** the browser sign-in prompt and an upload through the tunnel were not exercised in a
  browser (the browser pane cannot be given the password). They rely on the browser sending Basic
  credentials with same-origin requests, which `curl -u` imitates.
- Seen once on a fresh quick tunnel: Cloudflare `530 Origin DNS error` for a few requests in the
  first seconds. It cleared within a minute.
