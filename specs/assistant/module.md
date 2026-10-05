---
id: ASSISTANT
title: Assistant module
status: implemented
---

# Assistant module

**Service:** `services/assistant-service` · **DB schema:** none · **API base:** `/api/assistant`

A conversational AI ("Talk to Me") that answers questions about the user's contracts and invoices by
calling those modules' public read APIs as tools (ADR-0003), and explains what the app is and how it
works. It answers nothing else (AST-002, ADR-0005). It owns no business data and applies
no business rules of its own: statuses, risks and totals come from the contract and invoice
services, so its answers always match the screens.

## Features

| ID | Feature | Status |
|---|---|---|
| AST-001 | Conversational assistant ("Talk to Me") | implemented |
| AST-002 | Guardrails and app guide (amends AST-001) | implemented |

## Rules

- **On topic only.** It answers questions about the user's contracts and invoices, and about what
  this app is and how it works. Everything else is politely declined by a guard that runs before
  the main model, with fixed replies, and the model's own instructions enforce the same boundary.
- **Read-only.** The assistant can look things up but can never change data.
- **Grounded.** Answers use only lookup results. When the data doesn't say, the assistant says so.
- **Checkable.** Every record mentioned links to its page, and the lookups used are shown.
- **Private by default.** Conversations live in the browser tab. The server stores no
  conversation text and logs no question or answer text.
