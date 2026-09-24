# Specs

Specs are the source of truth for this project. Code implements specs; specs are never
reverse-engineered from code.

## Layout

| Path | Purpose | Changes |
|---|---|---|
| `product.md` | Vision, users, POC scope, glossary | Rarely |
| `architecture.md` | Tiers, services, API & data conventions | Via ADRs |
| `ui-design-system.md` | Colours, typography, layout, components | Rarely |
| `decisions/` | Architecture Decision Records (ADRs) | Append-only |
| `platform/` | Cross-cutting features (app shell, observability) | Per feature |
| `contracts/`, `invoices/` | One folder per business module | Per feature |
| `_templates/` | Copy these to start a new spec | Rarely |

Each module has a `module.md` (entities, business rules, API) plus one folder per feature:

```
<module>/<ID>-<short-name>/
├── requirements.md   # WHAT: user stories + acceptance criteria
├── design.md         # HOW: screens, endpoints, schema changes, edge cases
└── tasks.md          # STEPS: ordered checklist to implement and test
```

## Workflow

1. **Requirements.** Copy `_templates/requirements.md`, write stories and acceptance criteria,
   and set `status: draft`. Review it, then set `status: approved`.
2. **Design.** Only after requirements are approved. Same review → `approved` step.
3. **Tasks.** Break the design into small, testable steps, each linked to the acceptance
   criteria it satisfies.
4. **Implement.** Work through `tasks.md` on a feature branch. Every acceptance criterion needs at
   least one automated test whose name contains its ID (for example `test_INV_001_AC3_...`).
5. **Done.** Once all tasks are ticked and tests pass, set the feature's status to `implemented`.

Status lifecycle: `draft` → `approved` → `implemented` → (`deprecated`)

## IDs

| Prefix | Scope |
|---|---|
| `PLT-nnn` | Platform / cross-cutting features |
| `CON-nnn` | Contracts module |
| `INV-nnn` | Invoices module |
| `<ID>-ACn` | Acceptance criterion *n* of a feature |
| `ADR-nnnn` | Architecture decision |

## Frontmatter

Every spec file starts with:

```yaml
---
id: INV-001
title: Invoice Excel upload
status: draft          # draft | approved | implemented | deprecated
depends_on: [PLT-001]
---
```

## Git workflow

- `main` always holds approved specs and working code.
- **Specs before code:** commit a spec change on its own, for example
  `docs(specs): approve INV-001 requirements`.
- **One branch per feature:** `feat/INV-001-excel-upload`, `feat/CON-001-upload-and-extract`.
- **Commit messages** use Conventional Commits and include the ID:
  `feat(invoices): validate excel headers [INV-001]`, `fix(contracts): handle empty docx [CON-001]`.
- Merge to `main` only when the feature's tests pass.
- Never commit `.env`, uploaded files or real customer documents. Only anonymised samples go in `samples/`.

## Changing an approved spec

Edit it on a branch, set `status: draft`, and describe the change in a `## Changelog` section at
the bottom. Re-approve before any code changes. If the change affects architecture, add an ADR.
