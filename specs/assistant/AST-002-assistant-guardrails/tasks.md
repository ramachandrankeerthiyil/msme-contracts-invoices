---
id: AST-002
title: Assistant guardrails and app guide — tasks
status: implemented
design: ./design.md
---

# AST-002 — Tasks

Branch: `feat/AST-002-assistant-guardrails`. Commit prefix: `feat(assistant): … [AST-002]`.
Specs first (ADR-0005, AST-002, AST-001 amendments). Test names contain the AC ID.

## A. Guard and replies

- [x] 1. `config.py`: `ASSISTANT_GUARD_MODEL`, `INVOICE_AT_RISK_DAYS`, `CONTRACT_AT_RISK_DAYS`;
       compose and `.env.example` — _AC8, AC16_
- [x] 2. `guard.py`: `Intent`, `GuardDecision`, `ClaudeGuard` (JSON schema, 5 s, no retries, context
       from the last turns), `KeywordGuard` — _AC2, AC10, AC12, AC16, AC18_
- [x] 3. `refusals.py`: the fixed replies — _AC3–AC6_
- [x] 4. Tests: `ClaudeGuard` with a stubbed client, `KeywordGuard` table, replies — _AC3–AC6,
       AC10, AC12, AC16, AC18_

## B. Guide and prompt

- [x] 5. `app_guide.py`: `build_guide(invoice_days, contract_days)` — _AC7–AC9_
- [x] 6. `prompt.py`: Scope section, configured days, guide block, intent hint — _AC8, AC11, AC13_
- [x] 7. `loop.py`: pass the intent; no tools for `about_app`; `fake.py`: about-app answer —
       _AC7, AC18_
- [x] 8. Tests: guide coverage, configured numbers, prompt sections and block order — _AC7–AC9,
       AC11, AC13_

## C. Wiring and observability

- [x] 9. `chat.py`: run the guard first; declined → one `text` + `done` (`declined`); fall open on
       `None`; logs and metrics; `main.py` builds `app.state.guard`; `telemetry.py` counter —
       _AC2, AC12, AC15_
- [x] 10. API tests with a scripted guard: no main-model or downstream call when declined,
        `about_app` has no tools and has the guide, fall-open cases, log privacy, counters —
        _AC1–AC3, AC7, AC12, AC15, AC17_
- [x] 11. Live eval golden questions added to `test_live_llm.py` (opt-in) — _AC1–AC11_

## D. Frontend

- [x] 12. `AssistantPage`: two new suggestions, welcome text, subtitle; `Composer`: label —
        _AC14_
- [x] 13. Vitest updates (suggestions, label, a declined reply renders and can be copied) —
        _AC14, AC17_
- [x] 14. Playwright: app question answered; off-topic and manipulation declined; the declined
        reply is copyable; axe — _AC1, AC3, AC6, AC7, AC14, AC17_

## E. Verify and document

- [x] 15. Run `docker compose run --rm --build assistant-service pytest` and `ruff check .`;
        frontend `npm test`, `npm run lint`, typecheck; `scripts/e2e.sh`
- [x] 16. Update `assistant/module.md`, `architecture.md`, `product.md`, `CLAUDE.md`; set AST-001
        and AST-002 to `implemented`; fill in Verification below

## Verification (2026-10-05)

- assistant-service: 165 tests passed (11 opt-in live tests skipped); `ruff check` clean. New tests
  cover AST-002 AC1–AC13 and AC15–AC18: intents, `ClaudeGuard` request and every failure kind (with a
  stubbed API), the keyword stand-in (28 questions), the fixed replies, the app guide, the
  instructions, and the API behaviour with a scripted guard.
- Frontend: 170 unit tests passed; typecheck, ESLint and the design-token check clean.
- End to end: 68 Playwright tests passed (`scripts/e2e.sh`, stand-in guard and model): the app
  question is answered from the guide with no lookups; off-topic, override and change-data requests
  get their fixed replies; the conversation carries on after a decline; axe clean.
- **Not run: the live eval.** `pytest -m llm` (real guard and main model, a few rupees per run) now
  holds golden questions for every intent, but it was not run in this session, so the real
  Haiku guard's labelling quality is unverified. Run it with the demo data loaded before relying on
  the guard in front of real users:
  `docker compose run --rm -e RUN_LLM_TESTS=1 assistant-service pytest -m llm -s`
- Decision during testing: the shared `ruff format` rewrote unrelated assistant files, so those
  were restored and only the intended edits kept (this service's baseline is `ruff check`, not
  `ruff format`).
