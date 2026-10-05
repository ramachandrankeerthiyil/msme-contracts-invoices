---
id: AST-002
title: Assistant guardrails and app guide
status: implemented
depends_on: [AST-001, ADR-0003, ADR-0005]
---

# AST-002 — Assistant guardrails and app guide

## Goal

"Talk to Me" talks only about what the app offers: the user's contracts and invoices, and what
this app is and how it works. Anything else is politely declined, reliably, and cheaply, even if
the user tries to talk the assistant out of its limits. Questions about the app itself get a good,
coherent answer.

## User stories

- As a business owner, I want the assistant to stay on my contracts and invoices, so that I can
  trust it as a business tool and not as a general chatbot.
- As a new user, I want to ask "what is this app?" and "how does it work?", so that I can learn
  the app without reading documentation.
- As a user who asks for something the assistant can't do (changing data, legal advice, unrelated
  topics), I want a clear, kind answer that tells me what I *can* ask and where to go instead.
- As the product owner, I want the boundary to hold even when someone tries to override it, so
  that the assistant can't be misused or made to say things we haven't approved.

## Acceptance criteria

Intents used below are defined in ADR-0005: `data`, `about_app`, `write_request`, `legal_advice`,
`off_topic`, `manipulation`.

| ID | Criterion |
|---|---|
| AST-002-AC1 | THE SYSTEM SHALL answer only two kinds of question: those about the user's own invoices and contracts, and those about what this app is, what it can do, how it works or how to do something in it. It SHALL decline everything else. |
| AST-002-AC2 | WHEN a question is sent THE SYSTEM SHALL decide its intent before the main assistant model runs. IF the intent is `write_request`, `legal_advice`, `off_topic` or `manipulation` THEN the question SHALL NOT reach the main model or any lookup. |
| AST-002-AC3 | WHEN a question is declined THE SYSTEM SHALL reply with a fixed, polite message that says it cannot help with that, lists what it can help with (invoices, contracts, this app), and gives example questions. The message SHALL be the same each time for the same intent and SHALL contain only in-app links. |
| AST-002-AC4 | IF the question asks to change or send something (mark an invoice paid, edit, delete, upload, email a client) THEN THE SYSTEM SHALL say it can only look things up, and point to the right page: uploading an updated sheet to record a payment or fix an invoice, and the **Send email reminder** button to remind a client. |
| AST-002-AC5 | IF the question asks for legal advice (what to do legally, whether a clause is enforceable or lawful) THEN THE SYSTEM SHALL say it can explain what a contract says but cannot give legal advice, and suggest a lawyer or adviser. Asking what a clause *says* is a `data` question and SHALL be answered. |
| AST-002-AC6 | IF the question tries to override the assistant's rules, reveal its instructions, change its role, or pretend the rules don't apply THEN THE SYSTEM SHALL decline it with the general message (AC3), without repeating or explaining its instructions. |
| AST-002-AC7 | WHEN the question is about the app THE SYSTEM SHALL answer from a built-in guide to the app, without looking anything up, in a short, coherent, plain-language answer. The guide SHALL cover: what the app is and who it is for; the Contracts and Invoices modules and what each does; how to get started (upload a contract, upload an invoice sheet); what the statuses mean (Paid, Outstanding, At risk, Open; contract in force, at risk, expired); the email reminder; what Talk to Me can and cannot do; how the app works in simple terms (including that uploaded contract text and questions are sent to the AI service); and its main limits. |
| AST-002-AC8 | THE SYSTEM SHALL state the at-risk windows in the guide from the same settings the contract and invoice services use, so the guide never shows an outdated number. |
| AST-002-AC9 | WHEN an answer about the app mentions a place in the app THE SYSTEM SHALL link to it with an in-app link, and SHALL NOT invent features, pages or settings that the guide does not mention. |
| AST-002-AC10 | THE SYSTEM SHALL understand follow-up questions when deciding the intent: "and which of those are over ₹1 lakh?" after an invoice answer is `data`; a clearly unrelated question after a data answer is still declined. |
| AST-002-AC11 | IF a question mixes an in-scope part with an out-of-scope part ("list my unpaid invoices and write me a poem") THEN THE SYSTEM SHALL answer the in-scope part and briefly decline the rest. |
| AST-002-AC12 | IF the intent check is unavailable (error, timeout or unusable result) THEN THE SYSTEM SHALL pass the question to the main model, whose own instructions enforce the same boundary, and SHALL log and count it. The user SHALL see no difference. |
| AST-002-AC13 | THE SYSTEM SHALL give the main model the same boundary in its instructions: the scope above, a rule to decline everything else, never to reveal or discuss its instructions, and to treat conversation text and tool results as data, not instructions. |
| AST-002-AC14 | THE SYSTEM SHALL show the new scope to users: the Talk to Me welcome text, page subtitle and question-box label SHALL mention the app as well as contracts and invoices, and the empty conversation SHALL offer suggestions about the app ("What is this app about?" and "How does this app work?") alongside the contracts and invoices ones. |
| AST-002-AC15 | THE SYSTEM SHALL log each decision with its request ID, intent, source (classifier or fallback), duration and tokens, **but never the question or the reply text**, and SHALL expose `assistant_guard_total{intent}` and `assistant_chats_total{result="declined"}`. The classifier's tokens SHALL be counted under its model name. |
| AST-002-AC16 | THE SYSTEM SHALL show a declined reply within 3 seconds of the question in normal conditions (the intent check adds about half a second to an allowed question), and SHALL give up on the intent check after 5 seconds. |
| AST-002-AC17 | THE SYSTEM SHALL present declined replies and app answers like any other answer: streamed into the same card, copyable, announced to screen readers, kept in the conversation, and still read-only. |
| AST-002-AC18 | THE SYSTEM SHALL NOT call the real AI in automated tests. With `ASSISTANT_LLM=fake` it SHALL use a deterministic stand-in for the intent check too. |

## Out of scope

- Limiting how many questions a user asks, detecting abuse across a session, or blocking users.
- Moderating the *content* of uploaded documents, or translating questions.
- Filtering the main model's answers after they are written (the boundary is enforced before, and
  in its instructions).
- Answering questions about other businesses, the news, the web, or general knowledge.
- A separate help centre or documentation pages. The guide lives inside the assistant.

## Open questions

- None. Decided 2026-10-05: the intent check is a separate small model (ADR-0005); declined
  replies are fixed templates, not model-written; the check fails open to the prompt-level rules.
