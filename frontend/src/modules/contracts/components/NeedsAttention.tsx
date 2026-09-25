import { ChevronRight, PartyPopper } from 'lucide-react'
import { Link } from 'react-router'

import { StatusIcon } from '@/components/common/StatusBadge'

import type { ContractListItem } from '../api'
import { endHint, LIFECYCLE_META } from '../status'

/** Up to 5 contracts to look at: at risk first, then the soonest end dates (CON-003 AC4). */
export function NeedsAttention({ items }: { items: ContractListItem[] }) {
  return (
    <section
      aria-labelledby="needs-attention-heading"
      className="flex flex-col gap-4 rounded-lg border border-border bg-bg p-6 shadow-card"
    >
      <h2 id="needs-attention-heading" className="text-h2">
        Needs attention
      </h2>
      {items.length === 0 ? (
        <p className="flex items-center gap-3 text-text-muted">
          <PartyPopper aria-hidden className="size-6 text-success" />
          Nothing needs attention right now.
        </p>
      ) : (
        <ol className="flex flex-col divide-y divide-border rounded-lg border border-border">
          {items.map((item) => {
            const variant = item.at_risk ? 'warning' : LIFECYCLE_META[item.lifecycle].variant
            return (
              <li key={item.id}>
                <Link to={`/contracts/${item.id}`} className="flex items-center gap-4 p-4 transition-colors hover:bg-surface">
                  <StatusIcon variant={variant} className="size-6" />
                  <span className="sr-only">{item.at_risk ? 'At risk' : LIFECYCLE_META[item.lifecycle].label}:</span>
                  <div className="min-w-0 flex-1">
                    <p className="font-semibold">{item.title}</p>
                    {item.parties.length > 0 && (
                      <p className="text-small text-text-muted">{item.parties.join(' · ')}</p>
                    )}
                    <p className="text-small">
                      <span className="text-text-muted">{endHint(item.days_until_end)}</span>
                      {item.at_risk && (
                        <span className="font-semibold text-warning"> · {item.at_risk_reasons.join(' · ')}</span>
                      )}
                    </p>
                  </div>
                  <ChevronRight aria-hidden className="size-5 shrink-0 text-text-muted" />
                </Link>
              </li>
            )
          })}
        </ol>
      )}
    </section>
  )
}
