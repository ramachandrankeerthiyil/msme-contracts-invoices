import { ArrowRight } from 'lucide-react'
import { Link } from 'react-router'

import { StatusIcon, type StatusVariant } from './StatusBadge'

interface KpiCardProps {
  label: string
  value: string
  hint?: string
  variant?: StatusVariant
  /** The filtered list showing exactly the items behind this number. */
  to: string
}

export function KpiCard({ label, value, hint, variant, to }: KpiCardProps) {
  const accessibleName = [`${label}: ${value}.`, hint].filter(Boolean).join(' ')
  return (
    <Link
      to={to}
      aria-label={accessibleName}
      className="group flex h-full flex-col rounded-lg border border-border bg-bg p-6 shadow-card transition-colors hover:border-primary hover:bg-surface"
    >
      <div className="flex items-start justify-between gap-4">
        <p className="text-h3 text-text">{label}</p>
        {variant && <StatusIcon variant={variant} className="size-7" />}
      </div>
      <p className="mt-3 text-display tabular-nums">{value}</p>
      {hint && <p className="mt-1 text-small text-text-muted">{hint}</p>}
      <span className="mt-auto inline-flex items-center gap-1 pt-4 text-small font-semibold text-primary group-hover:underline">
        View list
        <ArrowRight aria-hidden className="size-4" />
      </span>
    </Link>
  )
}
