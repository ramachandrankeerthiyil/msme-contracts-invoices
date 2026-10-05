import { QueryClientProvider } from '@tanstack/react-query'
import { act, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { createMemoryRouter, RouterProvider } from 'react-router'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { createQueryClient } from '@/app/queryClient'
import { routes } from '@/app/router'
import { ApiError } from '@/lib/api/client'
import * as sse from '@/lib/api/sse'

import { STORAGE_KEY } from '../conversation'
import { DISCLAIMER } from '../components/Composer'
import { SUGGESTIONS } from './AssistantPage'

vi.mock('@/lib/api/sse', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/lib/api/sse')>()
  return { ...actual, postEventStream: vi.fn() }
})

/** One in-flight answer the test drives by hand. */
interface Call {
  body: { messages: { role: string; content: string }[] }
  emit: (event: string, data: unknown) => void
  finish: () => void
  fail: (error: unknown) => void
  signal?: AbortSignal
}

let calls: Call[] = []

/** The nth request sent so far (fails the test if it wasn't sent). */
function call(index: number): Call {
  const found = calls[index]
  if (!found) throw new Error(`expected request #${index + 1} to have been sent`)
  return found
}

beforeEach(() => {
  calls = []
  sessionStorage.clear()
  vi.mocked(sse.postEventStream).mockImplementation(
    (_path, body, onEvent, signal) =>
      new Promise<void>((resolve, reject) => {
        signal?.addEventListener('abort', () => reject(new DOMException('Aborted', 'AbortError')))
        calls.push({
          body: body as Call['body'],
          emit: (event, data) => act(() => onEvent({ event, data })),
          finish: resolve,
          fail: reject,
          signal,
        })
      }),
  )
  Object.assign(navigator, { clipboard: { writeText: vi.fn().mockResolvedValue(undefined) } })
})

afterEach(() => {
  vi.clearAllMocks()
})

function renderPage() {
  const router = createMemoryRouter(routes, { initialEntries: ['/assistant'] })
  return render(
    <QueryClientProvider client={createQueryClient()}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  )
}

async function settle(call: Call) {
  await act(async () => {
    call.finish()
    await Promise.resolve()
  })
}

async function answer(call: Call, text: string) {
  call.emit('status', { id: 't1', state: 'running', label: 'Checking unpaid invoices' })
  call.emit('status', { id: 't1', state: 'done', label: 'Checked unpaid invoices', count: 2 })
  call.emit('text', { delta: text })
  call.emit('done', { stop_reason: 'end_turn' })
  await settle(call)
}

const box = () => screen.getByRole('textbox', { name: 'Ask a question about your contracts, invoices or this app' })

