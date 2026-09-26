import { SendHorizontal, Square } from 'lucide-react'
import { forwardRef, useId, useState, type FormEvent, type KeyboardEvent } from 'react'

import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

import { COUNTER_FROM_CHARS, MAX_QUESTION_CHARS } from '../conversation'

export const DISCLAIMER =
  'Talk to Me can make mistakes. Check important details on the contract or invoice page.'

interface ComposerProps {
  isAnswering: boolean
  onSend: (question: string) => void
  onStop: () => void
}

/**
 * The question box (AST-001 AC3, AC4, AC11): Enter sends, Shift+Enter adds a line, it grows
 * from 2 to 6 lines, and Send becomes Stop while an answer is being written.
 */
export const Composer = forwardRef<HTMLTextAreaElement, ComposerProps>(function Composer(
  { isAnswering, onSend, onStop },
  ref,
) {
  const [text, setText] = useState('')
  const id = useId()
  const counterId = `${id}-counter`
  const disclaimerId = `${id}-disclaimer`
  const length = text.length
  const canSend = !isAnswering && text.trim().length > 0 && length <= MAX_QUESTION_CHARS

  function send(event?: FormEvent) {
    event?.preventDefault()
    if (!canSend) return
    onSend(text.trim())
    setText('')
  }

  function onKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault()
      send()
    }
  }

  return (
    <form
      onSubmit={send}
      className="sticky bottom-0 -mx-4 border-t border-border bg-bg px-4 pt-4 pb-4 sm:-mx-8 sm:px-8"
    >
      <label htmlFor={id} className="mb-2 block font-semibold">
        Ask a question about your contracts or invoices
      </label>
      <div className="flex items-end gap-3">
        <textarea
          ref={ref}
          id={id}
          value={text}
          onChange={(event) => setText(event.target.value)}
          onKeyDown={onKeyDown}
          rows={2}
          maxLength={MAX_QUESTION_CHARS}
          aria-describedby={cn(length >= COUNTER_FROM_CHARS && counterId, disclaimerId)}
          placeholder="For example: Which invoices are unpaid as of today?"
          className="field-sizing-content max-h-50 min-h-20 w-full resize-none rounded-md border border-border bg-bg px-4 py-3 placeholder:text-text-muted focus-visible:border-primary"
        />
        {isAnswering ? (
          <Button variant="secondary" onClick={onStop}>
            <Square aria-hidden />
            Stop
          </Button>
        ) : (
          <Button type="submit" disabled={!canSend}>
            <SendHorizontal aria-hidden />
            Send
          </Button>
        )}
      </div>
      <div className="mt-2 flex flex-col gap-1 text-small text-text-muted sm:flex-row sm:justify-between">
        <p id={disclaimerId}>{DISCLAIMER}</p>
        {length >= COUNTER_FROM_CHARS && (
          <p
            id={counterId}
            aria-live="polite"
            className={cn('shrink-0 tabular-nums', length >= MAX_QUESTION_CHARS && 'font-semibold text-warning')}
          >
            {length.toLocaleString('en-IN')} / {MAX_QUESTION_CHARS.toLocaleString('en-IN')} characters
          </p>
        )}
      </div>
    </form>
  )
})
