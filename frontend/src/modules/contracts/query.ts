import { useCallback, useMemo } from 'react'
import { useSearchParams } from 'react-router'

// Contract list state lives in the URL (CON-002), like the invoice list. Defaults are left out.

export const VIEWS = [
  'all',
  'in_force',
  'at_risk',
  'not_started',
  'expired',
  'no_end_date',
  'processing',
  'failed',
] as const
export type View = (typeof VIEWS)[number]

export const SORT_KEYS = ['end_date', 'start_date', 'title', 'status', 'high_risks', 'uploaded_at'] as const
export type SortKey = (typeof SORT_KEYS)[number]
export type SortOrder = 'asc' | 'desc'

export interface ContractQuery {
  view: View
  q: string
  sort: SortKey
  order: SortOrder
  page: number
}

export const DEFAULT_QUERY: ContractQuery = { view: 'all', q: '', sort: 'end_date', order: 'asc', page: 1 }
export const PAGE_SIZE = 25

function pick<T extends string>(value: string | null, allowed: readonly T[], fallback: T): T {
  return allowed.includes(value as T) ? (value as T) : fallback
}

export function parseContractQuery(params: URLSearchParams): ContractQuery {
  const page = Number(params.get('page'))
  return {
    view: pick(params.get('view'), VIEWS, DEFAULT_QUERY.view),
    q: params.get('q') ?? '',
    sort: pick(params.get('sort'), SORT_KEYS, DEFAULT_QUERY.sort),
    order: pick(params.get('order'), ['asc', 'desc'] as const, DEFAULT_QUERY.order),
    page: Number.isInteger(page) && page >= 1 ? page : 1,
  }
}

export function toUrlParams(query: ContractQuery): URLSearchParams {
  const params = new URLSearchParams()
  if (query.view !== DEFAULT_QUERY.view) params.set('view', query.view)
  if (query.q) params.set('q', query.q)
  if (query.sort !== DEFAULT_QUERY.sort) params.set('sort', query.sort)
  if (query.order !== DEFAULT_QUERY.order) params.set('order', query.order)
  if (query.page !== 1) params.set('page', String(query.page))
  return params
}

export function toApiParams(query: ContractQuery): URLSearchParams {
  const params = new URLSearchParams({
    view: query.view,
    sort: query.sort,
    order: query.order,
    page: String(query.page),
    page_size: String(PAGE_SIZE),
  })
  if (query.q) params.set('q', query.q)
  return params
}

/** A list filter sent by the API (dashboard card links) → the contract list URL. */
export function listUrl(link: { view: View }): string {
  const search = toUrlParams({ ...DEFAULT_QUERY, view: link.view }).toString()
  return search ? `/contracts?${search}` : '/contracts'
}

export function useContractQuery(): [ContractQuery, (patch: Partial<ContractQuery>) => void] {
  const [params, setParams] = useSearchParams()
  const query = useMemo(() => parseContractQuery(params), [params])
  const update = useCallback(
    (patch: Partial<ContractQuery>) => {
      const next = { ...query, ...patch }
      if (!('page' in patch)) next.page = 1
      setParams(toUrlParams(next))
    },
    [query, setParams],
  )
  return [query, update]
}
