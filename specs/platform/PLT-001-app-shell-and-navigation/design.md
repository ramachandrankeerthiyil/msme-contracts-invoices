---
id: PLT-001
title: App shell and navigation — design
status: approved
requirements: ./requirements.md
---

# PLT-001 — Design

## Overview

PLT-001 scaffolds the React frontend and builds the frame every page lives in: design tokens,
header, sidebar, breadcrumbs, page header, error handling and shared display components.
Business modules plug into the shell through a **module registry**. Adding a module means adding
one entry; the shell code doesn't change.

## Frontend layout

```
frontend/
  Dockerfile                    # multi-stage: node:22 build → nginx:alpine serving dist/
  nginx.conf                    # SPA fallback: try_files $uri /index.html
  package.json, vite.config.ts, tsconfig.json, components.json (shadcn)
  src/
    main.tsx
    app/
      App.tsx                   # providers + router
      router.tsx                # builds routes from the module registry
      modules.ts                # module registry (see below)
      providers.tsx             # TanStack QueryClient, ErrorBoundary
      layout/
        AppShell.tsx            # header + sidebar + <main> + skip link
        Header.tsx
        Sidebar.tsx             # nav built from the registry
        MobileNav.tsx           # "Menu" button + slide-in sheet below 1024px
        PageHeader.tsx          # breadcrumb + h1 + primary action slot
        Breadcrumbs.tsx         # built from route `handle.crumb`
        RouteFocus.tsx          # moves focus to the h1 on navigation
    styles/
      tokens.css                # CSS variables from ui-design-system.md
      globals.css               # Tailwind layers, base typography
    components/
      ui/                       # shadcn primitives (button, card, badge, table, alert, sheet, tabs, input, skeleton)
      common/
        StatusBadge.tsx         # icon + label per status variant
        KpiCard.tsx             # clickable KPI card
        EmptyState.tsx
        ErrorAlert.tsx          # shows ApiError message / reference ID
        QueryBoundary.tsx       # loading skeleton + error + retry for a query
    lib/
      api/client.ts             # fetch wrapper → ApiError (PLT-002 AC8/AC11)
      format.ts                 # formatDate, formatINR, relativeDue
      utils.ts                  # cn() etc.
    modules/
      contracts/index.ts        # exports the ModuleDefinition (routes + nav)
      invoices/index.ts
    pages/
      HomePage.tsx
      NotFoundPage.tsx
  tests/e2e/                    # Playwright specs
```

## Module registry

```ts
// src/app/modules.ts
export interface ModuleDefinition {
  id: 'contracts' | 'invoices';
  label: string;                        // "Contracts"
  nav: { label: string; to: string; icon: LucideIcon; end?: boolean }[];
  routes: RouteObject[];                // each route has handle: { crumb: string, title: string }
}
export const modules: ModuleDefinition[] = [contractsModule, invoicesModule];
```

Until a feature delivers its pages, module routes point to a `ComingSoon` page (same shell,
friendly message), so navigation can be tested end to end from day one.

## Routes (AC6)

| URL | Page | Crumbs | Primary action |
|---|---|---|---|
| `/` | Home | — | — |
| `/contracts/dashboard` | Contract dashboard | Contracts › Dashboard | Upload contract |
| `/contracts` | All contracts | Contracts › All contracts | Upload contract |
| `/contracts/upload` | Upload contract | Contracts › Upload | — |
| `/contracts/:id` | Contract detail | Contracts › All contracts › *{title}* | Download original |
| `/invoices/dashboard` | Invoice dashboard | Invoices › Dashboard | Upload invoices |
| `/invoices` | All invoices | Invoices › All invoices | Upload invoices |
| `/invoices/upload` | Upload invoices | Invoices › Upload | — |
| `*` | Not found | — | — |

- Filters, search, sort and page live in the query string (e.g. `/invoices?status=outstanding&q=acme`).
- `document.title` = `"<page title> · MSME Contracts & Invoices"`.

## Shell behaviour

| Element | Spec |
|---|---|
| **Header** (AC1) | 72px, white, bottom border `--color-border`. Logo mark + product name (link to Home). |
| **Sidebar** (AC1–AC3) | 264px, `--color-surface`. "Home", then group headings **CONTRACTS** / **INVOICES** (16px, 600, muted, uppercase with letter-spacing) with their items. Items are 48px tall with a 20px icon + label. The active item has an `--color-surface-strong` background, a 4px `--color-primary` left bar, 600 weight and `aria-current="page"`. Active matching uses the longest-prefix rule, so `/contracts/123` highlights "All contracts". |
| **Page header** (AC4) | Breadcrumb (16px, links except the last crumb), `h1` (32px), and a right-aligned primary action slot. Stacks vertically below 640px. |
| **Main** | `<main id="content" tabIndex={-1}>`, max-width 1280px, padding 32px (16px on mobile). |
| **Skip link** (AC8) | First focusable element; visible on focus; jumps to `#content`. |
| **Focus on navigation** (AC8) | After each route change, focus moves to the page `h1` (`tabIndex=-1`) so keyboard and screen-reader users start at the new content. |
| **Mobile** (AC7) | Below 1024px the sidebar is hidden. The header shows a 48px "☰ Menu" button (icon + text) that opens the same nav in a left `Sheet`. The sheet closes on navigation and on Escape, and focus returns to the button. |

