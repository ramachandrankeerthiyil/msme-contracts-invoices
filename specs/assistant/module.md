---
id: ASSISTANT
title: Assistant module
status: approved
---

# Assistant module

**Service:** `services/assistant-service` · **DB schema:** none · **API base:** `/api/assistant`

A conversational AI ("Talk to Me") that answers questions about the user's contracts and invoices by
calling those modules' public read APIs as tools (ADR-0003). It owns no business data and applies
no business rules of its own: statuses, risks and totals come from the contract and invoice
services, so its answers always match the screens.

## Features

| ID | Feature | Status |
|---|---|---|
| AST-001 | Conversational assistant ("Talk to Me") | approved |

## Rules

- **Read-only.** The assistant can look things up but can never change data.
- **Grounded.** Answers use only lookup results. When the data doesn't say, the assistant says so.
- **Checkable.** Every record mentioned links to its page, and the lookups used are shown.
- **Private by default.** Conversations live in the browser tab. The server stores no
  conversation text and logs no question or answer text.
