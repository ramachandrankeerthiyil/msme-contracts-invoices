import { OctagonAlert, RotateCw } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { ApiError, GENERIC_ERROR_MESSAGE } from '@/lib/api/client'

interface ErrorAlertProps {
  error: unknown
  onRetry?: () => void
  retryLabel?: string
}

/**
 * Plain-language error banner (PLT-001 AC10, PLT-002 AC8). Unexpected failures add
 * "Reference: <request id>" so the user can report the problem.
 */
export function ErrorAlert({ error, onRetry, retryLabel = 'Try again' }: ErrorAlertProps) {
  const apiError = error instanceof ApiError ? error : undefined
  const title =
    apiError?.code === 'SERVICE_UNAVAILABLE' ? 'Not available right now' : 'Something went wrong'
  const message = apiError?.message ?? GENERIC_ERROR_MESSAGE
  const reference = apiError?.showsReference ? apiError.requestId : undefined

  return (
    <div role="alert" className="flex gap-4 rounded-lg border border-danger bg-danger-bg p-6">
      <OctagonAlert aria-hidden className="size-7 shrink-0 text-danger" />
      <div className="min-w-0">
        <p className="text-h3 text-danger">{title}</p>
        <p className="mt-1">{message}</p>
        {reference && (
          <p className="mt-2 text-small text-text-muted">
            Reference: <span className="font-mono break-all select-all">{reference}</span>
          </p>
        )}
        {onRetry && (
          <Button variant="secondary" className="mt-4" onClick={onRetry}>
            <RotateCw aria-hidden />
            {retryLabel}
          </Button>
        )}
      </div>
    </div>
  )
}
