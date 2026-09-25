import { useQuery } from '@tanstack/react-query'
import { FileText, Info, Upload } from 'lucide-react'
import { Link } from 'react-router'

import { PageHeader } from '@/app/layout/PageHeader'
import { EmptyState } from '@/components/common/EmptyState'
import { QueryBoundary } from '@/components/common/QueryBoundary'
import { StatusBars } from '@/components/common/StatusBars'
import { ButtonLink } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { countOf, formatDate } from '@/lib/format'

import { contractKeys, type DashboardData, getDashboard } from '../api'
import { ContractKpis } from '../components/ContractKpis'
import { NeedsAttention } from '../components/NeedsAttention'
import { listUrl } from '../query'
import { LIFECYCLE_META } from '../status'

/** Contract dashboard (CON-003). Every number is computed by contract-service (AC2). */
export function ContractDashboardPage() {
  const query = useQuery({ queryKey: contractKeys.dashboard(), queryFn: getDashboard })
  return (
    <>
      <PageHeader />
      <QueryBoundary query={query} loading={<Skeleton className="h-96 w-full" />}>
        {(data) =>
          data.has_data ? (
            <DashboardContent data={data} />
          ) : (
            <EmptyState
              icon={FileText}
              title="No contracts yet"
              description="Upload a contract to see how many are in force, at risk or expired."
              action={
                <ButtonLink to="/contracts/upload">
                  <Upload aria-hidden />
                  Upload contract
                </ButtonLink>
              }
            />
          )
        }
      </QueryBoundary>
    </>
  )
}

function UnreadNote({ data }: { data: DashboardData }) {
  const { processing, failed } = data.unread
  if (!processing && !failed) return null
  return (
    <p className="flex flex-wrap items-center gap-x-4 gap-y-2 rounded-lg bg-info-bg px-4 py-3 text-info">
      <Info aria-hidden className="size-5 shrink-0" />
      {processing > 0 && (
        <Link to={listUrl({ view: 'processing' })} className="link">
          {countOf(processing, 'contract')} {processing === 1 ? 'is' : 'are'} still being read
        </Link>
      )}
      {failed > 0 && (
        <Link to={listUrl({ view: 'failed' })} className="link">
          {countOf(failed, 'contract')} could not be read
        </Link>
      )}
    </p>
  )
}

function DashboardContent({ data }: { data: DashboardData }) {
  return (
    <div className="flex flex-col gap-8">
      <p className="text-text-muted">
        Figures as of <strong className="text-text">{formatDate(data.today)}</strong>
      </p>
      <UnreadNote data={data} />
      <ContractKpis data={data} />
      <div className="grid gap-8 xl:grid-cols-2">
        <NeedsAttention items={data.needs_attention} />
        <StatusBars
          id="contracts-by-status-heading"
          heading="Contracts by status"
          caption="Number of read contracts in each status"
          valueHeader="Number of contracts"
          rows={data.by_lifecycle.map((row) => ({
            key: row.lifecycle,
            label: LIFECYCLE_META[row.lifecycle].label,
            variant: LIFECYCLE_META[row.lifecycle].variant,
            value: row.count,
            display: row.count.toLocaleString('en-IN'),
          }))}
        />
      </div>
    </div>
  )
}
