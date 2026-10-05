import type { ReactNode } from 'react'

import { cn } from '@/lib/utils'

import { STATUS_STYLES, StatusIcon } from './StatusBadge'

type AlertVariant = 'success' | 'warning' | 'info'

const BORDER: Record<AlertVariant, string> = {
  success: 'border-success',
  warning: 'border-warning',
  info: 'border-info',
}

interface InlineAlertProps {
  variant: AlertVariant
  title?: string
  /** `status` announces a result politely (e.g. "Reminder sent"). */
  role?: 'status'
  children: ReactNode
  className?: string
}

/** A calm inline banner with icon + text, never colour alone (ui-design-system.md "Alerts"). */
export function InlineAlert({ variant, title, role, children, className }: InlineAlertProps) {
  return (
    <div
      role={role}
      className={cn('flex gap-4 rounded-lg border p-5', STATUS_STYLES[variant].badge, BORDER[variant], className)}
    >
      <StatusIcon variant={variant} className="size-7" />
      <div className="min-w-0 text-text">
        {title && <p className="text-h3">{title}</p>}
        <div className={title ? 'mt-1' : undefined}>{children}</div>
      </div>
    </div>
  )
}
