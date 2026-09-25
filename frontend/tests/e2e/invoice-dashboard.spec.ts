import { expect, test, type Page } from '@playwright/test'

import { expectNoSeriousA11yIssues, listTotal, uploadSample } from './helpers'

// INV-003 end to end: every dashboard number must match the list behind it (AC6).

test.beforeAll(async ({ request }) => {
  await uploadSample(request)
})

/**
 * Reads the value from a KPI card's accessible name: "Need follow-up: 9. …" → "9",
 * "Total invoice value: ₹5,57,250.00. Due this week" → "₹5,57,250.00".
 */
async function kpiValue(page: Page, label: string) {
  const name = (await page.getByRole('link', { name: new RegExp(`^${label}: `) }).getAttribute('aria-label')) ?? ''
  const match = new RegExp(`^${label}: (.+?)\\.(?: |$)`).exec(name)
  expect(match, name).not.toBeNull()
  return match![1]!
}

test('INV_003_AC1 shows the week the numbers cover', async ({ page }) => {
  await page.goto('/invoices/dashboard')

  await expect(page.getByText(/^Week of .+ \(from your upload on .+\)$/)).toBeVisible()
})

test('INV_003_AC2_AC3_AC6 the week cards match the list they open', async ({ page }) => {
  await page.goto('/invoices/dashboard')
  const value = await kpiValue(page, 'Total invoice value')
  const count = Number(await kpiValue(page, 'Invoices this week'))

  await page.getByRole('link', { name: /^Invoices this week: / }).click()
  await expect(page).toHaveURL(/view=all&due_from=.*&due_to=/)
  const total = await listTotal(page)

  expect(total.count).toBe(count)
  expect(total.amount).toBe(value)
})

test('INV_003_AC4_AC6 the follow-up card matches its list and includes older overdue invoices', async ({ page }) => {
  await page.goto('/invoices/dashboard')
  const followUp = Number(await kpiValue(page, 'Need follow-up'))
  expect(followUp).toBeGreaterThanOrEqual(8) // freshly generated sample: 4 outstanding + 4 at risk

  await page.getByRole('link', { name: /^Need follow-up: / }).click()
  await expect(page).toHaveURL(/due_to=/)
  expect((await listTotal(page)).count).toBe(followUp)
  // INV-2606 is generated 40 days overdue: it was overdue long before this week started.
  await expect(page.getByRole('table', { name: 'Invoices' })).toContainText('40 days overdue')
})

test('INV_003_AC7 a top follow-up opens that invoice in the list', async ({ page }) => {
  await page.goto('/invoices/dashboard')
  const top = page.getByRole('region', { name: 'Top 5 to follow up' }).getByRole('listitem').first()
  await expect(top).toContainText('INV-2606 · 40 days overdue')

  await top.getByRole('link').click()

  await expect(page).toHaveURL(/q=INV-/)
  await expect(page.getByRole('table', { name: 'Invoices' }).locator('tbody tr')).toHaveCount(1)
})

test('INV_003_AC8 value by status lists all four statuses', async ({ page }) => {
  await page.goto('/invoices/dashboard')

  const table = page.getByRole('table', { name: /by payment status/ })
  await expect(table.getByRole('rowheader')).toHaveText(['Outstanding', 'At risk', 'Open', 'Paid'])
  await page.screenshot({ path: 'test-results/inv-003-dashboard.png', fullPage: true })
  await expectNoSeriousA11yIssues(page)
})

test('PLT_001_AC5 Home shows the invoice headline numbers', async ({ page }) => {
  await page.goto('/')

  const invoices = page.getByRole('region', { name: 'Invoices' })
  await expect(invoices.getByRole('link', { name: /^Need follow-up: / })).toBeVisible()
  await expect(invoices.getByRole('link', { name: /^Total invoice value: / })).toBeVisible()
})
