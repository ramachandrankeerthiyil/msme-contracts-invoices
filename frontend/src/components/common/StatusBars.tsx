import { cn } from '@/lib/utils'

import { StatusBadge, type StatusVariant } from './StatusBadge'

const BAR_COLOUR: Record<StatusVariant, string> = {
  danger: 'bg-danger',
  warning: 'bg-warning',
  neutral: 'bg-neutral',
  success: 'bg-success',
  info: 'bg-info',
}

export interface StatusBarRow {
  key: string
  label: string
  variant: StatusVariant
  /** The number the bar length is based on. */
  value: number
  /** How the value is shown, e.g. "₹3,96,750.00" or "2". */
  display: string
  /** A smaller second line, e.g. "4 invoices". */
  detail?: string
}

interface StatusBarsProps {
  id: string
  heading: string
  caption: string
  valueHeader: string
  rows: StatusBarRow[]
}

/**
 * A chart that is also its own accessible table: one row per status with a proportional bar
 * (INV-003 AC8, CON-003 AC5).
 */
export function StatusBars({ id, heading, caption, valueHeader, rows }: StatusBarsProps) {
  const total = rows.reduce((sum, row) => sum + row.value, 0)
  return (
    <section aria-labelledby={id} className="flex flex-col gap-4 rounded-lg border border-border bg-bg p-6 shadow-card">
      <h2 id={id} className="text-h2">
        {heading}
      </h2>
      <table className="w-full text-left">
        <caption className="sr-only">{caption}</caption>
        <thead className="sr-only">
          <tr>
            <th scope="col">Status</th>
            <th scope="col">Share</th>
            <th scope="col">{valueHeader}</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => {
            const share = total > 0 ? Math.round((row.value / total) * 100) : 0
            return (
              <tr key={row.key} className="border-b border-border last:border-b-0">
                <th scope="row" className="py-3 pr-4 text-left font-normal whitespace-nowrap">
                  <StatusBadge variant={row.variant} label={row.label} />
                </th>
                <td className="w-full py-3 pr-4">
                  <div aria-hidden className="h-4 min-w-16 rounded-full bg-surface-strong">
                    <div className={cn('h-full rounded-full', BAR_COLOUR[row.variant])} style={{ width: `${share}%` }} />
                  </div>
                  <span className="sr-only">{share}%</span>
                </td>
                <td className="py-3 text-right whitespace-nowrap">
                  <div className="font-semibold tabular-nums">{row.display}</div>
                  {row.detail && <div className="text-small text-text-muted">{row.detail}</div>}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </section>
  )
}
