import { CircleCheck, Clock, Info, OctagonAlert, TriangleAlert, type LucideIcon } from 'lucide-react'

import { cn } from '@/lib/utils'

// Status is never shown by colour alone: every variant has a fixed icon plus a text label
// (ui-design-system.md "Status colours").
export type StatusVariant = 'success' | 'warning' | 'danger' | 'info' | 'neutral'

export const STATUS_STYLES: Record<StatusVariant, { icon: LucideIcon; text: string; badge: string }> = {
  success: { icon: CircleCheck, text: 'text-success', badge: 'bg-success-bg text-success' },
  warning: { icon: TriangleAlert, text: 'text-warning', badge: 'bg-warning-bg text-warning' },
  danger: { icon: OctagonAlert, text: 'text-danger', badge: 'bg-danger-bg text-danger' },
  info: { icon: Info, text: 'text-info', badge: 'bg-info-bg text-info' },
  neutral: { icon: Clock, text: 'text-neutral', badge: 'bg-neutral-bg text-neutral' },
}

export function StatusIcon({ variant, className }: { variant: StatusVariant; className?: string }) {
  const { icon: Icon, text } = STATUS_STYLES[variant]
  return <Icon aria-hidden data-status-icon={variant} className={cn('shrink-0', text, className)} />
}

interface StatusBadgeProps {
  variant: StatusVariant
  label: string
  /** Let long labels (e.g. "Updated on 24 Sep 2026") wrap in narrow table cells. */
  wrap?: boolean
  className?: string
}

export function StatusBadge({ variant, label, wrap, className }: StatusBadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 px-3 py-1 text-small font-semibold',
        wrap ? 'rounded-lg' : 'rounded-full whitespace-nowrap',
        STATUS_STYLES[variant].badge,
        className,
      )}
    >
      <StatusIcon variant={variant} className="size-4" />
      {label}
    </span>
  )
}
