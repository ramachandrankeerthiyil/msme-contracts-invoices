import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Download, FileText, Info, OctagonAlert, RotateCw, TriangleAlert } from 'lucide-react'
import { useEffect, useRef } from 'react'
import { useParams } from 'react-router'

import { PageHeader } from '@/app/layout/PageHeader'
import { EmptyState } from '@/components/common/EmptyState'
import { ErrorAlert } from '@/components/common/ErrorAlert'
import { QueryBoundary } from '@/components/common/QueryBoundary'
import { StatusBadge } from '@/components/common/StatusBadge'
import { Button, ButtonLink, buttonClasses } from '@/components/ui/button'
import { ApiError } from '@/lib/api/client'
import { formatDate } from '@/lib/format'

import { type ContractDetail, contractKeys, fileUrl, getContract, isProcessing, retryContract } from '../api'
import {
  KeyDatesSection,
  PartiesSection,
  RisksSection,
  TermsSection,
} from '../components/ContractSections'
import { ProcessingCard } from '../components/ProcessingCard'
import { LIFECYCLE_META } from '../status'

const POLL_MS = 2000

/** One contract (CON-002 AC4–AC8), including its reading progress (CON-001 AC8, AC9). */
export function ContractDetailPage() {
  const { contractId = '' } = useParams()
  const query = useQuery({
    queryKey: contractKeys.detail(contractId),
    queryFn: () => getContract(contractId),
    refetchInterval: (q) => (isProcessing(q.state.data?.processing_status) ? POLL_MS : false),
  })
  const contract = query.data
  const notFound = query.error instanceof ApiError && query.error.status === 404

  return (
    <>
      <PageHeader
        title={notFound ? 'Contract not found' : (contract?.title ?? 'Contract details')}
        crumb={contract?.title}
        action={
          contract ? (
            <a href={fileUrl(contract.id)} download className={buttonClasses('primary')}>
              <Download aria-hidden />
              Download original
            </a>
          ) : null
        }
      />
      {notFound ? (
        <EmptyState
          icon={FileText}
          title="We couldn't find that contract"
          description="The link may be out of date."
          action={
            <ButtonLink to="/contracts" variant="secondary">
              Go to all contracts
            </ButtonLink>
          }
        />
      ) : (
        <QueryBoundary query={query}>{(data) => <ContractBody contract={data} />}</QueryBoundary>
      )}
    </>
  )
}

function ContractBody({ contract }: { contract: ContractDetail }) {
  const status = contract.processing_status
  const previous = useRef(status)

  // When reading finishes while the page is open, announce the result by focusing the heading.
  useEffect(() => {
    if (isProcessing(previous.current) && status === 'completed') {
      document.getElementById('page-title')?.focus()
    }
    previous.current = status
  }, [status])

  if (isProcessing(status)) return <ProcessingCard status={status} />
  if (status === 'failed') return <FailedCard contract={contract} />

  const lifecycle = LIFECYCLE_META[contract.lifecycle]
  const datesLookWrong = contract.start_date && contract.end_date && contract.end_date < contract.start_date
  return (
    <div className="flex flex-col gap-8">
      <div className="flex flex-wrap items-center gap-3">
        <StatusBadge variant={lifecycle.variant} label={lifecycle.label} />
        {contract.at_risk && (
          <StatusBadge variant="warning" label={`At risk: ${contract.at_risk_reasons.join(' · ')}`} />
        )}
      </div>

      <p className="flex items-start gap-3 rounded-lg bg-info-bg px-4 py-3 text-info">
        <Info aria-hidden className="mt-1 size-5 shrink-0" />
        <span>
          <strong>Extracted by AI</strong> — please check against the original document.
        </span>
      </p>

      {datesLookWrong && (
        <p className="flex items-start gap-3 rounded-lg bg-warning-bg px-4 py-3 text-warning">
          <TriangleAlert aria-hidden className="mt-1 size-5 shrink-0" />
          The end date is before the start date. Please check these dates against the original.
        </p>
      )}

      {contract.summary && (
        <section aria-labelledby="summary-heading" className="flex flex-col gap-2">
          <h2 id="summary-heading" className="text-h2">
            Summary
          </h2>
          <p className="max-w-prose">{contract.summary}</p>
          <p className="text-text-muted">
            {contract.start_date ? `Starts ${formatDate(contract.start_date)}` : 'No start date found'} ·{' '}
            {contract.end_date ? `ends ${formatDate(contract.end_date)}` : 'no end date'}
          </p>
        </section>
      )}

      <div className="grid gap-8 xl:grid-cols-2">
        <PartiesSection parties={contract.parties} />
        <KeyDatesSection contract={contract} />
      </div>
      <RisksSection risks={contract.risks} />
      <TermsSection terms={contract.terms} />

      <p className="text-small text-text-muted">
        File: {contract.file_name} · uploaded {formatDate(contract.uploaded_at)}
        {contract.extraction_model &&
          contract.processed_at &&
          ` · read by ${contract.extraction_model} on ${formatDate(contract.processed_at)}`}
      </p>
    </div>
  )
}

function FailedCard({ contract }: { contract: ContractDetail }) {
  const queryClient = useQueryClient()
  const retry = useMutation({
    mutationFn: () => retryContract(contract.id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: contractKeys.all }),
  })
  return (
    <div className="flex flex-col gap-4">
      <div role="alert" className="flex gap-4 rounded-lg border border-danger bg-danger-bg p-6">
        <OctagonAlert aria-hidden className="size-7 shrink-0 text-danger" />
        <div>
          <p className="text-h3 text-danger">We couldn&apos;t read this contract</p>
          <p className="mt-1">{contract.error_message}</p>
          <Button className="mt-4" onClick={() => retry.mutate()} disabled={retry.isPending}>
            <RotateCw aria-hidden />
            Try again
          </Button>
        </div>
      </div>
      {retry.isError && <ErrorAlert error={retry.error} />}
    </div>
  )
}
