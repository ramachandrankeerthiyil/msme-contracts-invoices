import { afterEach, describe, expect, it, vi } from 'vitest'

import { ApiError } from './client'
import { SseParser, postEventStream, type SseEvent } from './sse'

function streamOf(chunks: string[]): ReadableStream<Uint8Array> {
  const encoder = new TextEncoder()
  return new ReadableStream({
    start(controller) {
      for (const chunk of chunks) controller.enqueue(encoder.encode(chunk))
      controller.close()
    },
  })
}

afterEach(() => {
  vi.restoreAllMocks()
})

describe('SseParser', () => {
  it('parses events split across chunks', () => {
    const parser = new SseParser()

    expect(parser.push('event: text\ndata: {"del')).toEqual([])
    expect(parser.push('ta": "Hi"}\n\nevent: done\r\ndata: {}\r\n\r\n: keep-alive\n\n')).toEqual([
      { event: 'text', data: { delta: 'Hi' } },
      { event: 'done', data: {} },
    ])
  })

  it('skips blocks that are not valid JSON', () => {
    expect(new SseParser().push('event: text\ndata: nope\n\n')).toEqual([])
  })
})

describe('postEventStream', () => {
  it('POSTs JSON and delivers each event', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(streamOf(['event: text\ndata: {"delta":"₹4,25,000"}\n\n', 'event: done\ndata: {}\n\n']), {
        headers: { 'Content-Type': 'text/event-stream' },
      }),
    )
    const events: SseEvent[] = []

    await postEventStream('/assistant/chat', { messages: [] }, (e) => events.push(e))

    expect(fetchMock).toHaveBeenCalledWith(
      '/api/assistant/chat',
      expect.objectContaining({ method: 'POST', body: '{"messages":[]}' }),
    )
    expect(events).toEqual([
      { event: 'text', data: { delta: '₹4,25,000' } },
      { event: 'done', data: {} },
    ])
  })

  it('turns an error response into an ApiError', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => {})
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ error: { code: 'VALIDATION_ERROR', message: 'Too long.', request_id: 'r-12345678' } }), {
        status: 422,
      }),
    )

    const error = await postEventStream('/assistant/chat', {}, () => {}).catch((e: unknown) => e)

    expect(error).toBeInstanceOf(ApiError)
    expect((error as ApiError).code).toBe('VALIDATION_ERROR')
  })

  it('reports an unreachable service as unavailable', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => {})
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(new TypeError('Failed to fetch'))

    const error = await postEventStream('/assistant/chat', {}, () => {}).catch((e: unknown) => e)

    expect((error as ApiError).code).toBe('SERVICE_UNAVAILABLE')
  })
})
