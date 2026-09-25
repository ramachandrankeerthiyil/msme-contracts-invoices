import { useQuery } from '@tanstack/react-query'
import { ReceiptIndianRupee, Upload } from 'lucide-react'

import { PageHeader } from '@/app/layout/PageHeader'
import { EmptyState } from '@/components/common/EmptyState'
import { QueryBoundary } from '@/components/common/QueryBoundary'
import { ButtonLink } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { formatDateRange, formatDayMonth } from '@/lib/format'

import { type DashboardData, getDashboard, invoiceKeys } from '../api'
import { InvoiceKpis } from '../components/InvoiceKpis'
import { TopFollowUp } from '../components/TopFollowUp'
import { ValueByStatus } from '../components/ValueByStatus'

/** Invoice dashboard (INV-003). Every number is computed by invoice-service (AC5). */
export function InvoiceDashboardPage() {
  const query = useQuery({ queryKey: invoiceKeys.dashboard(), queryFn: getDashboard })

  return (
    <>
      <PageHeader />
      <QueryBoundary query={query} loading={<DashboardSkeleton />}>
        {(data) =>
          data.has_data ? (
            <DashboardContent data={data} />
          ) : (
            <EmptyState
              icon={ReceiptIndianRupee}
              title="No invoices yet"
              description="Upload your invoice spreadsheet to see this week's totals and who needs follow-up."
              action={
                <ButtonLink to="/invoices/upload">
                  <Upload aria-hidden />
                  Upload invoices
                </ButtonLink>
              }
            />
          )
        }
      </QueryBoundary>
    </>
  )
}

function DashboardContent({ data }: { data: DashboardData }) {
  const { week } = data
  return (
    <div className="flex flex-col gap-8">
      <p className="text-text-muted">
        Week of <strong className="text-text">{formatDateRange(week.start, week.end)}</strong> (from your
        upload on {formatDayMonth(week.anchor_uploaded_at)})
      </p>
      <InvoiceKpis data={data} />
      <div className="grid gap-8 xl:grid-cols-2">
        <TopFollowUp items={data.top_follow_up} followUpLink={data.links.follow_up} />
        <ValueByStatus rows={data.value_by_status} />
      </div>
    </div>
  )
}

function DashboardSkeleton() {
  return (
    <div className="flex flex-col gap-8">
      <Skeleton className="h-6 w-96" />
      <div className="grid grid-cols-[repeat(auto-fit,minmax(18rem,1fr))] gap-6">
        {[0, 1, 2].map((key) => (
          <Skeleton key={key} className="h-44" />
        ))}
      </div>
      <div className="grid gap-8 xl:grid-cols-2">
        <Skeleton className="h-80" />
        <Skeleton className="h-80" />
      </div>
    </div>
  )
}
