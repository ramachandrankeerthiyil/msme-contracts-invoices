import { QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { createMemoryRouter, RouterProvider } from 'react-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { createQueryClient } from '@/app/queryClient'
import { routes } from '@/app/router'
import { ApiError } from '@/lib/api/client'

import * as api from '../api'
import { INVOICE_PAGE, invoiceItem, reminderDraft } from '../testData'

vi.mock('../api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api')>()
  return { ...actual, listInvoices: vi.fn(), getReminderDraft: vi.fn(), sendReminder: vi.fn() }
})

const SENT = { id: 'r1', invoice_id: 'id-2606', to: 'accounts@deccanprinting.example', sent_at: '2026-10-05T04:00:00Z' }
const OPEN_BUTTON = 'Send email reminder for INV-2606'

function renderInvoices() {
  const router = createMemoryRouter(routes, { initialEntries: ['/invoices'] })
  render(
    <QueryClientProvider client={createQueryClient()}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  )
  return router
}

async function openDialog() {
  const opener = await screen.findByRole('button', { name: OPEN_BUTTON })
  await userEvent.click(opener)
  return { opener, dialog: await screen.findByRole('dialog', { name: 'Send email reminder' }) }
}

const sendButton = () => screen.getByRole('button', { name: /^(Send reminder|Sending…)$/ })

beforeEach(() => {
  vi.mocked(api.listInvoices).mockReset().mockResolvedValue(INVOICE_PAGE)
  vi.mocked(api.getReminderDraft).mockReset().mockResolvedValue(reminderDraft())
  vi.mocked(api.sendReminder).mockReset().mockResolvedValue(SENT)
})

describe('Send email reminder button', () => {
  it('INV_004_AC1 appears only on rows the service says can be reminded', async () => {
    renderInvoices()

    const table = await screen.findByRole('table', { name: 'Invoices' })
    expect(within(table).getAllByRole('button', { name: /^Send email reminder for / })).toHaveLength(1)
    expect(within(table).getByRole('button', { name: OPEN_BUTTON })).toBeInTheDocument()
    expect(within(table).queryByRole('button', { name: /INV-2611/ })).not.toBeInTheDocument() // at risk
    expect(within(table).queryByRole('button', { name: /INV-2603/ })).not.toBeInTheDocument() // paid
  })

  it('INV_004_AC1 the page does not decide: can_remind drives the button, not the status', async () => {
    vi.mocked(api.listInvoices).mockResolvedValue({
      ...INVOICE_PAGE,
      items: [invoiceItem({ status: 'outstanding', can_remind: false })],
    })
    renderInvoices()

    await screen.findByRole('table', { name: 'Invoices' })
    expect(screen.queryByRole('button', { name: /Send email reminder for/ })).not.toBeInTheDocument()
  })

  it('INV_004_AC8 shows when the last reminder was sent, under the button', async () => {
    vi.mocked(api.listInvoices).mockResolvedValue({
      ...INVOICE_PAGE,
      items: [
        invoiceItem({ last_reminder_at: '2026-09-30T04:00:00Z' }),
        invoiceItem({ id: 'id-2603', invoice_number: 'INV-2603', status: 'paid', can_remind: false, last_reminder_at: '2026-09-01T04:00:00Z', paid_date: '2026-09-12', days_until_due: null }),
        invoiceItem({ id: 'id-2650', invoice_number: 'INV-2650', can_remind: true }),
      ],
    })
    renderInvoices()

    const rows = within(await screen.findByRole('table', { name: 'Invoices' })).getAllByRole('row')
    expect(within(rows[1]!).getByText('Last reminder sent 30 Sep 2026')).toBeInTheDocument()
    expect(within(rows[1]!).getByRole('button', { name: OPEN_BUTTON })).toBeInTheDocument()
    expect(within(rows[2]!).getByText('Last reminder sent 1 Sep 2026')).toBeInTheDocument() // history kept
    expect(within(rows[3]!).queryByText(/Last reminder sent/)).not.toBeInTheDocument()
  })
})

