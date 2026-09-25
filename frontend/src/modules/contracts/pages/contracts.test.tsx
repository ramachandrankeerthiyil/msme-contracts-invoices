import { QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { createMemoryRouter, RouterProvider } from 'react-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { createQueryClient } from '@/app/queryClient'
import { routes } from '@/app/router'
import { ApiError } from '@/lib/api/client'

import * as api from '../api'
import { listUrl, parseContractQuery, toUrlParams } from '../query'
import { CONTRACT_DASHBOARD, CONTRACT_PAGE, contractDetail, EMPTY_CONTRACTS } from '../testData'

vi.mock('../api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api')>()
  return {
    ...actual,
    listContracts: vi.fn(),
    getContract: vi.fn(),
    getDashboard: vi.fn(),
    uploadContract: vi.fn(),
    retryContract: vi.fn(),
  }
})

function renderAt(path: string) {
  const router = createMemoryRouter(routes, { initialEntries: [path] })
  render(
    <QueryClientProvider client={createQueryClient()}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  )
  return router
}

const search = (router: ReturnType<typeof renderAt>) => new URLSearchParams(router.state.location.search)

beforeEach(() => {
  vi.mocked(api.listContracts).mockReset().mockResolvedValue(CONTRACT_PAGE)
  vi.mocked(api.getContract).mockReset().mockResolvedValue(contractDetail())
  vi.mocked(api.getDashboard).mockReset().mockResolvedValue(CONTRACT_DASHBOARD)
  vi.mocked(api.uploadContract).mockReset()
  vi.mocked(api.retryContract).mockReset()
})

describe('contract list URL state', () => {
  it('round-trips and drops defaults', () => {
    const query = parseContractQuery(new URLSearchParams('view=at_risk&q=blue&sort=title&order=desc&page=2'))
    expect(toUrlParams(query).toString()).toBe('view=at_risk&q=blue&sort=title&order=desc&page=2')
    expect(listUrl({ view: 'all' })).toBe('/contracts')
    expect(listUrl({ view: 'expired' })).toBe('/contracts?view=expired')
  })
})

describe('ContractsPage', () => {
  it('CON_002_AC1 lists contracts with parties, end hints, statuses and high risks', async () => {
    renderAt('/contracts')

    const table = await screen.findByRole('table', { name: 'Contracts' })
    const rows = within(table).getAllByRole('row')
    expect(within(rows[0]!).getAllByRole('columnheader').map((th) => th.textContent)).toEqual([
      'Contract', 'Start', 'End', 'Status', 'High risks', 'Uploaded',
    ])
    const msa = within(rows[1]!)
    expect(msa.getByRole('link', { name: 'Master Services Agreement' })).toHaveAttribute('href', '/contracts/c-msa')
    expect(msa.getByText('Kaveri Agro Foods Private Limited · Bluewave Logistics LLP')).toBeInTheDocument()
    expect(msa.getByText('in 2 days')).toBeInTheDocument()
    expect(msa.getByText('In force')).toBeInTheDocument()
    expect(msa.getByText('At risk')).toBeInTheDocument()
    expect(msa.getByText('Expires in 2 days · 4 high risks')).toBeInTheDocument()
  })

  it('CON_002_AC2 tabs, search and the being-read note', async () => {
    const router = renderAt('/contracts')

    expect(await screen.findByText(/1 contract is still/)).toBeInTheDocument()
    await userEvent.click(screen.getByRole('link', { name: /^At risk/ }))
    expect(search(router).get('view')).toBe('at_risk')

    await userEvent.type(screen.getByLabelText('Search contract title or party'), 'bluewave')
    await waitFor(() => expect(search(router).get('q')).toBe('bluewave'))
  })

  it('CON_002_AC3 sorting updates the URL', async () => {
    const router = renderAt('/contracts')
    const table = await screen.findByRole('table', { name: 'Contracts' })

    await userEvent.click(within(table).getByRole('button', { name: 'High risks' }))
    expect(search(router).get('sort')).toBe('high_risks')
  })

  it('CON_002_AC9 shows an empty state with Upload contract', async () => {
    vi.mocked(api.listContracts).mockResolvedValue(EMPTY_CONTRACTS)
    renderAt('/contracts')

    expect(await screen.findByText('No contracts yet')).toBeInTheDocument()
  })
})

