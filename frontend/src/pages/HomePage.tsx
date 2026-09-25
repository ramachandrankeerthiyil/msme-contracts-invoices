import { ArrowRight, FileText, ReceiptIndianRupee, type LucideIcon } from 'lucide-react'
import type { ReactNode } from 'react'
import { Link } from 'react-router'

import { PageHeader } from '@/app/layout/PageHeader'
import { ContractsOverview } from '@/modules/contracts/components/ContractsOverview'
import { InvoicesOverview } from '@/modules/invoices/components/InvoicesOverview'

interface HomeSection {
  id: string
  title: string
  icon: LucideIcon
  dashboard: { label: string; to: string }
  content: ReactNode
}

const SECTIONS: HomeSection[] = [
  {
    id: 'contracts',
    title: 'Contracts',
    icon: FileText,
    dashboard: { label: 'Go to contract dashboard', to: '/contracts/dashboard' },
    content: <ContractsOverview />,
  },
  {
    id: 'invoices',
    title: 'Invoices',
    icon: ReceiptIndianRupee,
    dashboard: { label: 'Go to invoice dashboard', to: '/invoices/dashboard' },
    content: <InvoicesOverview />,
  },
]

/** Home (PLT-001 AC5): each module's headline numbers, loading and failing independently. */
export function HomePage() {
  return (
    <>
      <PageHeader description="What needs your attention across your contracts and invoices." />
      <div className="grid gap-8 lg:grid-cols-2">
        {SECTIONS.map((section) => (
          <section
            key={section.id}
            aria-labelledby={`home-${section.id}`}
            className="flex flex-col gap-6 rounded-lg border border-border bg-bg p-6 shadow-card"
          >
            <h2 id={`home-${section.id}`} className="flex items-center gap-3 text-h2">
              <section.icon aria-hidden className="size-7 text-primary" />
              {section.title}
            </h2>
            {section.content}
            <Link to={section.dashboard.to} className="link inline-flex items-center gap-2 self-start">
              {section.dashboard.label}
              <ArrowRight aria-hidden className="size-5" />
            </Link>
          </section>
        ))}
      </div>
    </>
  )
}
