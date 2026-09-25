import { ArrowRight, ChevronRight, PartyPopper } from 'lucide-react'
import { Link } from 'react-router'

import { StatusIcon } from '@/components/common/StatusBadge'
import { formatINR } from '@/lib/format'

import type { ListLink, TopFollowUpItem } from '../api'
import { DEFAULT_QUERY, listUrl, toUrlParams } from '../query'
import { dueHintClass, invoiceDueHint, STATUS_META } from '../status'

interface TopFollowUpProps {
  items: TopFollowUpItem[]
  followUpLink: ListLink
}

/** "Top 5 to follow up", most overdue first (INV-003 AC7). */
export function TopFollowUp({ items, followUpLink }: TopFollowUpProps) {
  return (
    <section
      aria-labelledby="top-follow-up-heading"
      className="flex flex-col gap-4 rounded-lg border border-border bg-bg p-6 shadow-card"
    >
      <h2 id="top-follow-up-heading" className="text-h2">
        Top 5 to follow up
      </h2>
      {items.length === 0 ? (
        <p className="flex items-center gap-3 text-text-muted">
          <PartyPopper aria-hidden className="size-6 text-success" />
          No invoices need follow-up. Well done.
        </p>
      ) : (
        <ol className="flex flex-col divide-y divide-border rounded-lg border border-border">
          {items.map((item) => (
            <li key={item.id}>
              <Link
                to={`/invoices?${toUrlParams({ ...DEFAULT_QUERY, q: item.invoice_number })}`}
                className="flex items-center gap-4 p-4 transition-colors hover:bg-surface"
              >
                <StatusIcon variant={STATUS_META[item.status].variant} className="size-6" />
                <span className="sr-only">{STATUS_META[item.status].label}:</span>
                <div className="min-w-0 flex-1">
                  <p className="font-semibold">{item.customer_name}</p>
                  <p className="text-small text-text-muted">
                    {item.invoice_number} ·{' '}
                    <span className={dueHintClass(item.status)}>
                      {invoiceDueHint({ paid_date: null, days_until_due: item.days_until_due })}
                    </span>
                  </p>
                </div>
                <p className="font-semibold whitespace-nowrap tabular-nums">{formatINR(item.amount)}</p>
                <ChevronRight aria-hidden className="size-5 shrink-0 text-text-muted" />
              </Link>
            </li>
          ))}
        </ol>
      )}
      <Link to={listUrl(followUpLink)} className="link inline-flex items-center gap-2 self-start">
        See all invoices needing follow-up
        <ArrowRight aria-hidden className="size-5" />
      </Link>
    </section>
  )
}
