import type { LucideIcon } from 'lucide-react'
import { Link } from 'react-router'

import { cn } from '@/lib/utils'

export interface FilterTab<V extends string> {
  value: V
  label: string
  icon: LucideIcon
}

interface FilterTabsProps<V extends string> {
  /** Accessible name of the tab group, e.g. "Filter by status". */
  label: string
  tabs: FilterTab<V>[]
  current: V
  counts?: Partial<Record<V, number>>
  /** URL for each tab, so every view can be bookmarked. */
  hrefFor: (value: V) => string
}

/** Quick-filter tabs with counts (invoice and contract lists). Each tab is a link. */
export function FilterTabs<V extends string>({ label, tabs, current, counts, hrefFor }: FilterTabsProps<V>) {
  return (
    <nav aria-label={label}>
      <ul className="flex flex-wrap gap-2">
        {tabs.map(({ value, label: tabLabel, icon: Icon }) => {
          const active = value === current
          const count = counts?.[value]
          return (
            <li key={value}>
              <Link
                to={hrefFor(value)}
                aria-current={active ? 'page' : undefined}
                className={cn(
                  'inline-flex h-12 items-center gap-2 rounded-md border px-4 font-semibold transition-colors',
                  active
                    ? 'border-primary bg-primary text-on-primary'
                    : 'border-border bg-bg text-text hover:bg-surface-strong',
                )}
              >
                <Icon aria-hidden className="size-5" />
                {tabLabel}
                <span
                  className={cn(
                    'min-w-8 rounded-full px-2 text-center text-small tabular-nums',
                    active ? 'bg-bg text-primary' : 'bg-surface-strong text-text',
                  )}
                >
                  {count === undefined ? '–' : count.toLocaleString('en-IN')}
                </span>
              </Link>
            </li>
          )
        })}
      </ul>
    </nav>
  )
}
