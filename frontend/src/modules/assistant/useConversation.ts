import { useCallback, useEffect, useRef, useState } from 'react'

import { ApiError, GENERIC_ERROR_MESSAGE } from '@/lib/api/client'
import { postEventStream } from '@/lib/api/sse'

import {
  applyEvent,
  buildHistory,
  loadTurns,
  newTurn,
  saveTurns,
  type Turn,
} from './conversation'

function sessionStore(): Storage | undefined {
  try {
    return window.sessionStorage
  } catch {
    return undefined
  }
}

let turnCounter = 0
function turnId(): string {
  turnCounter += 1
  return `turn-${Date.now()}-${turnCounter}`
}

export interface Conversation {
  turns: Turn[]
  isAnswering: boolean
  /** Set once each time an answer finishes, for the screen-reader announcement. */
  finishedTurnId?: string
  ask: (question: string) => void
  stop: () => void
  retry: (turnId: string) => void
  reset: () => void
}

/**
 * The conversation kept for this browser tab (AST-001 AC8): ask, stream, stop, retry, reset.
 * Saved to sessionStorage, so a refresh keeps it and closing the tab forgets it.
 */
export function useConversation(): Conversation {
  const [turns, setTurns] = useState<Turn[]>(() => loadTurns(sessionStore()))
  const [finishedTurnId, setFinishedTurnId] = useState<string>()
  const controller = useRef<AbortController | null>(null)
  const turnsRef = useRef(turns)
  turnsRef.current = turns

  useEffect(() => {
    saveTurns(sessionStore(), turns)
  }, [turns])

  // Leaving the page stops the answer (and the AI work behind it).
  useEffect(() => () => controller.current?.abort(), [])

  const update = useCallback((id: string, change: (turn: Turn) => Turn) => {
    setTurns((current) => current.map((t) => (t.id === id ? change(t) : t)))
  }, [])

  const ask = useCallback(
    (question: string) => {
      const text = question.trim()
      if (!text || controller.current) return
      const history = buildHistory(turnsRef.current, text)
      const turn = newTurn(text, turnId())
      const abort = new AbortController()
      controller.current = abort
      setTurns((current) => [...current, turn])

      postEventStream(
        '/assistant/chat',
        { messages: history },
        ({ event, data }) => update(turn.id, (t) => applyEvent(t, event, data)),
        abort.signal,
      )
        .then(() => {
          // A stream that ends without "done" or "error" was cut off.
          update(turn.id, (t) =>
            t.status === 'streaming'
              ? { ...t, status: 'error', error: { code: 'SERVICE_UNAVAILABLE', message: GENERIC_ERROR_MESSAGE } }
              : t,
          )
        })
        .catch((error: unknown) => {
          if (abort.signal.aborted) {
            update(turn.id, (t) => ({
              ...t,
              status: 'stopped',
              lookups: t.lookups.map((l) => (l.state === 'running' ? { ...l, state: 'failed' } : l)),
            }))
            return
          }
          const apiError = error instanceof ApiError ? error : undefined
          update(turn.id, (t) => ({
            ...t,
            status: 'error',
            error: {
              code: apiError?.code ?? 'ASSISTANT_FAILED',
              message: apiError?.message ?? GENERIC_ERROR_MESSAGE,
              requestId: apiError?.requestId,
            },
          }))
        })
        .finally(() => {
          if (controller.current === abort) controller.current = null
          setFinishedTurnId(turn.id)
        })
    },
    [update],
  )

  const stop = useCallback(() => controller.current?.abort(), [])

  const retry = useCallback(
    (id: string) => {
      const turn = turnsRef.current.find((t) => t.id === id)
      if (!turn || controller.current) return
      // Drop the failed turn first so it isn't sent as history, then ask again.
      turnsRef.current = turnsRef.current.filter((t) => t.id !== id)
      setTurns(turnsRef.current)
      ask(turn.question)
    },
    [ask],
  )

  const reset = useCallback(() => {
    controller.current?.abort()
    controller.current = null
    turnsRef.current = []
    setTurns([])
    setFinishedTurnId(undefined)
  }, [])

  const isAnswering = turns.some((t) => t.status === 'streaming')
  return { turns, isAnswering, finishedTurnId, ask, stop, retry, reset }
}
