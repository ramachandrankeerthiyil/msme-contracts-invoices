import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ApiError, apiFetch, SERVICE_UNAVAILABLE_MESSAGE } from './client'

function jsonResponse(status: number, body: unknown, requestId = 'req-12345678'): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json', 'X-Request-ID': requestId },
  })
}

describe('apiFetch', () => {
  const fetchMock = vi.fn<typeof fetch>()
  const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {})

  beforeEach(() => {
    vi.stubGlobal('fetch', fetchMock)
    fetchMock.mockReset()
    consoleError.mockClear()
  })
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('prefixes /api and returns parsed JSON', async () => {
    fetchMock.mockResolvedValue(jsonResponse(200, { ok: true }))

    await expect(apiFetch('/invoices/dashboard')).resolves.toEqual({ ok: true })
    expect(fetchMock.mock.calls[0]?.[0]).toBe('/api/invoices/dashboard')
  })

  it('PLT_002_AC8 turns the standard error body into an ApiError with the request ID', async () => {
    fetchMock.mockResolvedValue(
      jsonResponse(500, {
        error: {
          code: 'INTERNAL_ERROR',
          message: 'Something went wrong on our side. Please try again.',
          details: {},
          request_id: 'boom-request-1',
        },
      }),
    )

    const error = await apiFetch('/invoices/x').catch((e: unknown) => e)

    expect(error).toBeInstanceOf(ApiError)
    expect(error).toMatchObject({
      status: 500,
      code: 'INTERNAL_ERROR',
      requestId: 'boom-request-1',
      showsReference: true,
    })
  })

  it('keeps business error codes and messages as sent', async () => {
    fetchMock.mockResolvedValue(
      jsonResponse(422, {
        error: { code: 'MISSING_COLUMNS', message: 'Your file is missing…', details: { missing: ['Due Date'] } },
      }),
    )

    const error = (await apiFetch('/invoices/uploads').catch((e: unknown) => e)) as ApiError

    expect(error.code).toBe('MISSING_COLUMNS')
    expect(error.message).toBe('Your file is missing…')
    expect(error.details).toEqual({ missing: ['Due Date'] })
    expect(error.showsReference).toBe(false)
  })

  it.each([502, 503, 504])('PLT_001_AC10 maps %i to SERVICE_UNAVAILABLE', async (status) => {
    fetchMock.mockResolvedValue(new Response('<html>bad gateway</html>', { status }))

    const error = (await apiFetch('/invoices/x').catch((e: unknown) => e)) as ApiError

    expect(error.code).toBe('SERVICE_UNAVAILABLE')
    expect(error.message).toBe(SERVICE_UNAVAILABLE_MESSAGE)
  })

  it('PLT_001_AC10 maps network failures to SERVICE_UNAVAILABLE', async () => {
    fetchMock.mockRejectedValue(new TypeError('Failed to fetch'))

    const error = (await apiFetch('/invoices/x').catch((e: unknown) => e)) as ApiError

    expect(error.code).toBe('SERVICE_UNAVAILABLE')
    expect(error.status).toBe(0)
  })

  it('PLT_002_AC11 logs failures to the console with the request ID', async () => {
    fetchMock.mockResolvedValue(
      jsonResponse(404, { error: { code: 'NOT_FOUND', message: 'nope', request_id: 'abc-12345' } }),
    )

    await apiFetch('/invoices/x').catch(() => undefined)

    expect(consoleError).toHaveBeenCalledWith('[api]', {
      method: 'GET',
      path: '/api/invoices/x',
      status: 404,
      code: 'NOT_FOUND',
      requestId: 'abc-12345',
    })
  })
})
