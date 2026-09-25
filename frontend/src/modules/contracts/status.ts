import {
  CircleCheck,
  Clock,
  FileX,
  Hourglass,
  Info,
  List,
  OctagonAlert,
  TriangleAlert,
  type LucideIcon,
} from 'lucide-react'

import type { StatusVariant } from '@/components/common/StatusBadge'

import type { Lifecycle, Severity, TermCategory } from './api'
import type { View } from './query'

// Presentation of contract statuses (CON-002). The statuses themselves always come from the API.

export const LIFECYCLE_META: Record<Lifecycle, { label: string; variant: StatusVariant }> = {
  in_force: { label: 'In force', variant: 'success' },
  not_started: { label: 'Not yet started', variant: 'neutral' },
  no_end_date: { label: 'No end date', variant: 'info' },
  expired: { label: 'Expired', variant: 'danger' },
  processing: { label: 'Being read', variant: 'neutral' },
  failed: { label: 'Could not be read', variant: 'danger' },
}

export const VIEW_TABS: { value: View; label: string; icon: LucideIcon }[] = [
  { value: 'all', label: 'All', icon: List },
  { value: 'in_force', label: 'In force', icon: CircleCheck },
  { value: 'at_risk', label: 'At risk', icon: TriangleAlert },
  { value: 'not_started', label: 'Not yet started', icon: Clock },
  { value: 'expired', label: 'Expired', icon: OctagonAlert },
  { value: 'no_end_date', label: 'No end date', icon: Info },
  { value: 'processing', label: 'Being read', icon: Hourglass },
  { value: 'failed', label: 'Could not be read', icon: FileX },
]

export const SEVERITY_META: Record<Severity, { label: string; variant: StatusVariant }> = {
  high: { label: 'High', variant: 'danger' },
  medium: { label: 'Medium', variant: 'warning' },
  low: { label: 'Low', variant: 'neutral' },
}

export const TERM_LABELS: Record<TermCategory, string> = {
  payment: 'Payment',
  termination: 'Termination',
  renewal: 'Renewal',
  liability: 'Liability',
  confidentiality: 'Confidentiality',
  governing_law: 'Governing law',
  other: 'Other',
}

function days(n: number): string {
  return `${n} day${n === 1 ? '' : 's'}`
}

/** "in 12 days", "ends today", "ended 3 days ago", "No end date". */
export function endHint(daysUntilEnd: number | null): string {
  if (daysUntilEnd === null) return 'No end date'
  if (daysUntilEnd === 0) return 'ends today'
  return daysUntilEnd > 0 ? `in ${days(daysUntilEnd)}` : `ended ${days(-daysUntilEnd)} ago`
}

/** "today", "in 12 days", "3 days ago". */
export function relativeDay(daysFromToday: number): string {
  if (daysFromToday === 0) return 'today'
  return daysFromToday > 0 ? `in ${days(daysFromToday)}` : `${days(-daysFromToday)} ago`
}
