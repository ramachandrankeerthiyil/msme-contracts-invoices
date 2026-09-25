---
id: ADR-0003
title: Conversational assistant as a separate service using tools over the existing APIs
status: proposed
date: 2026-09-25
---

# ADR-0003 — Conversational assistant as a separate service using tools over the existing APIs

## Context

AST-001 asks for a chat that answers questions about **both** contracts and invoices from live
data. The two business services are deliberately independent (architecture rules 1–2). The Claude
API key must stay on the server. Answers must be accurate, current (statuses depend on today's
date) and checkable.

## Decision

1. **A new `assistant-service`** (FastAPI, same skeleton and `app/core` as the others), behind
   the gateway at `/api/assistant`. It owns no business data and has no database schema.
2. **Claude with tool use, not a database or search index of its own.** The assistant is given
   five **read-only tools**, each a thin wrapper over an existing public API (e.g. `GET
   /api/invoices?view=…`, `GET /api/contracts/{id}`). The model decides which to call.
   Business rules stay where they live: the assistant reuses the services' own status and risk
   logic, so its answers always match the screens.
3. **A deliberate, narrow exception to "services never call each other":** assistant-service is a
   *consumer* of the other services' public read APIs, exactly like the browser is. The contract
   and invoice services know nothing about it and are unchanged. They still never call each other.
4. **A hand-written tool loop with streaming** (Messages API `stream` + `get_final_message`, up to
   8 tool calls per question) rather than the SDK's beta tool runner. We need token streaming to
   the browser, visible "looking up…" steps, a hard step limit and request-ID propagation to the
   downstream calls, so owning the loop is simpler. Tools use `strict: true` JSON schemas.
5. **Server-Sent Events** from `POST /api/assistant/chat` to stream the answer. The conversation
   is kept by the browser (tab session) and sent with each question, so the server stays
   stateless and stores no conversation text.
6. **Model: `ASSISTANT_LLM_MODEL`, default `claude-sonnet-5`** (pending confirmation), with
   adaptive thinking and `effort: medium` for chat responsiveness. There is also a deterministic
   **stand-in model** (`ASSISTANT_LLM=fake`) that calls the real tools, so tests and e2e runs never
   use the paid API.

## Alternatives considered

- **Text-to-SQL over both schemas:** breaks service independence, duplicates business rules
  (status, at risk) in generated SQL, and is risky.
- **RAG over document text:** the questions are mostly about structured status data, which RAG
  answers poorly. Contract details (risks, terms) are already extracted and available through the
  API.
- **Putting the chat logic in contract- or invoice-service:** would couple one service to the
  other's data.
- **The SDK's beta tool runner:** less code, but it hides the per-step streaming and limits we
  want to control.

## Consequences

- One more container. The gateway needs response buffering turned off for the streaming route.
- The assistant only knows what the APIs return. That is a feature: answers can't disagree with
  the screens.
- Question text is sent to Claude, as contract text already is (ADR-0002). This is acceptable for
  the POC.
- **Approximate cost per question** with Sonnet 5: a few thousand input tokens (instructions,
  tool definitions, lookup results) plus a few hundred output tokens, roughly ₹1–3. Logged and
  graphed like extraction.
