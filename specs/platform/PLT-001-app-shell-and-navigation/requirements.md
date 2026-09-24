---
id: PLT-001
title: App shell and navigation
status: approved
depends_on: [UI]
---

# PLT-001 — App shell and navigation

## Goal

A professional, consistent frame around every page, so that users (including those over 60)
always know where they are and how to get to any part of the app in one or two clicks.

## User stories

- As a user, I want the same menu on every page, so that I never get lost.
- As a user, I want to see where I am, so that I can go back confidently.
- As a user, I want a home page that tells me what needs attention, so that I know where to start.

## Acceptance criteria

| ID | Criterion |
|---|---|
| PLT-001-AC1 | THE SYSTEM SHALL show the same header and left sidebar on every page, styled only with `ui-design-system.md` tokens. |
| PLT-001-AC2 | THE SYSTEM SHALL show sidebar groups **Contracts** (Dashboard, All contracts, Upload contract) and **Invoices** (Dashboard, All invoices, Upload invoices), plus **Home**, each with an icon and a text label. |
| PLT-001-AC3 | THE SYSTEM SHALL highlight the current page in the sidebar with a background colour **and** a left marker bar. |
| PLT-001-AC4 | THE SYSTEM SHALL show a breadcrumb and a page title on every page except Home, and place the page's primary action at the top right of the page header. |
| PLT-001-AC5 | WHEN the user opens `/` THE SYSTEM SHALL show a Home page with the headline numbers from both dashboards, each linking to its dashboard. |
| PLT-001-AC6 | THE SYSTEM SHALL give every page a unique, bookmarkable URL (e.g. `/invoices?status=outstanding`), and the browser Back button SHALL work as expected. |
| PLT-001-AC7 | WHEN the window is narrower than 1024px THE SYSTEM SHALL collapse the sidebar behind a labelled "Menu" button. |
| PLT-001-AC8 | THE SYSTEM SHALL make all navigation usable by keyboard alone, with a visible focus outline and a "Skip to content" link. |
| PLT-001-AC9 | IF a URL does not exist THEN THE SYSTEM SHALL show a friendly "Page not found" page with links to Home and both dashboards. |
| PLT-001-AC10 | IF a service is unavailable THEN THE SYSTEM SHALL show a plain-language error in that page's content area, and the rest of the shell SHALL keep working. |
| PLT-001-AC11 | THE SYSTEM SHALL use 18px base text, nothing smaller than 16px, and pass an automated accessibility check (axe) with no serious or critical issues on every page. |

## Out of scope

- Login, user menu, settings, dark mode, multiple languages.

## Open questions

- None.
