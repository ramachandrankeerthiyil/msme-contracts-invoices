import { useCallback, useMemo } from 'react'
import { useSearchParams } from 'react-router'

// The invoice list's state lives entirely in the URL, so views can be bookmarked and Back/Forward
// restore them (INV-002 AC7). Defaults are left out of the URL to keep it short.

export const VIEWS = ['follow_up', 'outstanding', 'at_risk', 'open', 'paid', 'all'] as const
export type View = (typeof VIEWS)[number]

export const SORT_KEYS = [
  'status',
  'invoice_number',
  'customer_name',
  'date_raised',
  'due_date',
  'amount',
  'paid_date',
] as const
export type SortKey = (typeof SORT_KEYS)[number]
export type SortOrder = 'asc' | 'desc'

export interface InvoiceQuery {
  view: View
  q: string
  updated: boolean
  dueFrom?: string
  dueTo?: string
  sort: SortKey
  order: SortOrder
  page: number
}

export const DEFAULT_QUERY: InvoiceQuery = {
  view: 'follow_up',
  q: '',
  updated: false,
  sort: 'status',
  order: 'asc',
  page: 1,
}

export const PAGE_SIZE = 25

const ISO_DATE = /^\d{4}-\d{2}-\d{2}$/

function pick<T extends string>(value: string | null, allowed: readonly T[], fallback: T): T {
  return allowed.includes(value as T) ? (value as T) : fallback
}

function isoOrUndefined(value: string | null): string | undefined {
  return value && ISO_DATE.test(value) ? value : undefined
}

export function parseInvoiceQuery(params: URLSearchParams): InvoiceQuery {
  const page = Number(params.get('page'))
  return {
    view: pick(params.get('view'), VIEWS, DEFAULT_QUERY.view),
    q: params.get('q') ?? '',
    updated: params.get('updated') === 'true',
    dueFrom: isoOrUndefined(params.get('due_from')),
    dueTo: isoOrUndefined(params.get('due_to')),
    sort: pick(params.get('sort'), SORT_KEYS, DEFAULT_QUERY.sort),
    order: pick(params.get('order'), ['asc', 'desc'] as const, DEFAULT_QUERY.order),
    page: Number.isInteger(page) && page >= 1 ? page : 1,
  }
}

/** Search params for the browser URL: only non-default values. */
export function toUrlParams(query: InvoiceQuery): URLSearchParams {
  const params = new URLSearchParams()
  if (query.view !== DEFAULT_QUERY.view) params.set('view', query.view)
  if (query.q) params.set('q', query.q)
  if (query.updated) params.set('updated', 'true')
  if (query.dueFrom) params.set('due_from', query.dueFrom)
  if (query.dueTo) params.set('due_to', query.dueTo)
  if (query.sort !== DEFAULT_QUERY.sort) params.set('sort', query.sort)
  if (query.order !== DEFAULT_QUERY.order) params.set('order', query.order)
  if (query.page !== 1) params.set('page', String(query.page))
  return params
}

/** Search params for the API. Export omits paging. */
export function toApiParams(query: InvoiceQuery, { paged = true } = {}): URLSearchParams {
  const params = new URLSearchParams({ view: query.view, sort: query.sort, order: query.order })
  if (query.q) params.set('q', query.q)
  if (query.updated) params.set('updated', 'true')
  if (query.dueFrom) params.set('due_from', query.dueFrom)
  if (query.dueTo) params.set('due_to', query.dueTo)
  if (paged) {
    params.set('page', String(query.page))
    params.set('page_size', String(PAGE_SIZE))
  }
  return params
}

/** A list filter sent by the API (dashboard card links) → the invoice list URL. */
export function listUrl(link: { view: View; due_from?: string; due_to?: string }): string {
  const params = toUrlParams({ ...DEFAULT_QUERY, view: link.view, dueFrom: link.due_from, dueTo: link.due_to })
  const search = params.toString()
  return search ? `/invoices?${search}` : '/invoices'
}

/**
 * Reads the list state from the URL and returns an updater. Any change other than the page
 * itself goes back to page 1.
 */
export function useInvoiceQuery(): [InvoiceQuery, (patch: Partial<InvoiceQuery>) => void] {
  const [params, setParams] = useSearchParams()
  const query = useMemo(() => parseInvoiceQuery(params), [params])
  const update = useCallback(
    (patch: Partial<InvoiceQuery>) => {
      const next = { ...query, ...patch }
      if (!('page' in patch)) next.page = 1
      setParams(toUrlParams(next))
    },
    [query, setParams],
  )
  return [query, update]
}
