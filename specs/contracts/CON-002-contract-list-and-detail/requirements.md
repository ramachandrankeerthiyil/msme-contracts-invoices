---
id: CON-002
title: Contract list and detail
status: approved
depends_on: [CON-001]
---

# CON-002 — Contract list and detail

## Goal

A user can see all their contracts at a glance, and open any one to read its parties, dates,
terms and risks in plain language.

## User stories

- As a business owner, I want a list of all my contracts with their status, so that I can see which ones need attention.
- As a business owner, I want to see a contract's risks with the most serious first, so that I can act on them.
- As a business owner, I want to open the original file, so that I can check what the AI found.

## Acceptance criteria

| ID | Criterion |
|---|---|
| CON-002-AC1 | THE SYSTEM SHALL list contracts in a table with: title, parties, start date, end date, lifecycle status badge, an "At risk" badge when flagged, number of high-severity risks, and upload date. |
| CON-002-AC2 | THE SYSTEM SHALL let the user filter by lifecycle status (In force, Expired, Not yet started, No end date, Processing, Failed) and by "At risk", and search by title or party name. |
| CON-002-AC3 | THE SYSTEM SHALL sort by end date ascending by default (soonest first), and let the user sort by any column. |
| CON-002-AC4 | THE SYSTEM SHALL compute lifecycle status and the at-risk flag using the rules in `contracts/module.md`, relative to today, and show the at-risk reason ("Expires in 2 days", "2 high risks"). |
| CON-002-AC5 | WHEN the user opens a contract THE SYSTEM SHALL show a detail page with: title, status badges, summary, parties, key dates (in date order, with "in N days"/"N days ago"), terms grouped by category, and risks grouped High → Medium → Low. |
| CON-002-AC6 | THE SYSTEM SHALL show the `source_text` quote for each term, risk and key date. |
| CON-002-AC7 | THE SYSTEM SHALL clearly label extracted content "Extracted by AI — please check against the original document", and offer a "Download original" button. |
| CON-002-AC8 | IF a contract is processing or has failed THEN THE SYSTEM SHALL show its status in the list, and its detail page SHALL show the progress message or the error and a "Try again" button. |
| CON-002-AC9 | IF there are no contracts THEN THE SYSTEM SHALL show an empty state with an "Upload contract" button. |

## Out of scope

- Editing or deleting contracts (decided: no delete in the POC).

## Open questions

- None beyond those in `contracts/module.md`.
