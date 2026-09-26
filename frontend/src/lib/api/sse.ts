// Streamed POST requests answered with Server-Sent Events (AST-001 design "API").
// EventSource can only GET, so the stream is read from fetch() and parsed here.

import { ApiError, SERVICE_UNAVAILABLE_MESSAGE, logFailure, toApiError } from './client'

export interface SseEvent {
  event: string
  data: unknown
}

/** Splits an SSE byte stream into events. Keeps partial events across chunks. */
export class SseParser {
  private buffer = ''

  push(chunk: string): SseEvent[] {
    this.buffer += chunk.replace(/\r\n/g, '\n')
    const events: SseEvent[] = []
    let end = this.buffer.indexOf('\n\n')
    while (end !== -1) {
      const block = this.buffer.slice(0, end)
      this.buffer = this.buffer.slice(end + 2)
      const parsed = parseBlock(block)
      if (parsed) events.push(parsed)
      end = this.buffer.indexOf('\n\n')
    }
    return events
  }
}

function parseBlock(block: string): SseEvent | undefined {
  let event = 'message'
  const data: string[] = []
  for (const line of block.split('\n')) {
    if (line.startsWith(':')) continue // comment / keep-alive
    const colon = line.indexOf(':')
    const field = colon === -1 ? line : line.slice(0, colon)
    const value = colon === -1 ? '' : line.slice(colon + 1).replace(/^ /, '')
    if (field === 'event') event = value
    else if (field === 'data') data.push(value)
  }
  if (data.length === 0) return undefined
  try {
    return { event, data: JSON.parse(data.join('\n')) }
  } catch {
    return undefined
  }
}

/**
 * POSTs `body` as JSON and calls `onEvent` for each event until the stream ends.
 * Aborting `signal` stops reading (and closes the connection) and rejects with an AbortError.
 * HTTP errors before the stream starts reject with an ApiError, like apiFetch.
 */
export async function postEventStream(
  path: string,
  body: unknown,
  onEvent: (event: SseEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  const url = path.startsWith('/api/') ? path : `/api${path}`
  let response: Response
  try {
    response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream' },
      body: JSON.stringify(body),
      signal,
    })
  } catch (error) {
    if (signal?.aborted) throw error
    const apiError = new ApiError(0, 'SERVICE_UNAVAILABLE', SERVICE_UNAVAILABLE_MESSAGE)
    logFailure('POST', url, apiError)
    throw apiError
  }
  if (!response.ok || !response.body) {
    const apiError = await toApiError(response)
    logFailure('POST', url, apiError)
    throw apiError
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  const parser = new SseParser()
  try {
    for (;;) {
      const { done, value } = await reader.read()
      if (done) break
      for (const event of parser.push(decoder.decode(value, { stream: true }))) onEvent(event)
    }
  } catch (error) {
    if (signal?.aborted) throw error
    // The connection dropped mid-answer.
    const apiError = new ApiError(0, 'SERVICE_UNAVAILABLE', SERVICE_UNAVAILABLE_MESSAGE)
    logFailure('POST', url, apiError)
    throw apiError
  } finally {
    reader.releaseLock()
  }
}
