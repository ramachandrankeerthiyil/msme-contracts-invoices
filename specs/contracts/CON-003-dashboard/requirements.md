---
id: CON-003
title: Contract dashboard
status: draft
depends_on: [CON-002]
---

# CON-003 — Contract dashboard

## Goal

In a few seconds, a user can see how many contracts they have, how many are active, and which
need attention.

## Acceptance criteria

| ID | Criterion |
|---|---|
| CON-003-AC1 | THE SYSTEM SHALL show KPI cards for: **Total contracts**, **In force**, **At risk**, **Expired**, **Not yet started**, and **No end date**. No end date is shown in its own "Needs review" group, separate from the other cards. |
| CON-003-AC1a | THE SYSTEM SHALL count a contract as At risk when it expires within 3 days **or** has a high-severity risk, and SHALL show a breakdown on the card ("N expiring soon · M with high risks"). |
| CON-003-AC2 | THE SYSTEM SHALL compute every number in contract-service (`GET /api/contracts/dashboard`) using the rules in `contracts/module.md`, counting only contracts with `processing_status = completed`. |
| CON-003-AC3 | WHEN the user clicks a KPI card THE SYSTEM SHALL open the contract list filtered to exactly the contracts behind that number. |
| CON-003-AC4 | THE SYSTEM SHALL show a short list of up to 5 "Needs attention" contracts (at risk first, then the soonest end dates), each linking to its detail page. |
| CON-003-AC5 | THE SYSTEM SHALL show a chart of contracts by lifecycle status, with an accessible text/table alternative. |
| CON-003-AC6 | IF any contracts are processing or failed THEN THE SYSTEM SHALL show a note, e.g. "2 contracts are still being read" / "1 contract could not be read", linking to them. |
| CON-003-AC7 | IF there are no contracts THEN THE SYSTEM SHALL show an empty state with an "Upload contract" button instead of zero-value cards. |
| CON-003-AC8 | THE SYSTEM SHALL show "Figures as of <today's date>" so users know the numbers are current. |

## Out of scope

- Date-range filters and trend-over-time charts.

## Open questions

- None. (Resolved: "Not yet started" gets its own card.)
