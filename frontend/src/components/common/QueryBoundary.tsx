import type { UseQueryResult } from '@tanstack/react-query'
import type { ReactNode } from 'react'

import { Skeleton } from '@/components/ui/skeleton'

import { ErrorAlert } from './ErrorAlert'

interface QueryBoundaryProps<T> {
  query: UseQueryResult<T>
  loading?: ReactNode
  children: (data: T) => ReactNode
}

/**
 * Renders a query's loading, error or data state inside the page content area. Errors stay
 * local to this block, so the shell and navigation keep working (PLT-001 AC10).
 */
export function QueryBoundary<T>({ query, loading, children }: QueryBoundaryProps<T>) {
  if (query.isPending) {
    return (
      <div aria-busy="true" aria-live="polite">
        <span className="sr-only">Loading…</span>
        {loading ?? <Skeleton className="h-40 w-full" />}
      </div>
    )
  }
  if (query.isError) {
    return <ErrorAlert error={query.error} onRetry={() => void query.refetch()} />
  }
  return <>{children(query.data)}</>
}
