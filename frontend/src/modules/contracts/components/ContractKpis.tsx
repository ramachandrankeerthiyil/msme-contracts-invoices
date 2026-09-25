import { KpiCard } from '@/components/common/KpiCard'

import type { DashboardData } from '../api'
import { listUrl } from '../query'

type Card = { key: keyof DashboardData['counts']; label: string }

const MAIN: Card[] = [
  { key: 'total', label: 'Total contracts' },
  { key: 'in_force', label: 'In force' },
  { key: 'at_risk', label: 'At risk' },
  { key: 'expired', label: 'Expired' },
  { key: 'not_started', label: 'Not yet started' },
]
const HOME: Card['key'][] = ['in_force', 'at_risk', 'expired']

function hint(data: DashboardData, key: Card['key']): string | undefined {
  if (key === 'total') return 'read so far'
  if (key === 'at_risk' && data.counts.at_risk > 0) {
    const { expiring_soon, high_risk } = data.at_risk_breakdown
    return `${expiring_soon} expiring soon · ${high_risk} with high risks`
  }
  return undefined
}

function variant(data: DashboardData, key: Card['key']) {
  const n = data.counts[key]
  if (key === 'at_risk') return n > 0 ? 'warning' : 'success'
  if (key === 'expired') return n > 0 ? 'danger' : undefined
  if (key === 'no_end_date') return 'info'
  return undefined
}

function CardFor({ data, card }: { data: DashboardData; card: Card }) {
  const link = card.key === 'total' ? data.links.total : data.links[card.key]
  return (
    <KpiCard
      label={card.label}
      value={data.counts[card.key].toLocaleString('en-IN')}
      hint={hint(data, card.key)}
      variant={variant(data, card.key)}
      to={listUrl(link ?? { view: 'all' })}
    />
  )
}

/**
 * Contract headline numbers (CON-003 AC1–AC3). `compact` shows the three Home cards
 * (PLT-001 AC5); otherwise all five plus the separate "Needs review" group.
 */
export function ContractKpis({ data, compact }: { data: DashboardData; compact?: boolean }) {
  const cards = compact ? MAIN.filter((card) => HOME.includes(card.key)) : MAIN
  return (
    <div className="flex flex-col gap-6">
      <div className="grid grid-cols-[repeat(auto-fit,minmax(14rem,1fr))] gap-6">
        {cards.map((card) => (
          <CardFor key={card.key} data={data} card={card} />
        ))}
      </div>
      {!compact && (
        <section aria-labelledby="needs-review-heading" className="flex flex-col gap-3">
          <h2 id="needs-review-heading" className="text-h2">
            Needs review
          </h2>
          <div className="max-w-md">
            <KpiCard
              label="No end date"
              value={data.counts.no_end_date.toLocaleString('en-IN')}
              hint="Contracts with no end date found — check they are still wanted"
              variant="info"
              to={listUrl(data.links.no_end_date ?? { view: 'no_end_date' })}
            />
          </div>
        </section>
      )}
    </div>
  )
}
