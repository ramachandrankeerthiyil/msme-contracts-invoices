import { describe, expect, it } from 'vitest'

import { formatDate, formatINR, relativeDue, todayIso } from './format'

describe('formatDate', () => {
  it.each([
    ['2026-09-24', '24 Sep 2026'],
    ['2026-01-05', '5 Jan 2026'],
    ['2026-12-31', '31 Dec 2026'],
  ])('%s → %s', (input, expected) => {
    expect(formatDate(input)).toBe(expected)
  })

  it('converts timestamps to the Asia/Kolkata date', () => {
    // 20:00 UTC on 24 Sep is 01:30 on 25 Sep in India.
    expect(formatDate('2026-09-24T20:00:00Z')).toBe('25 Sep 2026')
  })
})

describe('formatINR', () => {
  it.each([
    ['425000.00', '₹4,25,000.00'],
    ['12345678.5', '₹1,23,45,678.50'],
    ['999', '₹999.00'],
    ['1000', '₹1,000.00'],
    ['100000', '₹1,00,000.00'],
    ['0.5', '₹0.50'],
    ['-2500.75', '-₹2,500.75'],
    ['99999999999.99', '₹99,99,99,99,999.99'],
  ])('%s → %s', (input, expected) => {
    expect(formatINR(input)).toBe(expected)
  })

  it('does not lose precision on large decimal strings', () => {
    // Beyond Number.MAX_SAFE_INTEGER: a float-based formatter would print …992.
    expect(formatINR('9007199254740993.01')).toBe('₹9,00,71,99,25,47,40,993.01')
  })
})

describe('relativeDue', () => {
  const today = '2026-09-24'

  it.each([
    ['2026-09-24', 'due today'],
    ['2026-09-25', 'due in 1 day'],
    ['2026-09-27', 'due in 3 days'],
    ['2026-09-23', '1 day overdue'],
    ['2026-09-12', '12 days overdue'],
    ['2026-10-01', 'due in 7 days'],
  ])('%s → %s', (due, expected) => {
    expect(relativeDue(due, today)).toBe(expected)
  })
})

describe('todayIso', () => {
  it('uses the Asia/Kolkata calendar day', () => {
    expect(todayIso(new Date('2026-09-24T19:00:00Z'))).toBe('2026-09-25')
    expect(todayIso(new Date('2026-09-24T18:00:00Z'))).toBe('2026-09-24')
  })
})
