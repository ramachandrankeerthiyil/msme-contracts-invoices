import { Check, CircleAlert, Copy, LoaderCircle, Sparkles } from 'lucide-react'
import { useEffect, useState } from 'react'

import { ErrorAlert } from '@/components/common/ErrorAlert'
import { Button } from '@/components/ui/button'
import { ApiError } from '@/lib/api/client'

import type { Lookup, Turn } from '../conversation'
import { AnswerMarkdown } from './AnswerMarkdown'

/** The user's question: right-aligned, light blue. */
export function QuestionBubble({ text }: { text: string }) {
  return (
    <div className="flex justify-end">
      <div className="max-w-prose rounded-lg rounded-br-md bg-primary-soft px-5 py-3 break-words whitespace-pre-wrap">
        <span className="sr-only">You asked: </span>
        {text}
      </div>
    </div>
  )
}

interface AnswerCardProps {
  turn: Turn
  onRetry: () => void
  canRetry: boolean
}

/** Talk to Me's answer: lookups, the answer text, and Copy or Try again (AST-001 AC4–AC7). */
export function AnswerCard({ turn, onRetry, canRetry }: AnswerCardProps) {
  const streaming = turn.status === 'streaming'
  const waiting = streaming && !turn.answer && turn.lookups.every((l) => l.state !== 'running')

  return (
    <article
      aria-label="Talk to Me's answer"
      aria-busy={streaming}
      className="rounded-lg border border-border bg-bg p-5 shadow-card sm:p-6"
    >
      <p className="flex items-center gap-2 text-small font-semibold text-primary">
        <Sparkles aria-hidden className="size-5" />
        Talk to Me
      </p>

      {turn.lookups.length > 0 && <LookupList lookups={turn.lookups} />}

      {waiting && (
        <p className="mt-3 flex items-center gap-2 text-text-muted">
          <LoaderCircle aria-hidden className="size-5 animate-spin text-primary" />
          Thinking…
        </p>
      )}

      {turn.answer && (
        <div className="mt-3">
          <AnswerMarkdown text={turn.answer} />
          {streaming && (
            <span aria-hidden className="ml-1 inline-block h-5 w-2 animate-pulse bg-primary align-middle" />
          )}
          {turn.status === 'stopped' && <p className="mt-2 text-small text-text-muted">(stopped)</p>}
        </div>
      )}

      {turn.status === 'stopped' && !turn.answer && (
        <p className="mt-3 text-text-muted">(stopped before answering)</p>
      )}

      {turn.status === 'error' && turn.error && (
        <div className="mt-4">
          <ErrorAlert
            title="Talk to Me couldn't answer that"
            error={new ApiError(0, turn.error.code, turn.error.message, turn.error.requestId)}
            onRetry={canRetry ? onRetry : undefined}
          />
        </div>
      )}

      {(turn.status === 'done' || turn.status === 'stopped') && turn.answer && (
        <CopyButton text={turn.answer} />
      )}
    </article>
  )
}

function LookupList({ lookups }: { lookups: Lookup[] }) {
  return (
    <ul aria-label="What I looked up" className="mt-3 flex flex-col gap-1 text-small text-text-muted">
      {lookups.map((lookup) => (
        <li key={lookup.id} className="flex items-center gap-2">
          {lookup.state === 'running' && (
            <LoaderCircle aria-hidden className="size-4 shrink-0 animate-spin text-primary" />
          )}
          {lookup.state === 'done' && <Check aria-hidden className="size-4 shrink-0 text-success" />}
          {lookup.state === 'failed' && <CircleAlert aria-hidden className="size-4 shrink-0 text-warning" />}
          <span>
            {lookup.label}
            {lookup.state === 'running' && '…'}
            {lookup.count !== undefined && ` (${lookup.count})`}
          </span>
        </li>
      ))}
    </ul>
  )
}

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    if (!copied) return
    const timer = window.setTimeout(() => setCopied(false), 2000)
    return () => window.clearTimeout(timer)
  }, [copied])

  async function copy() {
    try {
      await navigator.clipboard.writeText(text)
      setCopied(true)
    } catch {
      // Clipboard blocked (e.g. insecure context): nothing useful to show.
    }
  }

  return (
    <Button variant="secondary" className="mt-4" onClick={copy}>
      {copied ? <Check aria-hidden /> : <Copy aria-hidden />}
      {copied ? 'Copied' : 'Copy'}
      <span className="sr-only"> answer</span>
    </Button>
  )
}
