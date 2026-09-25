import { StatusBadge } from '@/components/common/StatusBadge'
import { countOf, formatINR } from '@/lib/format'
import { cn } from '@/lib/utils'

import type { InvoiceStatus, StatusValue } from '../api'
import { STATUS_META } from '../status'

const BAR_COLOUR: Record<InvoiceStatus, string> = {
  outstanding: 'bg-danger',
  at_risk: 'bg-warning',
  open: 'bg-neutral',
  paid: 'bg-success',
}

/**
 * This week's value by payment status (INV-003 AC8). A table whose rows carry a bar, so the
 * chart and its accessible text alternative are the same element.
 */
export function ValueByStatus({ rows }: { rows: StatusValue[] }) {
  const total = rows.reduce((sum, row) => sum + Number(row.amount), 0)
  return (
    <section
      aria-labelledby="value-by-status-heading"
      className="flex flex-col gap-4 rounded-lg border border-border bg-bg p-6 shadow-card"
    >
      <h2 id="value-by-status-heading" className="text-h2">
        This week&apos;s value by status
      </h2>
      <table className="w-full text-left">
        <caption className="sr-only">Value of invoices due this week, by payment status</caption>
        <thead className="sr-only">
          <tr>
            <th scope="col">Status</th>
            <th scope="col">Share of this week&apos;s value</th>
            <th scope="col">Value and number of invoices</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => {
            const share = total > 0 ? Math.round((Number(row.amount) / total) * 100) : 0
            return (
              <tr key={row.status} className="border-b border-border last:border-b-0">
                <th scope="row" className="py-3 pr-4 text-left font-normal whitespace-nowrap">
                  <StatusBadge variant={STATUS_META[row.status].variant} label={STATUS_META[row.status].label} />
                </th>
                <td className="w-full py-3 pr-4">
                  <div aria-hidden className="h-4 min-w-16 rounded-full bg-surface-strong">
                    <div className={cn('h-full rounded-full', BAR_COLOUR[row.status])} style={{ width: `${share}%` }} />
                  </div>
                  <span className="sr-only">{share}%</span>
                </td>
                <td className="py-3 text-right whitespace-nowrap">
                  <div className="font-semibold tabular-nums">{formatINR(row.amount)}</div>
                  <div className="text-small text-text-muted">{countOf(row.count, 'invoice')}</div>
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </section>
  )
}
