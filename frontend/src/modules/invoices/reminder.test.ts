import { describe, expect, it } from 'vitest'

import { noEmailMessage, validateReminder } from './reminder'

describe('validateReminder', () => {
  it('INV_004_AC4 accepts a normal subject and message', () => {
    expect(validateReminder({ subject: 'Payment reminder', message: 'Dear client,\n\nPlease pay.' })).toEqual({})
  })

  it('INV_004_AC4 asks for a subject and a message', () => {
    expect(validateReminder({ subject: '   ', message: '\n ' })).toEqual({
      subject: 'Please enter a subject.',
      message: 'Please write a message.',
    })
  })

  it('INV_004_AC4 limits are inclusive: 200 subject characters and 5,000 message characters', () => {
    expect(validateReminder({ subject: 'S'.repeat(200), message: 'M'.repeat(5000) })).toEqual({})
    const errors = validateReminder({ subject: 'S'.repeat(201), message: 'M'.repeat(5001) })
    expect(errors.subject).toBe('The subject can be at most 200 characters. It is 201 now.')
    expect(errors.message).toBe('The message can be at most 5,000 characters. It is 5,001 now.')
  })

  it('INV_004_AC4 counts the trimmed text, like the service does', () => {
    expect(validateReminder({ subject: `  ${'S'.repeat(200)}  `, message: `\n${'M'.repeat(5000)}\n` })).toEqual({})
  })

  it('INV_004_AC10 refuses a subject with a line break', () => {
    expect(validateReminder({ subject: 'One\nTwo', message: 'Text' }).subject).toBe('The subject must be on one line.')
  })
})

describe('noEmailMessage', () => {
  it('INV_004_AC6 names the customer and says what to do', () => {
    expect(noEmailMessage('Nilgiri Tea Traders')).toBe(
      "We don't have an email address for Nilgiri Tea Traders. Add it in the Customer Email column of your sheet and upload it again.",
    )
  })
})
