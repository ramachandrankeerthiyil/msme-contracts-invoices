import type { LucideIcon } from 'lucide-react'
import type { ReactNode } from 'react'

interface EmptyStateProps {
  icon: LucideIcon
  title: string
  description?: string
  action?: ReactNode
}

export function EmptyState({ icon: Icon, title, description, action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center rounded-lg border border-dashed border-border bg-surface px-6 py-12 text-center">
      <span className="grid size-16 place-items-center rounded-full bg-primary-soft text-primary">
        <Icon aria-hidden className="size-8" />
      </span>
      <p className="mt-4 text-h3">{title}</p>
      {description && <p className="mt-2 max-w-prose text-text-muted">{description}</p>}
      {action && <div className="mt-6">{action}</div>}
    </div>
  )
}
