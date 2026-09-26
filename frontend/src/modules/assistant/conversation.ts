// Conversation state for "Talk to Me" (AST-001). Pure functions, so the rules are unit-tested
// without React: how events update a turn, what history is sent, and what survives a refresh.

export type LookupState = 'running' | 'done' | 'failed'

export interface Lookup {
  id: string
  state: LookupState
  label: string
  count?: number
}

export type TurnStatus = 'streaming' | 'done' | 'stopped' | 'error'

export interface TurnError {
  code: string
  message: string
  requestId?: string
}

export interface Turn {
  id: string
  question: string
  answer: string
  lookups: Lookup[]
  status: TurnStatus
  error?: TurnError
}

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}

// Limits shared with the service (AST-001 design "API").
export const MAX_QUESTION_CHARS = 1000
export const COUNTER_FROM_CHARS = 800
const MAX_MESSAGES = 20
const MAX_ANSWER_CHARS = 8000

export const STORAGE_KEY = 'talk-to-me.conversation.v1'

export function newTurn(question: string, id: string): Turn {
  return { id, question, answer: '', lookups: [], status: 'streaming' }
}

/** Applies one server event to the turn being answered. */
export function applyEvent(turn: Turn, event: string, data: unknown): Turn {
  const payload = (data ?? {}) as Record<string, unknown>
  switch (event) {
    case 'text':
      return { ...turn, answer: turn.answer + String(payload.delta ?? '') }
    case 'status': {
      const lookup: Lookup = {
        id: String(payload.id),
        state: payload.state as LookupState,
        label: String(payload.label ?? ''),
        ...(typeof payload.count === 'number' ? { count: payload.count } : {}),
      }
      const exists = turn.lookups.some((l) => l.id === lookup.id)
      return {
        ...turn,
        lookups: exists
          ? turn.lookups.map((l) => (l.id === lookup.id ? lookup : l))
          : [...turn.lookups, lookup],
      }
    }
    case 'done':
      return { ...turn, status: 'done' }
    case 'error':
      return {
        ...turn,
        status: 'error',
        error: {
          code: String(payload.code ?? 'ASSISTANT_FAILED'),
          message: String(payload.message ?? ''),
          requestId: payload.request_id ? String(payload.request_id) : undefined,
        },
      }
    default:
      return turn
  }
}

/**
 * The messages sent with a new question: earlier answered turns (question + answer) followed by
 * the question, at most 20 messages, always starting with the user. Failed turns and stopped
 * turns with no text are left out so roles keep alternating.
 */
export function buildHistory(turns: Turn[], question: string): ChatMessage[] {
  const pairs: ChatMessage[][] = turns
    .filter((t) => (t.status === 'done' || t.status === 'stopped') && t.answer.trim())
    .map((t) => [
      { role: 'user', content: t.question },
      { role: 'assistant', content: t.answer.slice(0, MAX_ANSWER_CHARS) },
    ])
  const keep = Math.floor((MAX_MESSAGES - 1) / 2)
  return [...pairs.slice(-keep).flat(), { role: 'user', content: question }]
}

/** Reads the saved conversation. An answer interrupted by a refresh counts as stopped. */
export function loadTurns(storage: Storage | undefined): Turn[] {
  try {
    const raw = storage?.getItem(STORAGE_KEY)
    if (!raw) return []
    const turns = JSON.parse(raw) as Turn[]
    if (!Array.isArray(turns)) return []
    return turns.map((t) =>
      t.status === 'streaming'
        ? {
            ...t,
            status: 'stopped',
            lookups: t.lookups.map((l) => (l.state === 'running' ? { ...l, state: 'failed' } : l)),
          }
        : t,
    )
  } catch {
    return []
  }
}

export function saveTurns(storage: Storage | undefined, turns: Turn[]): void {
  try {
    if (turns.length === 0) storage?.removeItem(STORAGE_KEY)
    else storage?.setItem(STORAGE_KEY, JSON.stringify(turns))
  } catch {
    // Storage full or blocked: the conversation still works, it just won't survive a refresh.
  }
}

/** "Answer ready." plus the answer's first sentence, as plain text for screen readers. */
export function announcement(answer: string): string {
  const plain = answer
    .replace(/\[([^\]]+)\]\([^)]*\)/g, '$1')
    .replace(/[*_`#>|]/g, '')
    .replace(/\s+/g, ' ')
    .trim()
  const first = plain.match(/^.*?[.!?](?=\s|$)/)?.[0] ?? plain.slice(0, 200)
  return first ? `Answer ready. ${first}` : 'Answer ready.'
}
