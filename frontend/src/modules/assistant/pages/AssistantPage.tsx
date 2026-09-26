import { MessageCircleQuestion, RotateCcw, Sparkles } from 'lucide-react'
import { useEffect, useLayoutEffect, useRef, useState } from 'react'

import { PageHeader } from '@/app/layout/PageHeader'
import { Button } from '@/components/ui/button'

import { AnswerCard, QuestionBubble } from '../components/AnswerCard'
import { Composer } from '../components/Composer'
import { announcement } from '../conversation'
import { useConversation } from '../useConversation'

export const SUGGESTIONS = [
  'Which invoices are unpaid as of today?',
  'Who owes me the most?',
  'What is due this week?',
  'What risks are in my contracts?',
  'Which contracts end this month?',
  'Which contracts need my attention?',
] as const

const NEAR_BOTTOM_PX = 160

function nearBottom(): boolean {
  const { scrollY, innerHeight } = window
  return scrollY + innerHeight >= document.documentElement.scrollHeight - NEAR_BOTTOM_PX
}

/** "Talk to Me": ask questions about contracts and invoices in plain English (AST-001). */
export function AssistantPage() {
  const { turns, isAnswering, finishedTurnId, ask, stop, retry, reset } = useConversation()
  const input = useRef<HTMLTextAreaElement>(null)
  const end = useRef<HTMLDivElement>(null)
  const [announced, setAnnounced] = useState('')
  const followNewest = useRef(true)

  // Follow the answer as it grows, but only while the reader is already at the bottom.
  useLayoutEffect(() => {
    if (followNewest.current) end.current?.scrollIntoView?.({ block: 'end' })
  }, [turns])

  useEffect(() => {
    const onScroll = () => {
      followNewest.current = nearBottom()
    }
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  // Announce the finished answer once, then put the cursor back in the question box (AC13).
  useEffect(() => {
    if (!finishedTurnId) return
    const turn = turns.find((t) => t.id === finishedTurnId)
    if (!turn) return
    if (turn.status === 'done') setAnnounced(announcement(turn.answer))
    else if (turn.status === 'error') setAnnounced("Talk to Me couldn't answer that.")
    else setAnnounced('Answer stopped.')
    input.current?.focus()
    // Only when a new answer finishes, not on every streamed word.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [finishedTurnId])

  function send(question: string) {
    followNewest.current = true
    setAnnounced('')
    ask(question)
  }

  function startOver() {
    if (isAnswering && !window.confirm('Stop this answer and start a new conversation?')) return
    reset()
    setAnnounced('')
    input.current?.focus()
  }

  return (
    <>
      <PageHeader
        description="Ask questions about your contracts and invoices in plain English."
        action={
          turns.length > 0 ? (
            <Button variant="secondary" onClick={startOver}>
              <RotateCcw aria-hidden />
              New conversation
            </Button>
          ) : null
        }
      />

      {turns.length === 0 ? (
        <Welcome onPick={send} />
      ) : (
        <div role="log" aria-live="off" aria-label="Conversation" className="flex flex-col gap-6 pb-6">
          {turns.map((turn) => (
            <div key={turn.id} className="flex flex-col gap-4">
              <QuestionBubble text={turn.question} />
              <AnswerCard turn={turn} canRetry={!isAnswering} onRetry={() => retry(turn.id)} />
            </div>
          ))}
        </div>
      )}
      <div ref={end} />

      <p role="status" className="sr-only">
        {announced}
      </p>

      <Composer ref={input} isAnswering={isAnswering} onSend={send} onStop={stop} />
    </>
  )
}

function Welcome({ onPick }: { onPick: (question: string) => void }) {
  return (
    <section aria-labelledby="welcome-title" className="rounded-lg border border-border bg-surface px-6 py-10 text-center">
      <span className="mx-auto grid size-16 place-items-center rounded-full bg-primary-soft text-primary">
        <Sparkles aria-hidden className="size-8" />
      </span>
      <h2 id="welcome-title" className="mt-4 text-h2">
        How can I help today?
      </h2>
      <p className="mx-auto mt-2 max-w-prose text-text-muted">
        I can look up your invoices and contracts and explain what I find. Pick a question or
        type your own below.
      </p>
      <ul aria-label="Suggested questions" className="mx-auto mt-6 grid max-w-3xl gap-3 sm:grid-cols-2">
        {SUGGESTIONS.map((question) => (
          <li key={question}>
            <button
              type="button"
              onClick={() => onPick(question)}
              className="flex min-h-12 w-full items-center gap-3 rounded-md border border-border bg-bg px-4 py-3 text-left transition-colors hover:border-primary hover:bg-surface-strong"
            >
              <MessageCircleQuestion aria-hidden className="size-5 shrink-0 text-primary" />
              {question}
            </button>
          </li>
        ))}
      </ul>
    </section>
  )
}
