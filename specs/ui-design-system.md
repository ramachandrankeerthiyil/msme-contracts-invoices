---
id: UI
title: UI design system
status: approved
---

# UI design system

**Goals:** professional, calm, consistent, and comfortable for users over 60.
**Palette:** light blue and white.
**Rule:** every colour, size and spacing value comes from the tokens below. No ad-hoc values.

## Principles

1. **Readable first.** Large text, strong contrast, generous spacing. Meet WCAG 2.2 AA at minimum.
2. **Never rely on colour alone.** Every status shows an icon **and** a text label.
3. **One primary action per screen.** It sits in the same place (top right of the page header) on every page.
4. **Plain language.** "Upload invoices", not "Ingest dataset". Error messages say what happened and what to do next.
5. **Predictable.** The same things look and behave the same everywhere. Nothing moves unexpectedly, and nothing happens on hover alone.

## Colour tokens

Light blue is used for **surfaces and accents**. Text is always dark navy, because light blue
text on white fails contrast.

| Token | Hex | Use |
|---|---|---|
| `--color-bg` | `#FFFFFF` | Page background, cards |
| `--color-surface` | `#F3F8FD` | Sidebar, table header, subtle panels |
| `--color-surface-strong` | `#E3EFFB` | Selected nav item, zebra rows, hover |
| `--color-border` | `#C9DDF2` | Card and table borders, dividers |
| `--color-primary` | `#1D5FA8` | Primary buttons, links, active nav marker (6.4:1 on white) |
| `--color-primary-hover` | `#174C86` | Primary button hover |
| `--color-primary-soft` | `#D6E8F9` | Info badges, focus halo background |
| `--color-text` | `#0F2742` | Body text, headings (15:1 on white) |
| `--color-text-muted` | `#3F5875` | Secondary text, labels (7:1 on white). Never lighter than this. |
| `--color-focus` | `#1D5FA8` | 3px focus outline on every interactive element |

### Status colours (always paired with an icon + label)

| Status | Text/icon | Background | Icon |
|---|---|---|---|
| Success / Paid / In force | `#1B6E43` | `#E6F4EC` | check-circle |
| Warning / At risk | `#7A4E00` | `#FFF3D6` | alert-triangle |
| Danger / Outstanding / Expired | `#A61B1B` | `#FDEAEA` | alert-octagon |
| Info / Updated / No end date | `#1D5FA8` | `#E3EFFB` | info |
| Neutral / Not started / Processing | `#3F5875` | `#EEF2F6` | clock |

## Typography

- **Font:** Inter (self-hosted), falling back to `system-ui, sans-serif`. Tabular numbers
  (`font-variant-numeric: tabular-nums`) in tables and KPI cards.
- **Base size 18px.** Nothing below 16px anywhere, including table cells, badges and helper text.
- Line height 1.6 for body text and 1.3 for headings. Maximum line length about 75 characters.

| Token | Size / weight | Use |
|---|---|---|
| `--text-display` | 40px / 700 | KPI numbers on dashboards |
| `--text-h1` | 32px / 700 | Page title |
| `--text-h2` | 26px / 600 | Section title |
| `--text-h3` | 22px / 600 | Card title |
| `--text-body` | 18px / 400 | Default |
| `--text-small` | 16px / 400 | Table cells, helper text, badges (minimum size) |

## Spacing, shape, motion

- **Spacing scale (px):** 4, 8, 12, 16, 24, 32, 48, 64. Page padding 32 (desktop) / 16 (mobile).
- **Radius:** 8px on inputs and buttons, 12px on cards. Cards use `--color-border` plus a very light shadow.
- **Touch targets:** at least 44 × 44px. Buttons are 48px tall.
- **Motion:** 150ms fades only, and respect `prefers-reduced-motion`. No auto-dismissing messages
  that carry important information.

## Layout (app shell)

```
┌──────────────────────────────────────────────────────────────────────┐
│  [logo] MSME Contracts & Invoices                                    │  header 72px, white, bottom border
├──────────────┬───────────────────────────────────────────────────────┤
│ Home         │  Invoices › Dashboard                    (breadcrumb) │
│              │  Invoice dashboard            [ ⬆ Upload invoices ]   │  page header: title + primary action
│ CONTRACTS    │  ──────────────────────────────────────────────────── │
│  Dashboard   │                                                       │
│  All         │   page content (max width 1280px)                     │
│  Upload      │                                                       │
│              │                                                       │
│ INVOICES     │                                                       │
│  Dashboard ◄ │                                                       │
│  All         │                                                       │
│  Upload      │                                                       │
└──────────────┴───────────────────────────────────────────────────────┘
  sidebar 264px, --color-surface; collapses to a top menu button below 1024px
```

Navigation behaviour is specified in `platform/PLT-001-app-shell-and-navigation`.

## Components (shadcn/ui, restyled with the tokens)

| Component | Rules |
|---|---|
| **Button** | Primary (filled `--color-primary`), Secondary (white + border), Danger. Icon + text label; never icon-only. |
| **KPI card** | Label (`--text-h3`), big number (`--text-display`), one-line explanation, and a status icon. The whole card is clickable and opens the filtered list. |
| **Status badge** | Pill with icon + label from the status table. Minimum 16px text. |
| **Data table** | Sticky header, 56px rows, zebra `--color-surface-strong`, right-aligned numbers, sortable column headers with a visible sort arrow, and pagination with "Showing 1–25 of 140". |
| **File upload** | Large drop zone **and** a "Choose file" button; accepted formats and size limit stated in text; progress bar; clear success/error summary. |
| **Alerts** | Inline banner with icon, title and a plain-language message. Errors show what to do next. |
| **Empty state** | Illustration/icon, one sentence, and the primary action (e.g. "No invoices yet — Upload invoices"). |
| **Loading** | Skeletons shaped like the content. For AI extraction, a progress message: "Reading your contract… this usually takes under a minute." |

## Formatting

- **Dates:** `24 Sep 2026` (unambiguous; never `09/10/26`).
- **Money:** INR with Indian digit grouping and 2 decimals: `₹4,25,000.00` (`Intl.NumberFormat('en-IN', {style: 'currency', currency: 'INR'})`).
- **Relative hints** alongside dates: "due in 3 days", "12 days overdue".

## Accessibility checklist (applies to every feature)

- [ ] Every action is reachable by keyboard, with a visible 3px focus outline
- [ ] Every input has a visible label (placeholders are never labels)
- [ ] Status is conveyed by an icon + text, not colour alone
- [ ] The page is readable and usable at 200% browser zoom
- [ ] Headings are in a logical order; landmarks (`header`, `nav`, `main`) are present
- [ ] Charts have a text or table alternative
