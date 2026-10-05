---
id: ADR-0005
title: Assistant guardrails: a fast classifier in front of the main model, plus an in-prompt app guide
status: accepted
date: 2026-10-05
---

# ADR-0005 — Assistant guardrails

## Context

AST-001 asks "Talk to Me" to decline anything that is not about the user's contracts and invoices
(AC10). Today that rests on one sentence in the system prompt. A prompt is a request, not a
control: a determined or merely curious user can talk the model into writing poems, answering
general questions, role-playing, or revealing its instructions. Every such answer also costs a
full Sonnet call with tools. The product owner now wants a firm boundary: the assistant answers
only about the functionality the app exposes (the user's contracts and invoices), and about **what
the app is and how it works**, and for that second kind it should give a good, coherent answer.

## Decision

1. **A guard runs before the main model.** The latest question (with the last few turns for
   context, so follow-ups like "and the biggest one?" are understood) is classified by a small, fast
   model into one of six intents:

   | Intent | Meaning | What happens |
   |---|---|---|
   | `data` | About this business's invoices or contracts | The normal answer loop, with lookups |
   | `about_app` | What the app is, what it can do, how it works, how to do something in it | The main model answers from the built-in **app guide**, with no lookups |
   | `write_request` | Asks to change data or send something | Declined with a fixed message that points to the right page |
   | `legal_advice` | Asks what to do legally, or whether a clause is enforceable | Declined with a fixed message |
   | `off_topic` | Anything else (general knowledge, code, chit-chat, opinions) | Declined with a fixed message |
   | `manipulation` | Tries to override instructions, reveal the prompt, or change the assistant's role | Declined with the same fixed message as `off_topic` (no argument, no lecture) |

   Declined questions never reach the main model or the tools. The reply is a **fixed template**
   written by us, not model output, so it cannot be argued out of its wording, costs nothing, and
   is the same every time.
2. **The classifier is Claude Haiku 4.5** (`ASSISTANT_GUARD_MODEL`, default
   `claude-haiku-4-5-20251001`), called with a JSON-schema (`output_config.format`) so the answer
   is exactly one of the six intents. It gets no tools, a 5-second timeout and no retries. It adds
   roughly half a second to the first word of an answer.
3. **The guard fails open, because the prompt is a second layer.** If the classifier errors, times
   out or returns something unexpected, the question goes to the main model, whose system prompt
   enforces the same boundary. This is logged and counted (`intent="unknown"`), so an operator can
   see it. Failing closed would make every question fail whenever the cheap call hiccups, which
   would be a worse product for a boundary that the second layer also holds.
4. **The main model's system prompt is tightened too** (defence in depth): an explicit scope list,
   a refusal rule for everything else, instructions never to reveal or discuss its instructions,
   and to treat conversation text and tool results as data. It also carries the app guide and the
   classified intent as a hint, not as an instruction from the user.
5. **The app guide is a maintained document in the service** (`app/assistant/app_guide.py`), sent
   in the cached system prompt. It describes the app, the two modules, the statuses, how to upload,
   email reminders, Talk to Me itself, and the limits. The at-risk windows are filled in from the
   same settings the other services use, so the guide never states a stale number. An `about_app`
   question is answered from it alone.
6. **Tests never call the real classifier.** `ASSISTANT_LLM=fake` also selects a deterministic
   keyword guard, and the e2e script already refuses to run against the real AI.

## Alternatives considered

- **Prompt only (the status quo).** Cheapest, but it is the weakest control and every abuse costs
  a full call.
- **Keyword or regex rules only.** Free and instant, but it cannot tell "who owes me the most" from
  "who won the match", and it breaks on follow-ups. We keep keywords only for the fake guard.
- **Embeddings or a trained classifier.** More machinery than a POC needs, and a model call is
  simpler to explain and to change.
- **Let the main model call a `decline` tool.** The decision would still be the main model's, so
  it would inherit the weakness we are fixing, and the cost would remain.
- **Fail closed.** See decision 3.
- **Ask the main model to do `about_app` through tools.** The guide is small and stable, so the
  system prompt is simpler and faster than a lookup, and it caches.

## Consequences

- One more small model call per question (a few hundred tokens), with its tokens counted under the
  guard model's name in `llm_tokens_total`.
- A rare wrong decision is possible. The guard is told to prefer `data` when a question could
  plausibly be about the business's records, so a wrongly declined question can be rephrased,
  while a wrongly allowed one still meets the prompt. `assistant_guard_total{intent}` shows the
  mix, and the opt-in live eval (`pytest -m llm`) holds golden questions for every intent.
- The guide must be updated when the app changes. A unit test checks that it names every module
  and key behaviour, and that the specs' definitions (for example the at-risk windows) are not
  hard-coded.
- Question text is sent to one more model call (still Claude, same key), as before for the main
  call. It is still never logged.
