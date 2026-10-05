---
id: AST-001
title: Conversational AI assistant ("Talk to Me")
status: implemented
depends_on: [PLT-001, PLT-002, INV-002, INV-003, CON-002, CON-003, ADR-0003]
---

# AST-001 — Conversational AI assistant ("Talk to Me")

## Goal

A business owner can ask questions about their contracts and invoices in plain English, such as
"Which invoices are unpaid as of today?" or "What risks are in the Bluewave contract?". They get
a short, accurate answer based on their own live data, with links to the underlying records.

## User stories

- As a business owner, I want to ask a question in my own words, so that I don't have to know
  which page or filter holds the answer.
- As a business owner, I want to see the answer appear as it is written, so that I know the app
  is working.
- As a business owner, I want to see what the assistant looked up and open those records, so that
  I can trust and check its answer.
- As a business owner, I want to ask follow-up questions ("and which of those are over ₹1 lakh?"),
  so that I can dig deeper naturally.

## Acceptance criteria

| ID | Criterion |
|---|---|
| AST-001-AC1 | THE SYSTEM SHALL add an **Talk to Me** item (icon + label) to the left navigation, in its own **ASSISTANT** group, opening the page `/assistant`, with the same header, breadcrumb and focus behaviour as other pages (PLT-001). |
| AST-001-AC2 | WHEN a conversation is empty THE SYSTEM SHALL show a short welcome and 4–8 suggested questions covering contracts, invoices and the app itself (AST-002); choosing one SHALL ask it. |
| AST-001-AC3 | THE SYSTEM SHALL provide a labelled multi-line question box: Enter sends, Shift+Enter adds a new line, a 48px **Send** button (icon + label) sends, and it SHALL accept at most 1,000 characters, telling the user when the limit is near. |
| AST-001-AC4 | WHEN a question is sent THE SYSTEM SHALL show the answer progressively as it is written, and SHALL offer a **Stop** button that ends the answer, keeping what was written so far. |
| AST-001-AC5 | THE SYSTEM SHALL answer only from the user's live data, obtained through read-only lookups of the existing contract and invoice APIs. IF the data does not answer the question THEN it SHALL say so rather than guess. |
| AST-001-AC6 | THE SYSTEM SHALL show, for each answer, what was looked up (e.g. "Checked unpaid invoices", "Read *Master Services Agreement*") while it happens and afterwards. |
| AST-001-AC7 | THE SYSTEM SHALL link every contract or invoice it mentions to that record's page in the app. |
| AST-001-AC8 | THE SYSTEM SHALL understand follow-up questions within the same conversation, keep the conversation when the page is refreshed in the same browser tab, and offer **New conversation** to start again. |
| AST-001-AC9 | THE SYSTEM SHALL write short, plain-language answers, using lists or small tables where they help, with amounts in INR (₹4,25,000.00), dates like "24 Sep 2026", and "today" meaning today in Asia/Kolkata. |
| AST-001-AC10 | IF a question is not about the user's contracts, invoices or this app, asks for legal advice, or asks to change data THEN THE SYSTEM SHALL politely say what it can help with instead. The assistant SHALL NOT be able to change any data. How this is enforced is specified in AST-002. |
| AST-001-AC11 | THE SYSTEM SHALL show, near the question box, "Talk to Me can make mistakes. Check important details on the contract or invoice page." |
| AST-001-AC12 | IF answering fails THEN THE SYSTEM SHALL show a plain-language message with **Try again** and a reference number (PLT-002). The rest of the app SHALL keep working when the assistant is unavailable. |
| AST-001-AC13 | THE SYSTEM SHALL meet the design system's accessibility rules: 18px base text, fully usable by keyboard, a finished answer announced once to screen readers (not word by word), focus returned to the question box after answering, no serious axe issues, and usable on a phone-width screen. |
| AST-001-AC14 | THE SYSTEM SHALL log each question with its request ID, the lookups used, the number of AI steps, tokens and duration, **but not the question or answer text**, and SHALL expose metrics for questions, lookups and tokens (PLT-002). |
| AST-001-AC15 | THE SYSTEM SHALL start showing an answer to a typical question within 10 seconds and finish within 60 seconds, using at most 8 lookups per question. |
| AST-001-AC16 | THE SYSTEM SHALL offer a **Copy** button on each answer. |

## Out of scope

- Saving conversations beyond the browser tab, several saved conversations, or sharing them.
- Changing data through chat (marking invoices paid, uploading files, retrying contracts).
- Voice input, attaching files in the chat, and answering from outside knowledge or the web.
- Legal advice. The assistant explains what a contract says; it does not advise what to do legally.

## Decisions (product owner, 2026-09-25)

| Question | Decision |
|---|---|
| Name | **Talk to Me** (navigation item and page title) |
| Model | Claude Sonnet 5 |
| Conversation memory | Browser tab only; nothing stored on the server |

## Open questions

- None.

## Changelog

- **2026-10-05** — AC2 now allows 4–8 suggestions and includes questions about the app; AC10 now
  also allows questions about the app and points to AST-002, which makes the boundary firm
  (guard in front of the model, fixed replies, app guide). Re-approved together with AST-002.
