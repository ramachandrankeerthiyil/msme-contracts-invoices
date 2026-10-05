import { REMINDER_LIMITS } from './api'

// Client-side checks that mirror invoice-service's rules (INV-004 AC4), so the user hears about
// a problem next to the field instead of after a round trip. The service re-checks everything.

export interface ReminderFields {
  subject: string
  message: string
}

export type ReminderErrors = Partial<Record<keyof ReminderFields, string>>

/** Same wording as the service's `NO_CUSTOMER_EMAIL` message (INV-004 AC6). */
export function noEmailMessage(customerName: string): string {
  return `We don't have an email address for ${customerName}. Add it in the Customer Email column of your sheet and upload it again.`
}

export function validateReminder({ subject, message }: ReminderFields): ReminderErrors {
  const errors: ReminderErrors = {}
  const cleanSubject = subject.trim()
  const cleanMessage = message.trim()

  if (!cleanSubject) errors.subject = 'Please enter a subject.'
  else if (/[\r\n]/.test(cleanSubject)) errors.subject = 'The subject must be on one line.'
  else if (cleanSubject.length > REMINDER_LIMITS.subject)
    errors.subject = `The subject can be at most ${REMINDER_LIMITS.subject} characters. It is ${cleanSubject.length} now.`

  if (!cleanMessage) errors.message = 'Please write a message.'
  else if (cleanMessage.length > REMINDER_LIMITS.message)
    errors.message = `The message can be at most ${REMINDER_LIMITS.message.toLocaleString('en-IN')} characters. It is ${cleanMessage.length.toLocaleString('en-IN')} now.`

  return errors
}
