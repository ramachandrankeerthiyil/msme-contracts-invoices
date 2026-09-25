---
id: PLT-001
title: App shell and navigation — tasks
status: implemented
design: ./design.md
---

# PLT-001 — Tasks

Branch: `feat/PLT-001-app-shell` (start after PLT-002 has merged, so the gateway exists)

## A. Scaffold

- [x] 1. Vite + React + TypeScript (strict) app in `frontend/`; ESLint, Prettier, Vitest,
       Testing Library, Playwright + `@axe-core/playwright`.
- [x] 2. Tailwind v4 + shadcn/ui init; add the primitives listed in the design; `lucide-react`;
       `@fontsource-variable/inter`.
- [x] 3. `styles/tokens.css` with every token from `ui-design-system.md`; `@theme` mapping;
       18px base; lint/CI check blocking raw hex and px font sizes. — _AC1, AC11_
- [x] 4. `frontend/Dockerfile` (multi-stage) + `nginx.conf` with SPA fallback; replace the compose
       placeholder; add the `frontend-dev` service under `profiles: [dev]`; Vite `/api` proxy.

## B. Shell

- [x] 5. Module registry (`app/modules.ts`), `contracts` and `invoices` module definitions with
       routes pointing to `ComingSoon`; `router.tsx` builds routes + `handle.crumb/title`. — _AC2, AC6_
- [x] 6. `AppShell`, `Header`, `Sidebar` (groups, icons + labels, active state with longest-prefix
       match, `aria-current`). — _AC1, AC2, AC3_
- [x] 7. `PageHeader` + `Breadcrumbs` + `document.title`. — _AC4_
- [x] 8. `SkipLink` + `RouteFocus` (focus h1 on navigation). — _AC8_
- [x] 9. `MobileNav` (Menu button + Sheet below 1024px, Escape + focus return). — _AC7_
- [x] 10. `NotFoundPage`. — _AC9_

## C. Shared building blocks

- [x] 11. `lib/api/client.ts` (`apiFetch`, `ApiError`, service-unavailable mapping, console logging). — _AC10, PLT-002 AC8/AC11_
- [x] 12. `ErrorAlert`, `QueryBoundary`, top-level `ErrorBoundary`. — _AC10, PLT-002 AC8_
- [x] 13. `StatusBadge`, `KpiCard`, `EmptyState` + Vitest tests (icon and label always present).
- [x] 14. `lib/format.ts` (`formatDate`, `formatINR`, `relativeDue`) + unit tests including
       lakh/crore grouping and the "due today" boundary.

## D. Home

- [x] 15. `HomePage` with the two independent sections showing empty states. KPI wiring is
       completed in CON-003 / INV-003. — _AC5 (partial)_

## E. Verify

- [x] 16. Playwright specs for AC1–AC11 (see the design's Testing table); axe on every route.
- [x] 17. Update the `CLAUDE.md` commands (frontend dev, test, e2e).
- [x] 18. Set statuses to `implemented` (note that AC5 is completed by the dashboard features); commit and merge.

## Verification (2026-09-24)

- Unit (Vitest): 59 passed. Typecheck, ESLint and the design-token check are clean.
- End to end (Playwright + axe, against the full stack): 26 passed. That covers all 9 routes ×
  (shell + a11y + ≥16px text), sidebar, Home links, deep links + Back, the mobile menu at 800px,
  keyboard-only navigation, not found, and the shell with the API returning 503.
- AC5 is partial by design: Home shows empty states until CON-003 / INV-003 wire in the KPIs.
  Update 2026-09-25: Home now shows both modules' KPIs (INV-003, CON-003). AC5 complete.
