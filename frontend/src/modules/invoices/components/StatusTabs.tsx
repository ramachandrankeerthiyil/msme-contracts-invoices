import { Link } from 'react-router'

import { cn } from '@/lib/utils'

import type { ViewCounts } from '../api'
import { type InvoiceQuery, toUrlParams } from '../query'
import { VIEW_TABS } from '../status'

/** Quick-filter tabs with counts (INV-002 AC3). Each tab is a link, so it can be bookmarked. */
export function StatusTabs({ query, counts }: { query: InvoiceQuery; counts?: ViewCounts }) {
  return (
    <nav aria-label="Filter by status">
      <ul className="flex flex-wrap gap-2">
        {VIEW_TABS.map(({ view, label, icon: Icon }) => {
          const active = query.view === view
          return (
            <li key={view}>
              <Link
                to={`?${toUrlParams({ ...query, view, page: 1 })}`}
                aria-current={active ? 'page' : undefined}
                className={cn(
                  'inline-flex h-12 items-center gap-2 rounded-md border px-4 font-semibold transition-colors',
                  active
                    ? 'border-primary bg-primary text-on-primary'
                    : 'border-border bg-bg text-text hover:bg-surface-strong',
                )}
              >
                <Icon aria-hidden className="size-5" />
                {label}
                <span
                  className={cn(
                    'min-w-8 rounded-full px-2 text-center text-small tabular-nums',
                    active ? 'bg-bg text-primary' : 'bg-surface-strong text-text',
                  )}
                >
                  {counts ? counts[view].toLocaleString('en-IN') : '–'}
                </span>
              </Link>
            </li>
          )
        })}
      </ul>
    </nav>
  )
}