describe('ContractDetailPage', () => {
  it('CON_002_AC5_AC7 shows every section, quotes, AI notice and download', async () => {
    renderAt('/contracts/c-msa')

    expect(await screen.findByRole('heading', { level: 1, name: 'Master Services Agreement' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Download original' })).toHaveAttribute('href', '/api/contracts/c-msa/file')
    expect(screen.getByText('Extracted by AI')).toBeInTheDocument()
    expect(screen.getByText('At risk: Expires in 2 days · 1 high risk')).toBeInTheDocument()

    const risks = within(screen.getByRole('region', { name: 'Risks' }))
    expect(risks.getAllByRole('heading', { level: 3 }).map((h) => h.textContent)).toEqual([
      'High risks', 'Medium risks',
    ])
    expect(risks.getByText('“without limit”')).toBeInTheDocument()

    const dates = within(screen.getByRole('region', { name: 'Key dates' }))
    expect(dates.getByText('in 2 days')).toBeInTheDocument()
    expect(dates.getByText('358 days ago')).toBeInTheDocument()

    const terms = within(screen.getByRole('region', { name: 'Terms' }))
    expect(terms.getByRole('heading', { name: 'Payment' })).toBeInTheDocument()
    expect(terms.getByText(/couldn't find this exact wording/)).toBeInTheDocument()
    expect(screen.getByText(/read by claude-sonnet-5/)).toBeInTheDocument()
  })

  it('CON_001_AC8 shows progress while reading, then the result', async () => {
    vi.mocked(api.getContract)
      .mockResolvedValueOnce(contractDetail({ processing_status: 'analysing', title: 'contract.docx' }))
      .mockResolvedValue(contractDetail())
    renderAt('/contracts/c-msa')

    expect(await screen.findByRole('heading', { name: 'Reading your contract…' })).toBeInTheDocument()
    expect(screen.getByText('Finding parties, dates, terms and risks')).toBeInTheDocument()

    const heading = await screen.findByRole('heading', { level: 1, name: 'Master Services Agreement' }, { timeout: 4000 })
    await waitFor(() => expect(heading).toHaveFocus())
    expect(screen.queryByText('Reading your contract…')).toBeNull()
  })

  it('CON_001_AC9 a failed contract offers Try again', async () => {
    vi.mocked(api.getContract).mockResolvedValue(
      contractDetail({ processing_status: 'failed', lifecycle: 'failed', error_message: 'This file looks like a scanned image.' }),
    )
    vi.mocked(api.retryContract).mockResolvedValue({ id: 'c-msa', processing_status: 'uploaded' })
    renderAt('/contracts/c-msa')

    expect(await screen.findByText('This file looks like a scanned image.')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Try again' }))
    expect(api.retryContract).toHaveBeenCalledWith('c-msa')
  })

  it('shows a friendly message for an unknown contract', async () => {
    vi.mocked(api.getContract).mockRejectedValue(new ApiError(404, 'NOT_FOUND', "We couldn't find that contract."))
    renderAt('/contracts/nope')

    expect(await screen.findByText("We couldn't find that contract")).toBeInTheDocument()
  })
})

describe('UploadContractPage', () => {
  async function chooseFile() {
    await userEvent.upload(screen.getByTestId('file-input'), new File(['x'], 'msa.docx'))
    await userEvent.click(screen.getByRole('button', { name: 'Upload contract' }))
  }

  it('CON_001_AC1_AC8 uploads and opens the contract page', async () => {
    vi.mocked(api.uploadContract).mockResolvedValue({ id: 'c-new', processing_status: 'uploaded' })
    const router = renderAt('/contracts/upload')

    expect(screen.getByText('PDF or Word (.docx), up to 20 MB')).toBeInTheDocument()
    await chooseFile()

    await waitFor(() => expect(router.state.location.pathname).toBe('/contracts/c-new'))
  })

  it('CON_001_AC3a a duplicate links to the existing contract', async () => {
    vi.mocked(api.uploadContract).mockRejectedValue(
      new ApiError(409, 'DUPLICATE_CONTRACT', 'This contract was already uploaded on 24 Sep 2026.', 'r-1', {
        contract_id: 'c-msa',
      }),
    )
    renderAt('/contracts/upload')
    await chooseFile()

    expect(await screen.findByText('This contract was already uploaded on 24 Sep 2026.')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Open the existing contract' })).toHaveAttribute('href', '/contracts/c-msa')
  })
})

describe('ContractDashboardPage', () => {
  it('CON_003_AC1_AC3_AC8 cards, needs-review group, links and "figures as of"', async () => {
    renderAt('/contracts/dashboard')

    expect(await screen.findByText('25 Sep 2026')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Total contracts: 2. read so far' })).toHaveAttribute('href', '/contracts')
    expect(
      screen.getByRole('link', { name: 'At risk: 1. 1 expiring soon · 1 with high risks' }),
    ).toHaveAttribute('href', '/contracts?view=at_risk')
    const review = within(screen.getByRole('region', { name: 'Needs review' }))
    expect(review.getByRole('link', { name: /^No end date: 0\./ })).toHaveAttribute('href', '/contracts?view=no_end_date')
  })

  it('CON_003_AC4_AC5_AC6 needs attention, status bars and unread note', async () => {
    renderAt('/contracts/dashboard')

    const attention = within(await screen.findByRole('region', { name: 'Needs attention' }))
    expect(attention.getByRole('link', { name: /Master Services Agreement/ })).toHaveAttribute('href', '/contracts/c-msa')
    const bars = within(screen.getByRole('table', { name: 'Number of read contracts in each status' }))
    expect(bars.getAllByRole('rowheader').map((th) => th.textContent)).toEqual([
      'In force', 'Not yet started', 'No end date', 'Expired',
    ])
    expect(screen.getByRole('link', { name: '1 contract is still being read' })).toHaveAttribute('href', '/contracts?view=processing')
    expect(screen.getByRole('link', { name: '1 contract could not be read' })).toHaveAttribute('href', '/contracts?view=failed')
  })

  it('CON_003_AC7 empty state when there are no contracts', async () => {
    vi.mocked(api.getDashboard).mockResolvedValue({ today: '2026-09-25', has_data: false })
    renderAt('/contracts/dashboard')

    expect(await screen.findByText('No contracts yet')).toBeInTheDocument()
    expect(screen.queryByText('Total contracts')).toBeNull()
  })

  it('PLT_001_AC5 Home shows the contract headline numbers', async () => {
    renderAt('/')

    const contracts = within(screen.getByRole('region', { name: 'Contracts' }))
    expect(await contracts.findByRole('link', { name: /^In force: 2\./ })).toBeInTheDocument()
    expect(contracts.getByRole('link', { name: /^At risk: 1\./ })).toBeInTheDocument()
    expect(contracts.queryByRole('link', { name: /^Total contracts/ })).toBeNull()
  })
})