## Home page (AC5)

Two side-by-side sections (stacked on mobile): **Contracts** and **Invoices**. Each fetches its
own dashboard endpoint and shows 3 headline KPI cards:
- **Contracts:** In force · At risk · Expired
- **Invoices:** Value this week · Need follow-up · Invoices this week

Each section has a "Go to … dashboard" link. The sections load and fail **independently**
(AC10), and each has its own empty state ("No contracts yet — Upload contract").

_Home depends on the dashboard APIs (CON-003, INV-003). Until they exist, each section shows the
empty state. The KPI wiring is completed in each dashboard feature's tasks._

## Error handling (AC10, PLT-002 AC8/AC11)

`lib/api/client.ts`:

```ts
export class ApiError extends Error {
  constructor(public status: number, public code: string, message: string, public requestId?: string) { super(message); }
}
// apiFetch<T>(path, init): prefixes /api, reads X-Request-ID, parses the standard error body.
// Network failure or 502/503/504 → code 'SERVICE_UNAVAILABLE',
//   message "This part of the app isn't responding right now. Please try again in a minute."
// Always logs console.error('[api]', { method, path, status, code, requestId }) on failure.
```

- `QueryBoundary` wraps each page's data. On error it renders `ErrorAlert` inside the content
  area, with a **Try again** button (`refetch`). The shell and navigation stay usable.
- `ErrorAlert` shows `message`. For `INTERNAL_ERROR` / `SERVICE_UNAVAILABLE` it adds
  "Reference: <requestId>" in a monospace span that the user can select.
- A top-level `ErrorBoundary` catches render errors, logs them, and shows the same alert with a
  "Reload page" button.

## Design tokens → Tailwind

`styles/tokens.css` defines every token from `ui-design-system.md` as a CSS variable. Tailwind v4
`@theme` maps them to utilities (`bg-surface`, `text-muted`, `text-h1` …). A lint rule
(`eslint-plugin-tailwindcss` with no arbitrary values, plus a grep check in CI) blocks raw hex
colours and pixel font sizes outside `tokens.css` (AC1, AC11).

- **Font:** `@fontsource-variable/inter`, self-hosted. `html { font-size: 18px }`, and Tailwind's
  type scale is replaced by the token scale, so nothing can render below 16px.
- **Icons:** `lucide-react`.

## Shared display components

| Component | Props | Notes |
|---|---|---|
| `StatusBadge` | `variant: 'success' \| 'warning' \| 'danger' \| 'info' \| 'neutral'`, `label` | Icon is fixed per variant (see UI spec); text is always rendered |
| `KpiCard` | `label`, `value`, `hint?`, `variant`, `to` | Whole card is a `<Link>`; accessible name "<label>: <value>. <hint>" |
| `EmptyState` | `icon`, `title`, `action?` | |
| `ErrorAlert` | `error: ApiError \| Error`, `onRetry?` | |

## Formatting helpers (`lib/format.ts`)

- `formatDate('2026-09-24')` → `24 Sep 2026` (`en-IN`, `Asia/Kolkata`)
- `formatINR('425000.00')` → `₹4,25,000.00` (the decimal string is parsed without floating-point loss)
- `relativeDue(dueDate, today)` → `due today` / `due in 3 days` / `12 days overdue`

## Dev workflow

- **Recommended:** install Node 22 in WSL (via `nvm`) and run `npm run dev` for Vite hot reload
  on :5173. Vite proxies `/api` → `http://localhost:8080` (the gateway).
- **Without local Node:** `docker compose --profile dev up frontend-dev` runs the same Vite dev
  server in a `node:22` container with the source mounted.
- **Production-like:** the `frontend` image builds static files and serves them behind the gateway on :8080.

## Testing

| AC | Test |
|---|---|
| AC1, AC4 | Playwright: every route renders header, sidebar, breadcrumb (except Home) and h1 |
| AC2, AC3 | Playwright: sidebar items and labels; the active item has `aria-current` for each route, including `/contracts/:id` |
| AC5 | Vitest: Home renders both sections; one failing endpoint shows an error in that section only |
| AC6 | Playwright: deep-link to a filtered URL loads it; Back restores the previous view |
| AC7 | Playwright at 800px wide: sidebar hidden, Menu opens sheet, Escape closes it, focus returns |
| AC8 | Playwright: Tab reaches the skip link first; the whole nav is operable by keyboard; focus moves to h1 after navigation |
| AC9 | Playwright: `/nope` shows Not found with 3 links |
| AC10 | Playwright with the `/api/invoices/**` route mocked to 503: friendly alert + reference, nav still works |
| AC11 | `@axe-core/playwright` on every route: zero serious/critical violations; computed font-size ≥ 16px for all text nodes |
