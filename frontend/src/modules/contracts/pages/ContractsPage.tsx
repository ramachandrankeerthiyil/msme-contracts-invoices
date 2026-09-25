import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { FileText, Hourglass, SearchX, Upload, X } from 'lucide-react'
import { Link } from 'react-router'

import { PageHeader } from '@/app/layout/PageHeader'
import { EmptyState } from '@/components/common/EmptyState'
import { FilterTabs } from '@/components/common/FilterTabs'
import { Pagination } from '@/components/common/Pagination'
import { QueryBoundary } from '@/components/common/QueryBoundary'
import { SearchField } from '@/components/common/SearchField'
import { Button, ButtonLink } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { countOf } from '@/lib/format'

import { contractKeys, listContracts } from '../api'
import { ContractTable } from '../components/ContractTable'
import { PAGE_SIZE, type SortKey, toUrlParams, useContractQuery } from '../query'
import { VIEW_TABS } from '../status'

/** All contracts (CON-002 AC1–AC3, AC9). */
export function ContractsPage() {
  const [query, update] = useContractQuery()
  const result = useQuery({
    queryKey: contractKeys.list(query),
    queryFn: () => listContracts(query),
    placeholderData: keepPreviousData,
  })
  const counts = result.data?.counts

  function sortBy(key: SortKey) {
    if (query.sort === key) update({ order: query.order === 'asc' ? 'desc' : 'asc' })
    else update({ sort: key, order: 'asc' })
  }

  return (
    <>
      <PageHeader description="Every contract you have uploaded, with its status and risks." />
      <div className="flex flex-col gap-6">
        <FilterTabs
          label="Filter by status"
          tabs={VIEW_TABS}
          current={query.view}
          counts={counts}
          hrefFor={(view) => `?${toUrlParams({ ...query, view, page: 1 })}`}
        />
        <SearchField
          id="contract-search"
          label="Search contract title or party"
          placeholder="e.g. Supply Agreement or Bluewave"
          value={query.q}
          onSearch={(q) => update({ q })}
        />
        {counts && counts.processing > 0 && query.view !== 'processing' && (
          <p className="flex items-center gap-3 rounded-lg bg-info-bg px-4 py-3 text-info">
            <Hourglass aria-hidden className="size-5 shrink-0" />
            <span>
              {countOf(counts.processing, 'contract')} {counts.processing === 1 ? 'is' : 'are'} still
              being read.{' '}
              <Link to={`?${toUrlParams({ ...query, view: 'processing', page: 1 })}`} className="link">
                Show {counts.processing === 1 ? 'it' : 'them'}
              </Link>
            </span>
          </p>
        )}
        <QueryBoundary query={result} loading={<TableSkeleton />}>
          {(page) => {
            const hasContracts = Object.values(page.counts).some((n) => n > 0)
            if (!hasContracts && !query.q) {
              return (
                <EmptyState
                  icon={FileText}
                  title="No contracts yet"
                  description="Upload a contract and we will pick out the parties, key dates, terms and risks for you."
                  action={
                    <ButtonLink to="/contracts/upload">
                      <Upload aria-hidden />
                      Upload contract
                    </ButtonLink>
                  }
                />
              )
            }
            if (page.total === 0) {
              return (
                <EmptyState
                  icon={SearchX}
                  title={query.q ? 'No contracts match your search' : 'No contracts in this view'}
                  description={
                    query.q
                      ? 'Try a different search, or clear it to see all contracts.'
                      : 'Choose another tab, or show all contracts.'
                  }
                  action={
                    <Button variant="secondary" onClick={() => update({ view: 'all', q: '' })}>
                      <X aria-hidden />
                      {query.q ? 'Clear search' : 'Show all contracts'}
                    </Button>
                  }
                />
              )
            }
            return (
              <div className="flex flex-col gap-4">
                <ContractTable items={page.items} query={query} onSort={sortBy} stale={result.isPlaceholderData} />
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
      {Array.from({ length: 5 }, (_, index) => (
        <Skeleton key={index} className="h-14 w-full" />
      ))}
    </div>
  )
}
