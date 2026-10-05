import { expect, test, type APIRequestContext, type Page } from '@playwright/test'

import { expectNoSeriousA11yIssues, uploadSample } from './helpers'

// INV-004 end to end, against the regenerated sample (scripts/e2e.sh). Reminder emails go to the
// local Mailpit inbox, which e2e.sh forces. The sample has outstanding invoices
// INV-2606 (Deccan, has an email), INV-2608 (Nilgiri, no email) and others.

const MAILPIT = process.env.MAILPIT_URL ?? 'http://localhost:8025'
const DECCAN = 'accounts@deccanprinting.example'

test.describe.configure({ mode: 'serial' })

test.beforeAll(async ({ request }) => {
  await uploadSample(request)
  await clearInbox(request)
})

const table = (page: Page) => page.getByRole('table', { name: 'Invoices' })
const rowOf = (page: Page, number: string) => table(page).locator('tbody tr').filter({ hasText: number })
const openerOf = (page: Page, number: string) =>
  rowOf(page, number).getByRole('button', { name: `Send email reminder for ${number}` })

async function clearInbox(request: APIRequestContext) {
  const response = await request.delete(`${MAILPIT}/api/v1/messages`)
  expect(response.ok()).toBe(true)
}

interface MailSummary {
  ID: string
  Subject: string
  To: { Address: string }[]
}

async function inbox(request: APIRequestContext): Promise<MailSummary[]> {
  const response = await request.get(`${MAILPIT}/api/v1/messages`)
  return ((await response.json()) as { messages: MailSummary[] }).messages
}

async function openReminder(page: Page, number: string) {
  await page.goto('/invoices?view=outstanding')
  await openerOf(page, number).click()
  const dialog = page.getByRole('dialog', { name: 'Send email reminder' })
  await expect(dialog).toBeVisible()
  return dialog
}

test('INV_004_AC1 every outstanding row has the button, and no other row does', async ({ page }) => {
  await page.goto('/invoices?view=all')
  const rows = table(page).locator('tbody tr')
  await expect(rows.first()).toBeVisible()

  const found = await rows.evaluateAll((trs) =>
    trs.map((tr) => ({
      status: tr.children[4]?.textContent?.trim() ?? '',
      hasButton: Boolean(tr.querySelector('button[aria-label^="Send email reminder for"]')),
    })),
  )

  expect(found.length).toBeGreaterThanOrEqual(17)
  expect(found.filter((r) => r.status === 'Outstanding').length).toBeGreaterThanOrEqual(4)
  for (const row of found) expect(row.hasButton, row.status).toBe(row.status === 'Outstanding')
})

test('INV_004_AC2_AC3 the dialog shows the invoice and a composed draft, and sends nothing', async ({
  page,
  request,
}) => {
  const dialog = await openReminder(page, 'INV-2606')

  await expect(dialog.getByText(/^INV-2606 · Deccan Printing Works · ₹1,25,000\.00 · \d+ days overdue$/)).toBeVisible()
  await expect(dialog.getByLabel('To')).toHaveValue(DECCAN)
  await expect(dialog.getByLabel('To')).toHaveAttribute('readonly', '')
  await expect(dialog.getByLabel('Subject')).toHaveValue(
    /^Payment reminder: invoice INV-2606 \(₹1,25,000\.00\) was due on \d{1,2} [A-Z][a-z]{2} \d{4}$/,
  )
  const message = dialog.getByLabel('Message')
  await expect(message).toHaveValue(/^Dear Deccan Printing Works,/)
  await expect(message).toHaveValue(/is now \d+ days overdue\./)
  await expect(message).toHaveValue(/Thank you,\nAccounts Team$/)

  expect(await inbox(request)).toHaveLength(0)
})

test('INV_004_AC4 a blank subject is explained next to the field and nothing is sent', async ({ page, request }) => {
  const dialog = await openReminder(page, 'INV-2606')
  await dialog.getByLabel('Subject').fill('')

  await dialog.getByRole('button', { name: 'Send reminder' }).click()

  await expect(dialog.getByText('Please enter a subject.')).toBeVisible()
  expect(await inbox(request)).toHaveLength(0)
})

test('INV_004_AC5_AC8 the edited reminder reaches the client and the row records it', async ({ page, request }) => {
  await clearInbox(request)
  const dialog = await openReminder(page, 'INV-2606')
  await dialog.getByLabel('Subject').fill('Friendly reminder about INV-2606')
  await dialog.getByLabel('Message').fill('Hello team,\n\nCould you please look into invoice INV-2606?\n\nThanks,\nMeera')

  await dialog.getByRole('button', { name: 'Send reminder' }).click()

  await expect(dialog.getByRole('status')).toContainText(`Reminder sent to ${DECCAN}`)
  await expect(dialog).toBeVisible() // stays open until the user closes it

  await expect.poll(async () => (await inbox(request)).length).toBe(1)
  const [mail] = await inbox(request)
  expect(mail!.Subject).toBe('Friendly reminder about INV-2606')
  expect(mail!.To.map((to) => to.Address)).toEqual([DECCAN])
  const full = await (await request.get(`${MAILPIT}/api/v1/message/${mail!.ID}`)).json()
  expect(full.Text).toContain('Could you please look into invoice INV-2606?')
  expect(full.Text).toContain('Meera')

  await dialog.getByRole('button', { name: 'Close' }).click()
  await expect(dialog).toBeHidden()
  await expect(rowOf(page, 'INV-2606')).toContainText(/Last reminder sent \d{1,2} [A-Z][a-z]{2} \d{4}/)

  // Reopening warns that one has already gone out, but still allows another (AC8).
  await openerOf(page, 'INV-2606').click()
  await expect(page.getByRole('dialog').getByText(/A reminder for this invoice was already sent on/)).toBeVisible()
  await expect(page.getByRole('button', { name: 'Send reminder' })).toBeEnabled()
})

test('INV_004_AC6 an invoice without an email explains what to do and cannot be sent', async ({ page, request }) => {
  await clearInbox(request)
  const dialog = await openReminder(page, 'INV-2608')

  await expect(dialog.getByText('No email address on file')).toBeVisible()
  await expect(
    dialog.getByText(
      "We don't have an email address for Nilgiri Tea Traders. Add it in the Customer Email column of your sheet and upload it again.",
    ),
  ).toBeVisible()
  await expect(dialog.getByRole('link', { name: 'Upload invoices' })).toHaveAttribute('href', '/invoices/upload')
  await expect(dialog.getByRole('button', { name: 'Send reminder' })).toHaveCount(0)
  expect(await inbox(request)).toHaveLength(0)
})

test('INV_004_AC13 the dialog works by keyboard, returns focus, and passes the accessibility scan', async ({ page }) => {
  await page.goto('/invoices?view=outstanding')
  const opener = openerOf(page, 'INV-2607')
  await expect(opener).toBeVisible()

  await opener.focus()
  await page.keyboard.press('Enter')
  const dialog = page.getByRole('dialog', { name: 'Send email reminder' })
  await expect(dialog.getByLabel('Subject')).toBeVisible()
  await expect(dialog.getByLabel('To')).toHaveValue('ap@sunrisepharma.example')

  await expectNoSeriousA11yIssues(page)

  await page.keyboard.press('Escape')
  await expect(dialog).toBeHidden()
  await expect(opener).toBeFocused()
})
