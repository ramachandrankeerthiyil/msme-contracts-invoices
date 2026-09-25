import { KpiCard } from '@/components/common/KpiCard'
import { formatINR } from '@/lib/format'

import type { DashboardData } from '../api'
import { listUrl } from '../query'

/**
 * The three headline numbers (INV-003 AC2–AC4). Each card links to exactly the invoices behind
 * it, using the filter the API sent (AC6). Shared by the dashboard and Home (PLT-001 AC5), so the
 * layout follows the space it is given (container queries), not the window width.
 */
export function InvoiceKpis({ data }: { data: DashboardData }) {
  const { follow_up: followUp, links } = data
  const thisWeek = listUrl(links.this_week)
  return (
    <div className="@container">
      <div className="grid gap-6 @lg:grid-cols-2 @3xl:grid-cols-[3fr_2fr_2fr]">
        <div className="@lg:col-span-2 @3xl:col-span-1">
          <KpiCard
            label="Total invoice value"
            value={formatINR(data.value_this_week)}
            hint="Due this week"
            to={thisWeek}
          />
        </div>
        <KpiCard
          label="Invoices this week"
          value={data.invoices_this_week.toLocaleString('en-IN')}
          hint="Due this week"
          to={thisWeek}
        />
        <KpiCard
          label="Need follow-up"
          value={followUp.total.toLocaleString('en-IN')}
          hint={
            followUp.total
              ? `${followUp.outstanding} outstanding · ${followUp.at_risk} at risk`
              : 'Nothing to chase this week'
          }
          variant={followUp.total ? 'warning' : 'success'}
          to={listUrl(links.follow_up)}
        />
      </div>
    </div>
  )
}
