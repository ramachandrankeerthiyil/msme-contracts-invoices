// API client (PLT-001 AC10, PLT-002 AC8/AC11). Every failure becomes an ApiError carrying the
// user-friendly message from the standard error body and the request ID for support.

export const SERVICE_UNAVAILABLE_MESSAGE =
  "This part of the app isn't responding right now. Please try again in a minute."
export const GENERIC_ERROR_MESSAGE = 'Something went wrong. Please try again.'

const UNAVAILABLE_STATUSES = new Set([502, 503, 504])
const REFERENCE_CODES = new Set(['INTERNAL_ERROR', 'SERVICE_UNAVAILABLE'])

export class ApiError extends Error {
  readonly status: number
  readonly code: string
  readonly requestId?: string
  readonly details: Record<string, unknown>

  constructor(
    status: number,
    code: string,
    message: string,
    requestId?: string,
    details: Record<string, unknown> = {},
  ) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.requestId = requestId
    this.details = details
  }

  /** Unexpected failures show "Reference: <request id>" so users can report them. */
  get showsReference(): boolean {
    return REFERENCE_CODES.has(this.code)
  }
}

interface ErrorBody {
  error?: {
    code?: string
    message?: string
    details?: Record<string, unknown>
    request_id?: string
  }
}

function logFailure(method: string, path: string, error: ApiError): void {
  console.error('[api]', {
    method,
    path,
    status: error.status,
    code: error.code,
    requestId: error.requestId,
  })
}

async function readErrorBody(response: Response): Promise<ErrorBody['error']> {
  try {
    return ((await response.json()) as ErrorBody).error
  } catch {
    return undefined
  }
}

export async function toApiError(response: Response): Promise<ApiError> {
  const body = await readErrorBody(response)
  const requestId = body?.request_id ?? response.headers.get('X-Request-ID') ?? undefined

  if (UNAVAILABLE_STATUSES.has(response.status)) {
    return new ApiError(response.status, 'SERVICE_UNAVAILABLE', SERVICE_UNAVAILABLE_MESSAGE, requestId)
  }
  return new ApiError(
    response.status,
    body?.code ?? 'HTTP_ERROR',
    body?.message ?? GENERIC_ERROR_MESSAGE,
    requestId,
    body?.details ?? {},
  )
}

/** `apiFetch('/invoices/dashboard')` → GET /api/invoices/dashboard, parsed as JSON. */
export async function apiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const url = path.startsWith('/api/') ? path : `/api${path}`
  const method = (init.method ?? 'GET').toUpperCase()
  const headers = new Headers(init.headers)
  if (!headers.has('Accept')) headers.set('Accept', 'application/json')

  let response: Response
  try {
    response = await fetch(url, { ...init, headers })
  } catch {
    const error = new ApiError(0, 'SERVICE_UNAVAILABLE', SERVICE_UNAVAILABLE_MESSAGE)
    logFailure(method, url, error)
    throw error
  }

  if (!response.ok) {
    const error = await toApiError(response)
    logFailure(method, url, error)
    throw error
  }
  if (response.status === 204) return undefined as T
  return (await response.json()) as T
}
