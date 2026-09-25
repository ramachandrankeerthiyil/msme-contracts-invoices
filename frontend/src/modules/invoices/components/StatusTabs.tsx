import { FilterTabs } from '@/components/common/FilterTabs'

import type { ViewCounts } from '../api'
import { type InvoiceQuery, toUrlParams } from '../query'
import { VIEW_TABS } from '../status'

/** Quick-filter tabs with counts (INV-002 AC3). Each tab is a link, so it can be bookmarked. */
export function StatusTabs({ query, counts }: { query: InvoiceQuery; counts?: ViewCounts }) {
  return (
    <FilterTabs
      label="Filter by status"
      tabs={VIEW_TABS.map(({ view, label, icon }) => ({ value: view, label, icon }))}
      current={query.view}
      counts={counts}
      hrefFor={(view) => `?${toUrlParams({ ...query, view, page: 1 })}`}
    />
  )
}
