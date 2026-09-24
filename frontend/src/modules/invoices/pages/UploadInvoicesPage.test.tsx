import { QueryClientProvider } from '@tanstack/react-query'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { createMemoryRouter, RouterProvider } from 'react-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { createQueryClient } from '@/app/queryClient'
import { routes } from '@/app/router'
import { ApiError } from '@/lib/api/client'

import * as api from '../api'
import type { UploadSummary } from '../api'

vi.mock('../api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api')>()
  return { ...actual, uploadInvoices: vi.fn(), listUploads: vi.fn() }
})

const summary: UploadSummary = {
  id: 'u1',
  file_name: 'september.xlsx',
  uploaded_at: '2026-09-24T05:12:00Z',
  status: 'completed',
  rows_total: 8,
  rows_created: 2,
  rows_updated: 0,
  rows_overwritten: 1,
  rows_rejected: 5,
  rejections: [
    { row: 3, invoice_number: 'INV-2702', reason: 'Customer Name is missing.' },
    { row: 6, invoice_number: 'INV-2705', reason: "Date Raised '31/13/2026' is not a valid date." },
  ],
  overwrites: [{ row: 8, replaced_row: 2, invoice_number: 'INV-2701' }],
}

function renderPage() {
  const router = createMemoryRouter(routes, { initialEntries: ['/invoices/upload'] })
  render(
    <QueryClientProvider client={createQueryClient()}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  )
  return router
}

async function chooseFile() {
  await userEvent.upload(screen.getByTestId('file-input'), new File(['x'], 'september.xlsx'))
}

describe('UploadInvoicesPage', () => {
  beforeEach(() => {
    vi.mocked(api.listUploads).mockResolvedValue({ items: [], total: 0, page: 1, page_size: 5 })
    vi.mocked(api.uploadInvoices).mockReset()
  })

  it('INV_001_AC1 lists the required columns and links the template', async () => {
    renderPage()

    const columns = within(screen.getByRole('list', { name: 'Required columns' }))
    expect(columns.getAllByRole('listitem')).toHaveLength(6)
    expect(screen.getByRole('link', { name: 'Download template' })).toHaveAttribute(
      'href',
      '/api/invoices/template',
    )
    expect(await screen.findByText('No uploads yet. Your uploads will be listed here.')).toBeInTheDocument()
  })

  it('INV_001_AC9 uploads the chosen file and shows the summary', async () => {
    vi.mocked(api.uploadInvoices).mockResolvedValue(summary)
    renderPage()

    await chooseFile()
    expect(screen.getByText('september.xlsx')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Upload invoices' }))

    const heading = await screen.findByRole('heading', { name: 'Upload complete' })
    expect(heading).toHaveFocus()
    expect(
      screen.getByText('8 rows read · 2 new · 1 replaced by a later row · 5 need fixing'),
    ).toBeInTheDocument()
    const table = within(screen.getByRole('table', { name: 'Rows that need fixing' }))
    expect(table.getByText('Customer Name is missing.')).toBeInTheDocument()
    expect(screen.getByText('Row 8 replaced row 2 (INV-2701)')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'View invoices' })).toHaveAttribute('href', '/invoices')

    await userEvent.click(screen.getByRole('button', { name: 'Upload another file' }))
    expect(screen.getByRole('button', { name: 'Choose file' })).toBeInTheDocument()
  })

  it('INV_001_AC3 shows file-level errors and keeps the file selected for retry', async () => {
    vi.mocked(api.uploadInvoices).mockRejectedValue(
      new ApiError(422, 'MISSING_COLUMNS', 'Your file is missing these columns: Due Date.', 'r-12345678', {
        missing: ['Due Date'],
      }),
    )
    renderPage()

    await chooseFile()
    await userEvent.click(screen.getByRole('button', { name: 'Upload invoices' }))

    const alert = await screen.findByRole('alert')
    expect(alert).toHaveTextContent("We couldn't use this file")
    expect(alert).toHaveTextContent('Your file is missing these columns: Due Date.')
    expect(screen.getByRole('button', { name: 'Upload invoices' })).toBeInTheDocument()
  })

  it('shows "No invoices were saved" when every row was rejected', async () => {
    vi.mocked(api.uploadInvoices).mockResolvedValue({
      ...summary,
      status: 'no_valid_rows',
      rows_total: 1,
      rows_created: 0,
      rows_overwritten: 0,
      rows_rejected: 1,
      rejections: [{ row: 2, invoice_number: 'X', reason: 'Amount must be greater than zero.' }],
      overwrites: [],
    })
    renderPage()

    await chooseFile()
    await userEvent.click(screen.getByRole('button', { name: 'Upload invoices' }))

    expect(await screen.findByRole('heading', { name: 'No invoices were saved' })).toBeInTheDocument()
    expect(screen.getByText('1 row read · 1 needs fixing')).toBeInTheDocument()
  })
})
