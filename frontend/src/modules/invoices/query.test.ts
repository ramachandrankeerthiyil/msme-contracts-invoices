import { describe, expect, it } from 'vitest'

import { DEFAULT_QUERY, listUrl, parseInvoiceQuery, toApiParams, toUrlParams } from './query'

describe('INV_002_AC7 invoice list URL state', () => {
  it('parses a full URL and round-trips it', () => {
    const search = 'view=outstanding&q=acme&updated=true&due_from=2026-09-24&due_to=2026-09-30&sort=amount&order=desc&page=3'
    const query = parseInvoiceQuery(new URLSearchParams(search))

    expect(query).toEqual({
      view: 'outstanding',
      q: 'acme',
      updated: true,
      dueFrom: '2026-09-24',
      dueTo: '2026-09-30',
      sort: 'amount',
      order: 'desc',
      page: 3,
    })
    expect(toUrlParams(query).toString()).toBe(search)
  })

  it('falls back to defaults for missing or invalid values', () => {
    const query = parseInvoiceQuery(new URLSearchParams('view=bogus&sort=nope&order=up&page=-2&due_to=tomorrow'))

    expect(query).toEqual(DEFAULT_QUERY)
  })

  it('leaves defaults out of the URL', () => {
    expect(toUrlParams(DEFAULT_QUERY).toString()).toBe('')
  })

  it('always sends view, sort and order to the API, and paging unless exporting', () => {
    expect(toApiParams(DEFAULT_QUERY).toString()).toBe(
      'view=follow_up&sort=status&order=asc&page=1&page_size=25',
    )
    expect(toApiParams(DEFAULT_QUERY, { paged: false }).toString()).toBe(
      'view=follow_up&sort=status&order=asc',
    )
  })

  it('INV_003_AC6 turns dashboard links into list URLs', () => {
    expect(listUrl({ view: 'all', due_from: '2026-09-24', due_to: '2026-09-30' })).toBe(
      '/invoices?view=all&due_from=2026-09-24&due_to=2026-09-30',
    )
    expect(listUrl({ view: 'follow_up', due_to: '2026-09-30' })).toBe('/invoices?due_to=2026-09-30')
  })
})
