import {
  BellRing,
  CircleCheck,
  Clock,
  List,
  OctagonAlert,
  TriangleAlert,
  type LucideIcon,
} from 'lucide-react'

import type { StatusVariant } from '@/components/common/StatusBadge'
import { dueHintFromDays, formatDate } from '@/lib/format'

import type { InvoiceStatus } from './api'
import type { View } from './query'

// Payment status presentation (INV-002 AC1, AC2). The status itself always comes from the API.

export const STATUS_META: Record<InvoiceStatus, { label: string; variant: StatusVariant }> = {
  outstanding: { label: 'Outstanding', variant: 'danger' },
  at_risk: { label: 'At risk', variant: 'warning' },
  open: { label: 'Open', variant: 'neutral' },
  paid: { label: 'Paid', variant: 'success' },
}

export const VIEW_TABS: { view: View; label: string; icon: LucideIcon }[] = [
  { view: 'follow_up', label: 'Needs follow-up', icon: BellRing },
  { view: 'outstanding', label: 'Outstanding', icon: OctagonAlert },
  { view: 'at_risk', label: 'At risk', icon: TriangleAlert },
  { view: 'open', label: 'Open', icon: Clock },
  { view: 'paid', label: 'Paid', icon: CircleCheck },
  { view: 'all', label: 'All', icon: List },
]

/** "due in 3 days", "12 days overdue", "paid on 20 Sep 2026". */
export function invoiceDueHint(item: { paid_date: string | null; days_until_due: number | null }): string {
  if (item.paid_date) return `paid on ${formatDate(item.paid_date)}`
  return dueHintFromDays(item.days_until_due ?? 0)
}

/** Colour for the due hint: urgent statuses stand out, others stay quiet. */
export function dueHintClass(status: InvoiceStatus): string {
  if (status === 'outstanding') return 'font-semibold text-danger'
  if (status === 'at_risk') return 'font-semibold text-warning'
  return 'text-text-muted'
}
