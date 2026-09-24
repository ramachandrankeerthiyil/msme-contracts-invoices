import { ArrowRight, FileText, ReceiptIndianRupee, Upload, type LucideIcon } from 'lucide-react'
import { Link } from 'react-router'

import { PageHeader } from '@/app/layout/PageHeader'
import { EmptyState } from '@/components/common/EmptyState'
import { ButtonLink } from '@/components/ui/button'

interface HomeSection {
  id: string
  title: string
  icon: LucideIcon
  dashboard: { label: string; to: string }
  empty: { title: string; description: string }
  upload: { label: string; to: string }
}

const SECTIONS: HomeSection[] = [
  {
    id: 'contracts',
    title: 'Contracts',
    icon: FileText,
    dashboard: { label: 'Go to contract dashboard', to: '/contracts/dashboard' },
    empty: {
      title: 'No contracts yet',
      description: 'Upload a contract and we will pick out the parties, key dates, terms and risks for you.',
    },
    upload: { label: 'Upload contract', to: '/contracts/upload' },
  },
  {
    id: 'invoices',
    title: 'Invoices',
    icon: ReceiptIndianRupee,
    dashboard: { label: 'Go to invoice dashboard', to: '/invoices/dashboard' },
    empty: {
      title: 'No invoices yet',
      description: 'Upload your invoice spreadsheet to see what is outstanding and what needs follow-up this week.',
    },
    upload: { label: 'Upload invoices', to: '/invoices/upload' },
  },
]

/**
 * Home (PLT-001 AC5). Each section will show its dashboard's headline numbers once the
 * dashboard APIs exist (CON-003, INV-003); until then it shows its empty state.
 */
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
            <EmptyState
              icon={section.icon}
              title={section.empty.title}
              description={section.empty.description}
              action={
                <ButtonLink to={section.upload.to}>
                  <Upload aria-hidden />
                  {section.upload.label}
                </ButtonLink>
              }
            />
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
