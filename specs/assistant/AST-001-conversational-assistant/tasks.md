---
id: AST-001
title: Conversational AI assistant — tasks
status: approved
design: ./design.md
---

# AST-001 — Tasks

Branch: `feat/AST-001-conversational-assistant` (the pre-assistant version is tagged `v1.0-poc`).

## A. Service foundation

- [ ] 1. `services/assistant-service` skeleton (copy of the service template; `app/core`
       identical; no DB/migrations); compose service (8003), gateway route with buffering off,
       Prometheus target, `/ready` checks (key, downstream health) — _AC12, AC14_
- [ ] 2. Settings + `.env.example` (`ASSISTANT_LLM`, `ASSISTANT_LLM_MODEL`, `ASSISTANT_LLM_EFFORT`,
       downstream URLs)

## B. Assistant core

- [ ] 3. `tools.py`: five read-only tools (strict schemas), httpx client with X-Request-ID,
       trimmed results with app links, fixed status labels, `is_error` on failures — _AC5–AC7_
- [ ] 4. `prompt.py` (system prompt + today) — _AC5, AC9, AC10_
- [ ] 5. `claude.py` streaming step; `loop.py` (≤ 8 lookups, parallel tool calls, final answer
       when the limit is hit, cancellation) — _AC4, AC5, AC15_
- [ ] 6. `chat.py`: request validation, SSE events, error mapping, disconnect → cancel — _AC4, AC12_
- [ ] 7. `fake.py` deterministic stand-in model using the real tools — (tests/e2e)
- [ ] 8. Logs + metrics without question/answer text — _AC14_
- [ ] 9. Tests: scripted-Claude loop, tools against mocked APIs, SSE sequence, errors, limits,
       log privacy; opt-in live eval (`-m llm`) with golden questions — _AC4–AC15_

## C. Frontend

- [ ] 10. `lib/api/sse.ts`: POST + streamed SSE parsing with AbortController
- [ ] 11. `modules/assistant`: registry entry (ASSISTANT group, Talk to Me) + route — _AC1_
- [ ] 12. `useConversation` (sessionStorage, send, stop, retry, new) — _AC4, AC8, AC12_
- [ ] 13. Page: welcome + suggestions, message list (`role="log"`), lookups, Markdown answer
        (react-markdown + remark-gfm, in-app links only), Copy, sticky composer (auto-grow,
        Enter/Shift+Enter, counter, Send/Stop), disclaimer, live-region announcement,
        focus handling — _AC2–AC4, AC6, AC7, AC9, AC11, AC13, AC16_
- [ ] 14. Vitest for the hook and page.

## D. Verify & release

- [ ] 15. `scripts/e2e.sh`: assistant in fake mode + safety check; Playwright spec (suggestion →
        answer with links → follow-up → Stop → New conversation; axe; phone width).
- [ ] 16. Live eval with the real model on the sample data; screenshots; update the Grafana
        dashboard.
- [ ] 17. Docs (README, CLAUDE.md, architecture.md, product.md); set statuses `implemented`; on
        approval merge to `main` and tag `v1.1-assistant`.
