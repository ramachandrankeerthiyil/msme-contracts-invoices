import { StatusBars } from '@/components/common/StatusBars'
import { countOf, formatINR } from '@/lib/format'

import type { StatusValue } from '../api'
import { STATUS_META } from '../status'

/** This week's value by payment status (INV-003 AC8). */
export function ValueByStatus({ rows }: { rows: StatusValue[] }) {
  return (
    <StatusBars
      id="value-by-status-heading"
      heading="This week's value by status"
      caption="Value of invoices due this week, by payment status"
      valueHeader="Value and number of invoices"
      rows={rows.map((row) => ({
        key: row.status,
        label: STATUS_META[row.status].label,
        variant: STATUS_META[row.status].variant,
        value: Number(row.amount),
        display: formatINR(row.amount),
        detail: countOf(row.count, 'invoice'),
      }))}
    />
  )
}