describe('Reminder dialog', () => {
  it('INV_004_AC2 opens with the invoice summary and the draft, and sends nothing', async () => {
    renderInvoices()

    const { dialog } = await openDialog()

    expect(api.getReminderDraft).toHaveBeenCalledWith('id-2606')
    const view = within(dialog)
    expect(view.getByText('INV-2606 · Deccan Printing Works · ₹1,25,000.00 · 41 days overdue')).toBeInTheDocument()
    expect(await view.findByLabelText('To')).toHaveValue('accounts@deccanprinting.example')
    expect(view.getByLabelText('Subject')).toHaveValue(reminderDraft().subject)
    expect(view.getByLabelText('Message')).toHaveValue(reminderDraft().message)
    expect(view.getByRole('button', { name: 'Send reminder' })).toBeEnabled()
    expect(api.sendReminder).not.toHaveBeenCalled()
  })

  it('INV_004_AC4 shows the recipient but does not let it be changed', async () => {
    renderInvoices()
    await openDialog()

    const to = await screen.findByLabelText('To')

    expect(to).toHaveAttribute('readonly')
    await userEvent.type(to, 'someone-else@example.com')
    expect(to).toHaveValue('accounts@deccanprinting.example')
  })

  it('INV_004_AC4 an empty subject or message is explained next to the field and nothing is sent', async () => {
    renderInvoices()
    await openDialog()
    await userEvent.clear(await screen.findByLabelText('Subject'))
    await userEvent.clear(screen.getByLabelText('Message'))

    await userEvent.click(sendButton())

    expect(screen.getByText('Please enter a subject.')).toBeInTheDocument()
    expect(screen.getByText('Please write a message.')).toBeInTheDocument()
    expect(screen.getByLabelText('Subject')).toHaveAttribute('aria-invalid', 'true')
    expect(screen.getByLabelText('Subject')).toHaveAccessibleDescription('Please enter a subject.')
    expect(screen.getByLabelText('Subject')).toHaveFocus()
    expect(api.sendReminder).not.toHaveBeenCalled()
  })

  it('INV_004_AC4 a message over 5,000 characters is refused before sending', async () => {
    renderInvoices()
    await openDialog()
    const message = await screen.findByLabelText('Message')
    await userEvent.clear(message)
    await userEvent.click(message)
    await userEvent.paste('M'.repeat(5001))

    await userEvent.click(sendButton())

    expect(screen.getByText(/The message can be at most 5,000 characters/)).toBeInTheDocument()
    expect(api.sendReminder).not.toHaveBeenCalled()
  })

  it('INV_004_AC5 sends the edited subject and message, then confirms and stays open', async () => {
    renderInvoices()
    await openDialog()
    const subject = await screen.findByLabelText('Subject')
    await userEvent.clear(subject)
    await userEvent.type(subject, '  A quick note  ')
    const message = screen.getByLabelText('Message')
    await userEvent.clear(message)
    await userEvent.type(message, 'Please pay soon.')

    await userEvent.click(sendButton())

    await waitFor(() =>
      expect(api.sendReminder).toHaveBeenCalledExactlyOnceWith('id-2606', {
        subject: 'A quick note',
        message: 'Please pay soon.',
      }),
    )
    const confirmation = await screen.findByRole('status')
    expect(confirmation).toHaveTextContent('Reminder sent to accounts@deccanprinting.example')
    expect(screen.getByRole('dialog', { name: 'Send email reminder' })).toBeInTheDocument()
    expect(screen.queryByLabelText('Subject')).not.toBeInTheDocument()
  })

  it('INV_004_AC5_AC8 after sending, the invoice list is refreshed', async () => {
    renderInvoices()
    await openDialog()
    await userEvent.click(await screen.findByRole('button', { name: 'Send reminder' }))
    await screen.findByRole('status')

    await waitFor(() => expect(vi.mocked(api.listInvoices).mock.calls.length).toBeGreaterThan(1))
  })

  it('INV_004_AC5 Close dismisses the confirmation', async () => {
    renderInvoices()
    await openDialog()
    await userEvent.click(await screen.findByRole('button', { name: 'Send reminder' }))
    await screen.findByRole('status')

    await userEvent.click(screen.getByRole('button', { name: 'Close' }))

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })

  it('INV_004_AC6 without an email it explains, links to upload, and offers no Send button', async () => {
    vi.mocked(api.getReminderDraft).mockResolvedValue(reminderDraft({ to: null, customer_name: 'Deccan Printing Works' }))
    renderInvoices()

    const { dialog } = await openDialog()

    const view = within(dialog)
    expect(await view.findByText('No email address on file')).toBeInTheDocument()
    expect(
      view.getByText(
        "We don't have an email address for Deccan Printing Works. Add it in the Customer Email column of your sheet and upload it again.",
      ),
    ).toBeInTheDocument()
    expect(view.getByRole('link', { name: 'Upload invoices' })).toHaveAttribute('href', '/invoices/upload')
    expect(view.queryByRole('button', { name: 'Send reminder' })).not.toBeInTheDocument()
    expect(view.queryByLabelText('Subject')).not.toBeInTheDocument()
  })

  it('INV_004_AC7 a failed send says nothing was sent, keeps the edits, and can be retried', async () => {
    vi.mocked(api.sendReminder)
      .mockRejectedValueOnce(
        new ApiError(424, 'EMAIL_NOT_SENT', "We couldn't send this email, so nothing was sent. Please try again in a minute."),
      )
      .mockResolvedValueOnce(SENT)
    renderInvoices()
    await openDialog()
    const subject = await screen.findByLabelText('Subject')
    await userEvent.clear(subject)
    await userEvent.type(subject, 'My own subject')

    await userEvent.click(sendButton())

    const alert = await screen.findByRole('alert')
    expect(alert).toHaveTextContent('Reminder not sent')
    expect(alert).toHaveTextContent("We couldn't send this email, so nothing was sent. Please try again in a minute.")
    expect(screen.getByLabelText('Subject')).toHaveValue('My own subject')
    expect(sendButton()).toBeEnabled()

    await userEvent.click(sendButton())

    expect(await screen.findByRole('status')).toHaveTextContent('Reminder sent to')
    expect(api.sendReminder).toHaveBeenCalledTimes(2)
    expect(api.sendReminder).toHaveBeenLastCalledWith('id-2606', expect.objectContaining({ subject: 'My own subject' }))
  })

  it('INV_004_AC8 warns when a reminder was already sent, but still allows another', async () => {
    vi.mocked(api.getReminderDraft).mockResolvedValue(reminderDraft({ last_reminder_at: '2026-09-30T04:00:00Z' }))
    renderInvoices()

    const { dialog } = await openDialog()

    expect(await within(dialog).findByText('A reminder for this invoice was already sent on 30 Sep 2026.')).toBeInTheDocument()
    expect(within(dialog).getByRole('button', { name: 'Send reminder' })).toBeEnabled()
  })

  it('INV_004_AC9 an invoice that is no longer overdue gets no draft, and the list refreshes', async () => {
    vi.mocked(api.getReminderDraft).mockRejectedValue(
      new ApiError(409, 'INVOICE_NOT_REMINDABLE', 'This invoice is no longer overdue, so no reminder was sent.'),
    )
    renderInvoices()
    await screen.findByRole('button', { name: OPEN_BUTTON })
    const before = vi.mocked(api.listInvoices).mock.calls.length

    await userEvent.click(screen.getByRole('button', { name: OPEN_BUTTON }))

    const dialog = await screen.findByRole('dialog', { name: 'Send email reminder' })
    expect(await within(dialog).findByText('No reminder sent')).toBeInTheDocument()
    expect(within(dialog).getByText('This invoice is no longer overdue, so no reminder was sent.')).toBeInTheDocument()
    expect(within(dialog).queryByRole('button', { name: 'Send reminder' })).not.toBeInTheDocument()
    await waitFor(() => expect(vi.mocked(api.listInvoices).mock.calls.length).toBeGreaterThan(before))
  })

  it('INV_004_AC9 an invoice paid while the dialog was open is refused at send time', async () => {
    vi.mocked(api.sendReminder).mockRejectedValue(
      new ApiError(409, 'INVOICE_NOT_REMINDABLE', 'This invoice is no longer overdue, so no reminder was sent.'),
    )
    renderInvoices()
    await openDialog()
    await userEvent.click(await screen.findByRole('button', { name: 'Send reminder' }))

    expect(await screen.findByText('No reminder sent')).toBeInTheDocument()
    expect(screen.getByText('This invoice is no longer overdue, so no reminder was sent.')).toBeInTheDocument()
    expect(screen.queryByLabelText('Subject')).not.toBeInTheDocument()
  })

  it('INV_004_AC11 while sending, the button is disabled and a double click sends one email', async () => {
    let finish: (value: typeof SENT) => void = () => {}
    vi.mocked(api.sendReminder).mockReturnValue(new Promise((resolve) => (finish = resolve)))
    renderInvoices()
    await openDialog()
    const send = await screen.findByRole('button', { name: 'Send reminder' })

    await userEvent.dblClick(send)

    expect(await screen.findByRole('button', { name: 'Sending…' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Cancel' })).toBeDisabled()
    expect(api.sendReminder).toHaveBeenCalledTimes(1)
    finish(SENT)
    expect(await screen.findByRole('status')).toBeInTheDocument()
  })

  it('INV_004_AC11 the dialog cannot be dismissed with Escape while sending', async () => {
    vi.mocked(api.sendReminder).mockReturnValue(new Promise(() => {}))
    renderInvoices()
    await openDialog()
    await userEvent.click(await screen.findByRole('button', { name: 'Send reminder' }))
    await screen.findByRole('button', { name: 'Sending…' })

    await userEvent.keyboard('{Escape}')

    expect(screen.getByRole('dialog', { name: 'Send email reminder' })).toBeInTheDocument()
  })
})

describe('Reminder dialog accessibility', () => {
  it('INV_004_AC13 the opener names its invoice, and every field has a label', async () => {
    renderInvoices()
    // Checked first: an open dialog hides the page behind it from assistive technology.
    const opener = await screen.findByRole('button', { name: OPEN_BUTTON })
    expect(opener).toHaveTextContent('Send email reminder')

    const { dialog } = await openDialog()

    const view = within(dialog)
    await view.findByLabelText('To')
    expect(view.getByLabelText('Subject')).toBeInTheDocument()
    expect(view.getByLabelText('Message')).toBeInTheDocument()
  })

  it('INV_004_AC13 Escape closes the dialog and focus returns to the button that opened it', async () => {
    renderInvoices()
    const { opener } = await openDialog()
    await screen.findByLabelText('Subject')

    await userEvent.keyboard('{Escape}')

    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
    expect(opener).toHaveFocus()
  })

  it('INV_004_AC13 focus moves into the dialog when it opens', async () => {
    renderInvoices()
    const { dialog } = await openDialog()
    await screen.findByLabelText('Subject')

    await waitFor(() => expect(dialog.contains(document.activeElement)).toBe(true))
  })

  it('INV_004_AC13 after sending, focus moves to the confirmation so it is announced', async () => {
    renderInvoices()
    await openDialog()
    await userEvent.click(await screen.findByRole('button', { name: 'Send reminder' }))

    const confirmation = await screen.findByRole('status')

    await waitFor(() => expect(confirmation.parentElement).toHaveFocus())
  })

  it('INV_004_AC13 an error is announced as an alert', async () => {
    vi.mocked(api.getReminderDraft).mockRejectedValue(new ApiError(500, 'INTERNAL_ERROR', 'Something went wrong on our side.'))
    renderInvoices()
    const { dialog } = await openDialog()

    expect(await within(dialog).findByRole('alert')).toHaveTextContent('We couldn\'t prepare the reminder')
    expect(within(dialog).getByRole('button', { name: 'Try again' })).toBeInTheDocument()
  })
})
