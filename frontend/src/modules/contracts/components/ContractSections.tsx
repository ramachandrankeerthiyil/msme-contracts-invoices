import { CalendarDays, Scale, ShieldAlert, TriangleAlert, Users } from 'lucide-react'
import type { ReactNode } from 'react'

import { StatusBadge } from '@/components/common/StatusBadge'
import { formatDate } from '@/lib/format'
import { cn } from '@/lib/utils'

import type { ContractDetail, Severity, TermCategory } from '../api'
import { relativeDay, SEVERITY_META, TERM_LABELS } from '../status'
import { Quote } from './Quote'

function Section({
  id,
  title,
  icon: Icon,
  aside,
  children,
}: {
  id: string
  title: string
  icon: typeof Users
  aside?: ReactNode
  children: ReactNode
}) {
  return (
    <section aria-labelledby={id} className="flex flex-col gap-4 rounded-lg border border-border bg-bg p-6 shadow-card">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 id={id} className="flex items-center gap-3 text-h2">
          <Icon aria-hidden className="size-7 text-primary" />
          {title}
        </h2>
        {aside}
      </div>
      {children}
    </section>
  )
}

export function PartiesSection({ parties }: { parties: ContractDetail['parties'] }) {
  return (
    <Section id="parties-heading" title="Parties" icon={Users}>
      {parties.length === 0 ? (
        <p className="text-text-muted">No parties were found.</p>
      ) : (
        <ul className="flex flex-col gap-3">
          {parties.map((party) => (
            <li key={`${party.name}-${party.role}`}>
              <p className="font-semibold">{party.name}</p>
              <p className="text-small text-text-muted">{party.role}</p>
            </li>
          ))}
        </ul>
      )}
    </Section>
  )
}

export function KeyDatesSection({ contract }: { contract: ContractDetail }) {
  const soon = (days: number) => days >= 0 && days <= 3
  return (
    <Section id="dates-heading" title="Key dates" icon={CalendarDays}>
      {contract.key_dates.length === 0 ? (
        <p className="text-text-muted">No key dates were found.</p>
      ) : (
        <ul className="flex flex-col gap-4">
          {contract.key_dates.map((item) => (
            <li key={`${item.label}-${item.date}`}>
              <p className="flex flex-wrap items-center gap-x-3">
                <span className="font-semibold">{formatDate(item.date)}</span>
                <span>{item.label}</span>
                <span className={cn('text-small', soon(item.days_from_today) ? 'font-semibold text-warning' : 'text-text-muted')}>
                  {soon(item.days_from_today) && <TriangleAlert aria-hidden className="mr-1 inline size-4" />}
                  {relativeDay(item.days_from_today)}
                </span>
              </p>
              <Quote text={item.source_text} verified={item.source_verified} />
            </li>
          ))}
        </ul>
      )}
    </Section>
  )
}

const SEVERITIES: Severity[] = ['high', 'medium', 'low']

export function RisksSection({ risks }: { risks: ContractDetail['risks'] }) {
  const counts = SEVERITIES.map((s) => [s, risks.filter((r) => r.severity === s).length] as const)
  return (
    <Section
      id="risks-heading"
      title="Risks"
      icon={ShieldAlert}
      aside={
        <p className="text-text-muted">
          {counts.map(([severity, n]) => `${n} ${SEVERITY_META[severity].label.toLowerCase()}`).join(' · ')}
        </p>
      }
    >
      {risks.length === 0 ? (
        <p className="text-text-muted">No risks were found.</p>
      ) : (
        SEVERITIES.filter((severity) => risks.some((r) => r.severity === severity)).map((severity) => (
          <div key={severity} className="flex flex-col gap-3">
            <h3 className="text-h3">{SEVERITY_META[severity].label} risks</h3>
            <ul className="flex flex-col gap-4">
              {risks
                .filter((risk) => risk.severity === severity)
                .map((risk) => (
                  <li key={risk.title} className="rounded-lg border border-border p-4">
                    <div className="flex flex-wrap items-center gap-3">
                      <StatusBadge variant={SEVERITY_META[severity].variant} label={SEVERITY_META[severity].label} />
                      <p className="font-semibold">{risk.title}</p>
                    </div>
                    <p className="mt-2">{risk.description}</p>
                    <Quote text={risk.source_text} verified={risk.source_verified} />
                  </li>
                ))}
            </ul>
          </div>
        ))
      )}
    </Section>
  )
}

export function TermsSection({ terms }: { terms: ContractDetail['terms'] }) {
  const categories = [...new Set(terms.map((t) => t.category))] as TermCategory[]
  return (
    <Section id="terms-heading" title="Terms" icon={Scale}>
      {terms.length === 0 ? (
        <p className="text-text-muted">No terms were found.</p>
      ) : (
        categories.map((category) => (
          <div key={category} className="flex flex-col gap-3">
            <h3 className="text-h3">{TERM_LABELS[category]}</h3>
            <ul className="flex flex-col gap-4">
              {terms
                .filter((term) => term.category === category)
                .map((term) => (
                  <li key={term.summary}>
                    <p>{term.summary}</p>
                    <Quote text={term.source_text} verified={term.source_verified} />
                  </li>
                ))}
            </ul>
          </div>
        ))
      )}
    </Section>
  )
}
