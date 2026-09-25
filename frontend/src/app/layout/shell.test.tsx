import { QueryClientProvider } from '@tanstack/react-query'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { createMemoryRouter, RouterProvider } from 'react-router'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { EMPTY_PAGE } from '@/modules/invoices/testData'

import { createQueryClient } from '../queryClient'
import { routes } from '../router'

function renderAt(path: string) {
  const router = createMemoryRouter(routes, { initialEntries: [path] })
  render(
    <QueryClientProvider client={createQueryClient()}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  )
  return router
}

// Pages now load data; answer every API call as an empty system.
beforeEach(() => {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) => {
      const body = url.includes('/dashboard')
        ? { today: '2026-09-25', has_data: false }
        : url.includes('/uploads')
          ? { items: [], total: 0, page: 1, page_size: 5 }
          : EMPTY_PAGE
      return new Response(JSON.stringify(body), { headers: { 'Content-Type': 'application/json' } })
    }),
  )
})
afterEach(() => {
  vi.unstubAllGlobals()
})

function mainNav() {
  return screen.getByRole('navigation', { name: 'Main' })
}

describe('App shell', () => {
  it('PLT_001_AC2 shows Home plus the Contracts and Invoices groups with labelled items', () => {
    renderAt('/')

    const nav = within(mainNav())
    for (const label of [
      'Home',
      'Dashboard',
      'All contracts',
      'Upload contract',
      'All invoices',
      'Upload invoices',
    ]) {
      expect(nav.getAllByRole('link', { name: label }).length).toBeGreaterThan(0)
    }
    expect(nav.getByRole('list', { name: 'Contracts' })).toBeInTheDocument()
    expect(nav.getByRole('list', { name: 'Invoices' })).toBeInTheDocument()
  })

  it('PLT_001_AC3 highlights "All contracts" on a contract detail page', () => {
    renderAt('/contracts/3f1c-uuid')

    const current = within(mainNav()).getByRole('link', { current: 'page' })
    expect(current).toHaveTextContent('All contracts')
  })

  it('PLT_001_AC4 shows breadcrumb, h1, title and the primary action', () => {
    renderAt('/invoices/dashboard')

    const breadcrumb = within(screen.getByRole('navigation', { name: 'Breadcrumb' }))
    expect(breadcrumb.getByRole('link', { name: 'Invoices' })).toHaveAttribute('href', '/invoices/dashboard')
    expect(breadcrumb.getByText('Dashboard')).toHaveAttribute('aria-current', 'page')
    expect(screen.getByRole('heading', { level: 1, name: 'Invoice dashboard' })).toBeInTheDocument()
    expect(document.title).toBe('Invoice dashboard · MSME Contracts & Invoices')
    expect(within(screen.getByRole('main')).getByRole('link', { name: 'Upload invoices' })).toHaveAttribute(
      'href',
      '/invoices/upload',
    )
  })

  it('PLT_001_AC4 detail pages show the full breadcrumb trail', () => {
    renderAt('/contracts/abc')

    const breadcrumb = within(screen.getByRole('navigation', { name: 'Breadcrumb' }))
    expect(breadcrumb.getByRole('link', { name: 'Contracts' })).toBeInTheDocument()
    expect(breadcrumb.getByRole('link', { name: 'All contracts' })).toHaveAttribute('href', '/contracts')
    expect(breadcrumb.getByText('Contract details')).toBeInTheDocument()
  })

  it('PLT_001_AC5 Home shows both module sections with dashboard links and no breadcrumb', () => {
    renderAt('/')

    expect(screen.queryByRole('navigation', { name: 'Breadcrumb' })).toBeNull()
    const contracts = within(screen.getByRole('region', { name: 'Contracts' }))
    const invoices = within(screen.getByRole('region', { name: 'Invoices' }))
    expect(contracts.getByRole('link', { name: 'Go to contract dashboard' })).toHaveAttribute(
      'href',
      '/contracts/dashboard',
    )
    expect(invoices.getByRole('link', { name: 'Go to invoice dashboard' })).toHaveAttribute(
      'href',
      '/invoices/dashboard',
    )
  })

  it('PLT_001_AC8 moves focus to the new page heading after navigation', async () => {
    renderAt('/')

    await userEvent.click(within(mainNav()).getByRole('link', { name: 'All invoices' }))

    const heading = await screen.findByRole('heading', { level: 1, name: 'All invoices' })
    expect(heading).toHaveFocus()
  })

  it('PLT_001_AC8 has a skip link to the main content', () => {
    renderAt('/')

    expect(screen.getByRole('link', { name: 'Skip to content' })).toHaveAttribute('href', '#content')
    expect(screen.getByRole('main')).toHaveAttribute('id', 'content')
  })

  it('PLT_001_AC9 unknown URLs show Not found with links to Home and both dashboards', () => {
    renderAt('/no/such/page')

    expect(screen.getByRole('heading', { level: 1, name: 'Page not found' })).toBeInTheDocument()
    const main = within(screen.getByRole('main'))
    expect(main.getByRole('link', { name: 'Home' })).toHaveAttribute('href', '/')
    expect(main.getByRole('link', { name: 'Contract dashboard' })).toHaveAttribute('href', '/contracts/dashboard')
    expect(main.getByRole('link', { name: 'Invoice dashboard' })).toHaveAttribute('href', '/invoices/dashboard')
  })
})
