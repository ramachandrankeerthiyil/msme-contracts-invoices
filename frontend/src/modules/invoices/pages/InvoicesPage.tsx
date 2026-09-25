import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { ReceiptIndianRupee, SearchX, Upload, X } from 'lucide-react'
import { Link } from 'react-router'

import { PageHeader } from '@/app/layout/PageHeader'
import { EmptyState } from '@/components/common/EmptyState'
import { Pagination } from '@/components/common/Pagination'
import { QueryBoundary } from '@/components/common/QueryBoundary'
import { Button, ButtonLink } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { countOf, formatINR } from '@/lib/format'

import { invoiceKeys, listInvoices } from '../api'
import { InvoiceTable } from '../components/InvoiceTable'
import { InvoiceToolbar } from '../components/InvoiceToolbar'
import { StatusTabs } from '../components/StatusTabs'
import { PAGE_SIZE, type SortKey, toUrlParams, useInvoiceQuery } from '../query'

/** All invoices with status flags (INV-002). */
export function InvoicesPage() {
  const [query, update] = useInvoiceQuery()
  const result = useQuery({
    queryKey: invoiceKeys.list(query),
    queryFn: () => listInvoices(query),
    placeholderData: keepPreviousData,
  })
  const hasFilters = Boolean(query.q || query.updated || query.dueFrom || query.dueTo)

  function sortBy(key: SortKey) {
    if (query.sort === key) update({ order: query.order === 'asc' ? 'desc' : 'asc' })
    else update({ sort: key, order: 'asc' })
  }

  function clearFilters() {
    update({ view: 'all', q: '', updated: false, dueFrom: undefined, dueTo: undefined })
  }

  return (
    <>
      <PageHeader description="Outstanding and at-risk invoices are flagged, so you know whom to chase first." />
      <div className="flex flex-col gap-6">
        <StatusTabs query={query} counts={result.data?.counts} />
        <InvoiceToolbar query={query} onChange={update} />
        <QueryBoundary query={result} loading={<TableSkeleton />}>
          {(page) => {
            if (page.counts.all === 0 && !hasFilters) {
              return (
                <EmptyState
                  icon={ReceiptIndianRupee}
                  title="No invoices yet"
                  description="Upload your invoice spreadsheet to see what is outstanding and what needs follow-up."
                  action={
                    <ButtonLink to="/invoices/upload">
                      <Upload aria-hidden />
                      Upload invoices
                    </ButtonLink>
                  }
                />
              )
            }
            if (page.total === 0) {
              return (
                <EmptyState
                  icon={SearchX}
                  title={hasFilters ? 'No invoices match these filters' : 'No invoices in this view'}
                  description={
                    hasFilters
                      ? 'Try a different search, or clear the filters to see all invoices.'
                      : 'Choose another tab, or show all invoices.'
                  }
                  action={
                    <Button variant="secondary" onClick={clearFilters}>
                      <X aria-hidden />
                      {hasFilters ? 'Clear filters' : 'Show all invoices'}
                    </Button>
                  }
                />
              )
            }
            if (page.items.length === 0) {
              return (
                <p>
                  No invoices on this page.{' '}
                  <Link to={`?${toUrlParams({ ...query, page: 1 })}`} className="link">
                    Go to the first page
                  </Link>
                </p>
              )
            }
            return (
              <div className="flex flex-col gap-4">
                <p className="text-h3" aria-live="polite">
                  Total: <span className="tabular-nums">{formatINR(page.total_amount)}</span> across{' '}
                  {countOf(page.total, 'invoice')}
                </p>
                <InvoiceTable items={page.items} query={query} onSort={sortBy} stale={result.isPlaceholderData} />
                <Pagination
                  page={page.page}
                  pageSize={PAGE_SIZE}
                  total={page.total}
                  onPage={(next) => update({ page: next })}
                />
              </div>
            )
          }}
        </QueryBoundary>
      </div>
    </>
  )
}

function TableSkeleton() {
  return (
    <div className="flex flex-col gap-3">
      <Skeleton className="h-8 w-80" />
      {Array.from({ length: 6 }, (_, index) => (
        <Skeleton key={index} className="h-14 w-full" />
      ))}
    </div>
  )
}