describe('AssistantPage', () => {
  it('AST-001 AC1: is in the navigation under Assistant', () => {
    renderPage()

    const [nav] = screen.getAllByRole('navigation', { name: 'Main' }) as [HTMLElement]
    const group = within(nav).getByRole('list', { name: 'Assistant' })
    expect(within(group).getByRole('link', { name: 'Talk to Me' })).toHaveAttribute('aria-current', 'page')
    expect(screen.getByRole('heading', { level: 1, name: 'Talk to Me' })).toBeInTheDocument()
  })

  it('AST-001 AC2, AC11: welcomes with suggestions and shows the disclaimer', () => {
    renderPage()

    const suggestions = within(screen.getByRole('list', { name: 'Suggested questions' })).getAllByRole('button')
    expect(suggestions.map((b) => b.textContent)).toEqual(SUGGESTIONS)
    expect(screen.getByText(DISCLAIMER)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /new conversation/i })).not.toBeInTheDocument()
  })

  it('AST-001 AC2, AC4, AC6, AC7, AC13: a suggestion is asked and the answer streams in', async () => {
    renderPage()

    await userEvent.click(screen.getByRole('button', { name: SUGGESTIONS[0] }))

    expect(call(0).body.messages).toEqual([{ role: 'user', content: SUGGESTIONS[0] }])
    const log = screen.getByRole('log', { name: 'Conversation' })
    expect(within(log).getByText(SUGGESTIONS[0])).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Stop' })).toBeInTheDocument()

    call(0).emit('status', { id: 't1', state: 'running', label: 'Checking unpaid invoices' })
    expect(screen.getByText('Checking unpaid invoices…')).toBeInTheDocument()

    await answer(
      call(0),
      'You have **2 unpaid invoices**. See [INV-2606](/invoices?view=all&q=INV-2606) and [a site](https://example.com).',
    )

    expect(screen.getByText('Checked unpaid invoices (2)')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'INV-2606' })).toHaveAttribute('href', '/invoices?view=all&q=INV-2606')
    expect(screen.queryByRole('link', { name: 'a site' })).not.toBeInTheDocument()
    expect(screen.getByText('a site')).toBeInTheDocument()
    expect(screen.getByRole('status')).toHaveTextContent('Answer ready. You have 2 unpaid invoices.')
    expect(box()).toHaveFocus()
    expect(screen.getByRole('button', { name: 'Send' })).toBeInTheDocument()
  })

  it('AST-002 AC14: the welcome, subtitle and question box say it covers the app too', () => {
    renderPage()

    expect(SUGGESTIONS).toContain('What is this app about?')
    expect(SUGGESTIONS).toContain('How does this app work?')
    const buttons = within(screen.getByRole('list', { name: 'Suggested questions' })).getAllByRole('button')
    expect(buttons.map((b) => b.textContent)).toEqual(expect.arrayContaining(['What is this app about?', 'How does this app work?']))
    expect(SUGGESTIONS.length).toBeGreaterThanOrEqual(4)
    expect(SUGGESTIONS.length).toBeLessThanOrEqual(8)
    expect(screen.getByText('Ask about your contracts and invoices, or how this app works.')).toBeInTheDocument()
    expect(screen.getByText(/and tell you about this\s+app\./)).toBeInTheDocument()
    expect(box()).toBeInTheDocument()
  })

  it('AST-002 AC14: asking the app questions sends them like any other question', async () => {
    renderPage()

    await userEvent.click(screen.getByRole('button', { name: 'What is this app about?' }))

    expect(call(0).body.messages).toEqual([{ role: 'user', content: 'What is this app about?' }])
  })

  it('AST-002 AC17: a declined reply is an ordinary answer: shown, copyable, announced, kept', async () => {
    renderPage()
    await userEvent.type(box(), 'Write me a poem{Enter}')
    const declined =
      "I can only help with your contracts and invoices, and with explaining how this app works, so I can't help with that.\n\n- To record a payment, see [Upload invoices](/invoices/upload)."

    call(0).emit('text', { delta: declined })
    call(0).emit('done', { stop_reason: 'declined' })
    await settle(call(0))

    const card = screen.getByRole('article', { name: "Talk to Me's answer" })
    expect(within(card).getByText(/I can only help with your contracts and invoices/)).toBeInTheDocument()
    expect(within(card).getByRole('link', { name: 'Upload invoices' })).toHaveAttribute('href', '/invoices/upload')
    expect(within(card).queryByText(/Checked|Checking/)).not.toBeInTheDocument() // nothing was looked up
    expect(screen.getByRole('status')).toHaveTextContent('Answer ready.')
    expect(box()).toHaveFocus()
    await userEvent.click(within(card).getByRole('button', { name: 'Copy answer' }))
    expect(navigator.clipboard.writeText).toHaveBeenCalledWith(declined)

    await userEvent.type(box(), 'Which invoices are unpaid?{Enter}')
    expect(call(1).body.messages.map((m) => m.role)).toEqual(['user', 'assistant', 'user'])
    expect(call(1).body.messages[1]?.content).toBe(declined)
  })

  it('AST-001 AC3: Enter sends, Shift+Enter adds a line, empty questions cannot be sent', async () => {
    renderPage()
    expect(screen.getByRole('button', { name: 'Send' })).toBeDisabled()

    await userEvent.type(box(), 'Line one{Shift>}{Enter}{/Shift}line two')
    expect(box()).toHaveValue('Line one\nline two')
    expect(calls).toHaveLength(0)

    await userEvent.type(box(), '{Enter}')
    expect(call(0).body.messages[0]?.content).toBe('Line one\nline two')
    expect(box()).toHaveValue('')
  })

  it('AST-001 AC3: shows a character count near the limit', async () => {
    renderPage()

    await userEvent.click(box())
    await userEvent.paste('x'.repeat(799))
    expect(screen.queryByText(/characters$/)).not.toBeInTheDocument()

    await userEvent.type(box(), 'x')
    expect(screen.getByText('800 / 1,000 characters')).toBeInTheDocument()
    expect(box()).toHaveAttribute('maxLength', '1000')
  })

  it('AST-001 AC4: Stop keeps what was written', async () => {
    renderPage()
    await userEvent.click(screen.getByRole('button', { name: SUGGESTIONS[1] }))
    call(0).emit('text', { delta: 'Kaveri Textiles owes' })

    await userEvent.click(screen.getByRole('button', { name: 'Stop' }))

    expect(call(0).signal?.aborted).toBe(true)
    expect(await screen.findByText('(stopped)')).toBeInTheDocument()
    expect(screen.getByText('Kaveri Textiles owes')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Send' })).toBeInTheDocument()
  })

  it('AST-001 AC8: follow-ups send the conversation so far', async () => {
    renderPage()
    await userEvent.click(screen.getByRole('button', { name: SUGGESTIONS[0] }))
    await answer(call(0), 'Two invoices.')

    await userEvent.type(box(), 'Which is the biggest?{Enter}')

    expect(call(1).body.messages).toEqual([
      { role: 'user', content: SUGGESTIONS[0] },
      { role: 'assistant', content: 'Two invoices.' },
      { role: 'user', content: 'Which is the biggest?' },
    ])
  })

  it('AST-001 AC8: the conversation survives a refresh and New conversation clears it', async () => {
    const first = renderPage()
    await userEvent.click(screen.getByRole('button', { name: SUGGESTIONS[0] }))
    await answer(call(0), 'Two invoices.')
    first.unmount()

    renderPage()
    expect(screen.getByText('Two invoices.')).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: 'New conversation' }))
    expect(screen.getByRole('heading', { name: 'How can I help today?' })).toBeInTheDocument()
    expect(sessionStorage.getItem(STORAGE_KEY)).toBeNull()
  })

  it('AST-001 AC12: a failure shows a reference and Try again asks the same question', async () => {
    renderPage()
    await userEvent.click(screen.getByRole('button', { name: SUGGESTIONS[2] }))
    call(0).emit('error', {
      code: 'ASSISTANT_FAILED',
      message: "Talk to Me couldn't answer that right now. Please try again in a moment.",
      request_id: 'req-12345678',
    })
    await settle(call(0))

    const alert = screen.getByRole('alert')
    expect(alert).toHaveTextContent("Talk to Me couldn't answer that right now")
    expect(alert).toHaveTextContent('Reference: req-12345678')

    await userEvent.click(within(alert).getByRole('button', { name: 'Try again' }))

    expect(call(1).body.messages).toEqual([{ role: 'user', content: SUGGESTIONS[2] }])
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('AST-001 AC12: an unavailable assistant is explained', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => {})
    renderPage()
    await userEvent.click(screen.getByRole('button', { name: SUGGESTIONS[3] }))

    await act(async () => {
      call(0).fail(new ApiError(503, 'SERVICE_UNAVAILABLE', "This part of the app isn't responding right now.", 'r-99999999'))
      await Promise.resolve()
    })

    expect(await screen.findByRole('alert')).toHaveTextContent('Not available right now')
  })

  it('AST-001 AC16: Copy copies the answer text', async () => {
    renderPage()
    await userEvent.click(screen.getByRole('button', { name: SUGGESTIONS[0] }))
    await answer(call(0), 'Two invoices.')

    await userEvent.click(screen.getByRole('button', { name: 'Copy answer' }))

    expect(navigator.clipboard.writeText).toHaveBeenCalledWith('Two invoices.')
    expect(screen.getByRole('button', { name: 'Copied answer' })).toBeInTheDocument()
  })
})
