import type { UseQueryResult } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Inbox } from 'lucide-react'
import { MemoryRouter } from 'react-router'
import { describe, expect, it, vi } from 'vitest'

import { ApiError, SERVICE_UNAVAILABLE_MESSAGE } from '@/lib/api/client'

import { EmptyState } from './EmptyState'
import { ErrorAlert } from './ErrorAlert'
import { KpiCard } from './KpiCard'
import { QueryBoundary } from './QueryBoundary'
import { StatusBadge, type StatusVariant } from './StatusBadge'

describe('StatusBadge', () => {
  it.each<StatusVariant>(['success', 'warning', 'danger', 'info', 'neutral'])(
    'always shows an icon and a text label (%s)',
    (variant) => {
      const { container } = render(<StatusBadge variant={variant} label="Label text" />)

      expect(screen.getByText('Label text')).toBeInTheDocument()
      expect(container.querySelector(`[data-status-icon="${variant}"]`)).not.toBeNull()
    },
  )
})

describe('KpiCard', () => {
  it('is a single link to the filtered list with a descriptive accessible name', () => {
    render(
      <MemoryRouter>
        <KpiCard label="At risk" value="4" hint="2 expiring soon" variant="warning" to="/contracts?at_risk=true" />
      </MemoryRouter>,
    )

    const link = screen.getByRole('link', { name: 'At risk: 4. 2 expiring soon' })
    expect(link).toHaveAttribute('href', '/contracts?at_risk=true')
  })
})

describe('EmptyState', () => {
  it('shows title, description and action', () => {
    render(<EmptyState icon={Inbox} title="No invoices yet" description="Upload a file." action={<button>Upload</button>} />)

    expect(screen.getByText('No invoices yet')).toBeInTheDocument()
    expect(screen.getByText('Upload a file.')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Upload' })).toBeInTheDocument()
  })
})

describe('ErrorAlert', () => {
  it('PLT_002_AC8 shows a reference number for unexpected errors', () => {
    const error = new ApiError(500, 'INTERNAL_ERROR', 'Something went wrong on our side.', 'boom-request-1')
    render(<ErrorAlert error={error} />)

    expect(screen.getByRole('alert')).toHaveTextContent('Something went wrong')
    expect(screen.getByText('boom-request-1')).toBeInTheDocument()
  })

  it('shows business messages without a reference', () => {
    const error = new ApiError(422, 'MISSING_COLUMNS', 'Your file is missing Due Date.', 'req-12345678')
    render(<ErrorAlert error={error} />)

    expect(screen.getByRole('alert')).toHaveTextContent('Your file is missing Due Date.')
    expect(screen.queryByText(/Reference/)).toBeNull()
  })

  it('handles non-API errors with a generic message', () => {
    render(<ErrorAlert error={new TypeError('x is undefined')} />)

    expect(screen.getByRole('alert')).toHaveTextContent('Something went wrong. Please try again.')
    expect(screen.queryByText(/x is undefined/)).toBeNull()
  })
})

describe('QueryBoundary', () => {
  function query<T>(state: Partial<UseQueryResult<T>>): UseQueryResult<T> {
    return state as UseQueryResult<T>
  }

  it('shows a loading state', () => {
    render(<QueryBoundary query={query({ isPending: true })}>{() => 'data'}</QueryBoundary>)

    expect(screen.getByText('Loading…')).toBeInTheDocument()
  })

  it('PLT_001_AC10 shows a friendly alert with reference and retries on request', async () => {
    const refetch = vi.fn()
    const error = new ApiError(503, 'SERVICE_UNAVAILABLE', SERVICE_UNAVAILABLE_MESSAGE, 'gw-request-99')
    render(
      <QueryBoundary query={query({ isPending: false, isError: true, error, refetch } as never)}>
        {() => 'data'}
      </QueryBoundary>,
    )

    expect(screen.getByRole('alert')).toHaveTextContent('Not available right now')
    expect(screen.getByRole('alert')).toHaveTextContent(SERVICE_UNAVAILABLE_MESSAGE)
    expect(screen.getByText('gw-request-99')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Try again' }))
    expect(refetch).toHaveBeenCalledOnce()
  })

  it('renders children with data', () => {
    render(
      <QueryBoundary query={query({ isPending: false, isError: false, data: 42 })}>
        {(value) => `value is ${value}`}
      </QueryBoundary>,
    )

    expect(screen.getByText('value is 42')).toBeInTheDocument()
  })
})
