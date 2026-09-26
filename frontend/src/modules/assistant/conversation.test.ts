import { describe, expect, it } from 'vitest'

import {
  STORAGE_KEY,
  announcement,
  applyEvent,
  buildHistory,
  loadTurns,
  newTurn,
  saveTurns,
  type Turn,
} from './conversation'

function done(question: string, answer: string, id = question): Turn {
  return { ...newTurn(question, id), answer, status: 'done' }
}

describe('applyEvent (AST-001 AC4, AC6, AC12)', () => {
  it('appends text, tracks lookups by id and finishes', () => {
    let turn = newTurn('Q', 't')
    turn = applyEvent(turn, 'status', { id: 't1', state: 'running', label: 'Checking unpaid invoices' })
    turn = applyEvent(turn, 'text', { delta: 'You have ' })
    turn = applyEvent(turn, 'status', { id: 't1', state: 'done', label: 'Checked unpaid invoices', count: 9 })
    turn = applyEvent(turn, 'text', { delta: '9 unpaid invoices.' })
    turn = applyEvent(turn, 'done', { stop_reason: 'end_turn' })

    expect(turn.answer).toBe('You have 9 unpaid invoices.')
    expect(turn.lookups).toEqual([{ id: 't1', state: 'done', label: 'Checked unpaid invoices', count: 9 }])
    expect(turn.status).toBe('done')
  })

  it('keeps the error with its reference', () => {
    const turn = applyEvent(newTurn('Q', 't'), 'error', {
      code: 'ASSISTANT_FAILED',
      message: "Talk to Me couldn't answer that right now.",
      request_id: 'abc-12345',
    })

    expect(turn.status).toBe('error')
    expect(turn.error).toEqual({
      code: 'ASSISTANT_FAILED',
      message: "Talk to Me couldn't answer that right now.",
      requestId: 'abc-12345',
    })
  })

  it('ignores unknown events', () => {
    const turn = newTurn('Q', 't')
    expect(applyEvent(turn, 'ping', {})).toBe(turn)
  })
})

describe('buildHistory (AST-001 AC8)', () => {
  it('sends answered turns then the new question', () => {
    const history = buildHistory([done('Unpaid?', 'Nine.')], 'Biggest?')

    expect(history).toEqual([
      { role: 'user', content: 'Unpaid?' },
      { role: 'assistant', content: 'Nine.' },
      { role: 'user', content: 'Biggest?' },
    ])
  })

  it('leaves out failed turns and empty stopped turns so roles alternate', () => {
    const failed: Turn = { ...newTurn('Broken?', 'f'), status: 'error' }
    const emptyStop: Turn = { ...newTurn('Stopped?', 's'), status: 'stopped' }
    const partial: Turn = { ...newTurn('Partial?', 'p'), answer: 'Half an', status: 'stopped' }

    const history = buildHistory([failed, emptyStop, partial], 'Next')

    expect(history.map((m) => m.content)).toEqual(['Partial?', 'Half an', 'Next'])
  })

  it('keeps at most 20 messages, starting with the user', () => {
    const turns = Array.from({ length: 15 }, (_, i) => done(`Q${i}`, `A${i}`))

    const history = buildHistory(turns, 'Last')

    expect(history).toHaveLength(19)
    expect(history[0]).toEqual({ role: 'user', content: 'Q6' })
    expect(history.at(-1)).toEqual({ role: 'user', content: 'Last' })
  })

  it('trims very long answers to the service limit', () => {
    const history = buildHistory([done('Q', 'x'.repeat(9000))], 'Next')
    expect(history[1]?.content).toHaveLength(8000)
  })
})

describe('saving the conversation (AST-001 AC8)', () => {
  it('round-trips, and an answer cut off by a refresh counts as stopped', () => {
    const streaming: Turn = {
      ...newTurn('Q2', 't2'),
      answer: 'Part',
      lookups: [{ id: 't1', state: 'running', label: 'Checking invoices' }],
    }
    saveTurns(sessionStorage, [done('Q1', 'A1'), streaming])

    const loaded = loadTurns(sessionStorage)

    expect(loaded[0]).toEqual(done('Q1', 'A1'))
    expect(loaded[1]?.status).toBe('stopped')
    expect(loaded[1]?.lookups[0]?.state).toBe('failed')
  })

  it('clears storage for an empty conversation and survives bad data', () => {
    saveTurns(sessionStorage, [])
    expect(sessionStorage.getItem(STORAGE_KEY)).toBeNull()

    sessionStorage.setItem(STORAGE_KEY, '{not json')
    expect(loadTurns(sessionStorage)).toEqual([])
    expect(loadTurns(undefined)).toEqual([])
  })
})

describe('announcement (AST-001 AC13)', () => {
  it('reads the first sentence as plain text', () => {
    expect(announcement('You have **9 unpaid invoices** worth ₹9,94,150.75. Details: [INV-1](/invoices)')).toBe(
      'Answer ready. You have 9 unpaid invoices worth ₹9,94,150.75.',
    )
    expect(announcement('')).toBe('Answer ready.')
  })
})
