---
id: PLT-001
title: App shell and navigation — tasks
status: approved
design: ./design.md
---

# PLT-001 — Tasks

Branch: `feat/PLT-001-app-shell` (start after PLT-002 has merged, so the gateway exists)

## A. Scaffold

- [ ] 1. Vite + React + TypeScript (strict) app in `frontend/`; ESLint, Prettier, Vitest,
       Testing Library, Playwright + `@axe-core/playwright`.
- [ ] 2. Tailwind v4 + shadcn/ui init; add the primitives listed in the design; `lucide-react`;
       `@fontsource-variable/inter`.
- [ ] 3. `styles/tokens.css` with every token from `ui-design-system.md`; `@theme` mapping;
       18px base; lint/CI check blocking raw hex and px font sizes. — _AC1, AC11_
- [ ] 4. `frontend/Dockerfile` (multi-stage) + `nginx.conf` with SPA fallback; replace the compose
       placeholder; add the `frontend-dev` service under `profiles: [dev]`; Vite `/api` proxy.

## B. Shell

- [ ] 5. Module registry (`app/modules.ts`), `contracts` and `invoices` module definitions with
       routes pointing to `ComingSoon`; `router.tsx` builds routes + `handle.crumb/title`. — _AC2, AC6_
- [ ] 6. `AppShell`, `Header`, `Sidebar` (groups, icons + labels, active state with longest-prefix
       match, `aria-current`). — _AC1, AC2, AC3_
- [ ] 7. `PageHeader` + `Breadcrumbs` + `document.title`. — _AC4_
- [ ] 8. `SkipLink` + `RouteFocus` (focus h1 on navigation). — _AC8_
- [ ] 9. `MobileNav` (Menu button + Sheet below 1024px, Escape + focus return). — _AC7_
- [ ] 10. `NotFoundPage`. — _AC9_

## C. Shared building blocks

- [ ] 11. `lib/api/client.ts` (`apiFetch`, `ApiError`, service-unavailable mapping, console logging). — _AC10, PLT-002 AC8/AC11_
- [ ] 12. `ErrorAlert`, `QueryBoundary`, top-level `ErrorBoundary`. — _AC10, PLT-002 AC8_
- [ ] 13. `StatusBadge`, `KpiCard`, `EmptyState` + Vitest tests (icon and label always present).
- [ ] 14. `lib/format.ts` (`formatDate`, `formatINR`, `relativeDue`) + unit tests including
       lakh/crore grouping and the "due today" boundary.

## D. Home

- [ ] 15. `HomePage` with the two independent sections showing empty states. KPI wiring is
       completed in CON-003 / INV-003. — _AC5 (partial)_

## E. Verify

- [ ] 16. Playwright specs for AC1–AC11 (see the design's Testing table); axe on every route.
- [ ] 17. Update the `CLAUDE.md` commands (frontend dev, test, e2e).
- [ ] 18. Set statuses to `implemented` (note that AC5 is completed by the dashboard features); commit and merge.
