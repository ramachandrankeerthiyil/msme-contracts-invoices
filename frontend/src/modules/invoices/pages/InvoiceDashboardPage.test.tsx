import { QueryClientProvider } from '@tanstack/react-query'
import { render, screen, within } from '@testing-library/react'
import { createMemoryRouter, RouterProvider } from 'react-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { createQueryClient } from '@/app/queryClient'
import { routes } from '@/app/router'

import * as api from '../api'
import { DASHBOARD } from '../testData'

vi.mock('../api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api')>()
  return { ...actual, getDashboard: vi.fn() }
})

function renderAt(path: string) {
  render(
    <QueryClientProvider client={createQueryClient()}>
      <RouterProvider router={createMemoryRouter(routes, { initialEntries: [path] })} />
    </QueryClientProvider>,
  )
}

describe('InvoiceDashboardPage', () => {
  beforeEach(() => {
    vi.mocked(api.getDashboard).mockReset().mockResolvedValue(DASHBOARD)
  })

  it('INV_003_AC1 states the week and where it comes from', async () => {
    renderAt('/invoices/dashboard')

    expect(await screen.findByText(/Week of/)).toHaveTextContent(
      'Week of 24 Sep – 30 Sep 2026 (from your upload on 24 Sep)',
    )
  })

  it('INV_003_AC2_AC6 shows the three KPI cards, each linking to its list', async () => {
    renderAt('/invoices/dashboard')

    expect(await screen.findByRole('link', { name: 'Total invoice value: ₹5,57,250.00. Due this week' })).toHaveAttribute(
      'href',
      '/invoices?view=all&due_from=2026-09-24&due_to=2026-09-30',
    )
    expect(screen.getByRole('link', { name: 'Invoices this week: 6. Due this week' })).toHaveAttribute(
      'href',
      '/invoices?view=all&due_from=2026-09-24&due_to=2026-09-30',
    )
    expect(screen.getByRole('link', { name: 'Need follow-up: 9. 5 outstanding · 4 at risk' })).toHaveAttribute(
      'href',
      '/invoices?due_to=2026-09-30',
    )
  })

  it('INV_003_AC7 lists the top invoices to follow up with links', async () => {
    renderAt('/invoices/dashboard')

    const section = within(await screen.findByRole('region', { name: 'Top 5 to follow up' }))
    const item = section.getAllByRole('link')[0]!
    expect(item).toHaveTextContent('Deccan Printing Works')
    expect(item).toHaveTextContent('INV-2606 · 41 days overdue')
    expect(item).toHaveTextContent('₹1,25,000.00')
    expect(item).toHaveAttribute('href', '/invoices?q=INV-2606')
    expect(section.getByRole('link', { name: 'See all invoices needing follow-up' })).toHaveAttribute(
      'href',
      '/invoices?due_to=2026-09-30',
    )
  })

  it('INV_003_AC8 shows value by status as an accessible table', async () => {
    renderAt('/invoices/dashboard')

    const table = within(await screen.findByRole('table', { name: /by payment status/ }))
    const rows = table.getAllByRole('row').slice(1)
    expect(rows.map((row) => within(row).getByRole('rowheader').textContent)).toEqual([
      'Outstanding', 'At risk', 'Open', 'Paid',
    ])
    expect(rows[0]).toHaveTextContent('1 invoice')
    expect(rows[1]).toHaveTextContent('₹3,96,750.00')
    expect(rows[1]).toHaveTextContent('4 invoices')
    expect(rows[1]).toHaveTextContent('71%')
  })

  it('INV_003_AC9 with no uploads shows an empty state instead of zero cards', async () => {
    vi.mocked(api.getDashboard).mockResolvedValue({ today: '2026-09-25', has_data: false })
    renderAt('/invoices/dashboard')

    expect(await screen.findByText('No invoices yet')).toBeInTheDocument()
    expect(screen.queryByText('Total invoice value')).toBeNull()
  })

  it('PLT_001_AC5 Home shows the invoice headline numbers', async () => {
    renderAt('/')

    const invoices = within(screen.getByRole('region', { name: 'Invoices' }))
    expect(await invoices.findByRole('link', { name: /^Need follow-up: 9\./ })).toBeInTheDocument()
    expect(invoices.getByRole('link', { name: /^Total invoice value/ })).toBeInTheDocument()
  })
})
