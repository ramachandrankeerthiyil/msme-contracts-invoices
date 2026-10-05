import { QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { createMemoryRouter, RouterProvider } from 'react-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { createQueryClient } from '@/app/queryClient'
import { routes } from '@/app/router'

import * as api from '../api'
import { EMPTY_PAGE, INVOICE_PAGE } from '../testData'

vi.mock('../api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api')>()
  return { ...actual, listInvoices: vi.fn() }
})

function renderAt(path = '/invoices') {
  const router = createMemoryRouter(routes, { initialEntries: [path] })
  render(
    <QueryClientProvider client={createQueryClient()}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  )
  return router
}

const search = (router: ReturnType<typeof renderAt>) => new URLSearchParams(router.state.location.search)

describe('InvoicesPage', () => {
  beforeEach(() => {
    vi.mocked(api.listInvoices).mockReset().mockResolvedValue(INVOICE_PAGE)
  })

  it('INV_002_AC1_AC1a shows every column with badges, due hints and record status', async () => {
    renderAt()

    const table = await screen.findByRole('table', { name: 'Invoices' })
    const rows = within(table).getAllByRole('row')
    expect(within(rows[0]!).getAllByRole('columnheader').map((th) => th.textContent)).toEqual([
      'Invoice', 'Customer', 'Due', 'Amount', 'Status', 'Reminder',
    ])
    const overdue = within(rows[1]!)
    expect(overdue.getByText('INV-2606')).toBeInTheDocument()
    expect(overdue.getByText('Raised 16 Jul 2026')).toBeInTheDocument()
    expect(overdue.getByText('₹1,25,000.00')).toBeInTheDocument()
    expect(overdue.getByText('41 days overdue')).toBeInTheDocument()
    expect(overdue.getByText('Outstanding')).toBeInTheDocument()
    expect(overdue.getByText('New')).toBeInTheDocument()

    const atRisk = within(rows[2]!)
    expect(atRisk.getByText('due today')).toBeInTheDocument()
    expect(atRisk.getByText('At risk')).toBeInTheDocument()
    expect(atRisk.getByText('Updated on 24 Sep 2026')).toBeInTheDocument()

    expect(within(rows[3]!).getByText('paid on 12 Sep 2026')).toBeInTheDocument()
  })

  it('INV_002_AC3 shows tabs with counts, Needs follow-up selected by default', async () => {
    renderAt()

    const tabs = within(await screen.findByRole('navigation', { name: 'Filter by status' }))
    await waitFor(() => expect(tabs.getByRole('link', { current: 'page' })).toHaveTextContent('Needs follow-up9'))
    expect(tabs.getByRole('link', { name: /^All/ })).toHaveTextContent('17')
  })

  it('INV_002_AC3_AC7 switching tabs updates the URL and requests that view', async () => {
    const router = renderAt()

    await userEvent.click(await screen.findByRole('link', { name: /^Paid/ }))

    expect(search(router).get('view')).toBe('paid')
    await waitFor(() =>
      expect(vi.mocked(api.listInvoices)).toHaveBeenLastCalledWith(expect.objectContaining({ view: 'paid' })),
    )
  })

  it('INV_002_AC4 clicking a column sorts it, clicking again reverses', async () => {
    const router = renderAt()
    const table = await screen.findByRole('table', { name: 'Invoices' })

    await userEvent.click(within(table).getByRole('button', { name: 'Amount' }))
    expect(search(router).get('sort')).toBe('amount')
    expect(search(router).get('order')).toBeNull() // asc is the default

    await userEvent.click(within(screen.getByRole('table', { name: 'Invoices' })).getByRole('button', { name: 'Amount' }))
    expect(search(router).get('order')).toBe('desc')
    await waitFor(() =>
      expect(screen.getByRole('columnheader', { name: 'Amount' })).toHaveAttribute('aria-sort', 'descending'),
    )
  })

  it('INV_002_AC5 search updates the URL after typing, and updated-only is a checkbox', async () => {
    const router = renderAt()

    await userEvent.type(await screen.findByLabelText('Search invoice number or customer'), 'deccan')
    await waitFor(() => expect(search(router).get('q')).toBe('deccan'))

    await userEvent.click(screen.getByRole('checkbox', { name: 'Only show updated invoices' }))
    expect(search(router).get('updated')).toBe('true')
    expect(search(router).get('q')).toBe('deccan')
  })

  it('INV_002_AC6 shows the total for everything that matches', async () => {
    renderAt()

    expect(await screen.findByText(/Total:/)).toHaveTextContent('Total: ₹9,94,150.75 across 9 invoices')
  })

  it('INV_002_AC9 export links to the current view', async () => {
    renderAt('/invoices?view=outstanding&q=acme')

    expect(await screen.findByRole('link', { name: 'Export to Excel' })).toHaveAttribute(
      'href',
      '/api/invoices/export?view=outstanding&sort=status&order=asc&q=acme',
    )
  })

  it('INV_003_AC6 shows and clears the due-date range from dashboard links', async () => {
    const router = renderAt('/invoices?view=all&due_from=2026-09-24&due_to=2026-09-30')

    expect(await screen.findByText('Due 24 Sep – 30 Sep 2026')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Clear due date filter' }))
    expect(search(router).get('due_from')).toBeNull()
    expect(search(router).get('view')).toBe('all')
  })

  it('INV_002_AC8 empty database offers Upload invoices', async () => {
    vi.mocked(api.listInvoices).mockResolvedValue(EMPTY_PAGE)
    renderAt()

    expect(await screen.findByText('No invoices yet')).toBeInTheDocument()
    expect(within(screen.getByRole('main')).getAllByRole('link', { name: 'Upload invoices' }).length).toBeGreaterThan(0)
  })

  it('INV_002_AC8 no matches offers Clear filters', async () => {
    vi.mocked(api.listInvoices).mockResolvedValue({ ...EMPTY_PAGE, counts: INVOICE_PAGE.counts })
    const router = renderAt('/invoices?q=zzz')

    expect(await screen.findByText('No invoices match these filters')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Clear filters' }))
    expect(search(router).get('q')).toBeNull()
    expect(search(router).get('view')).toBe('all')
  })
})
