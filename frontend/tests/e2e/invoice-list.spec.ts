import { expect, test, type Locator } from '@playwright/test'

import { expectNoSeriousA11yIssues, listTotal, uploadSample } from './helpers'

// INV-002 end to end, against the regenerated sample (scripts/e2e.sh).

test.beforeAll(async ({ request }) => {
  await uploadSample(request)
})

const table = (page: import('@playwright/test').Page) => page.getByRole('table', { name: 'Invoices' })
const DUE_COLUMN = 2
const STATUS_COLUMN = 4

async function columnTexts(rows: Locator, column: number) {
  return rows.evaluateAll((trs, index) => trs.map((tr) => tr.children[index]?.textContent?.trim() ?? ''), column)
}

test('INV_002_AC3_AC4 the default view lists follow-ups, outstanding (most overdue) first', async ({ page }) => {
  await page.goto('/invoices')

  await expect(page.getByRole('navigation', { name: 'Filter by status' }).locator('[aria-current="page"]'))
    .toContainText('Needs follow-up')
  const rows = table(page).locator('tbody tr')
  await expect(rows.first()).toBeVisible()

  const statuses = await columnTexts(rows, STATUS_COLUMN)
  expect(statuses.every((s) => s === 'Outstanding' || s === 'At risk')).toBe(true)
  const firstAtRisk = statuses.indexOf('At risk')
  expect(firstAtRisk).toBeGreaterThan(0)
  expect(statuses.slice(firstAtRisk)).not.toContain('Outstanding')

  // Most overdue first: "N days overdue" never increases down the list.
  const hints = await columnTexts(rows, DUE_COLUMN)
  const overdue = hints.map((h) => /(\d+) days? overdue/.exec(h)?.[1]).filter(Boolean).map(Number)
  expect(overdue).toEqual([...overdue].sort((a, b) => b - a))
  expect(overdue.length).toBeGreaterThanOrEqual(4) // the sample has 4 invoices overdue
})

test('INV_002_AC3 the Paid tab shows only paid invoices with paid-on hints', async ({ page }) => {
  await page.goto('/invoices')
  await page.getByRole('link', { name: /^Paid/ }).click()

  await expect(page).toHaveURL(/view=paid/)
  const rows = table(page).locator('tbody tr')
  await expect(rows.first()).toBeVisible()
  expect(new Set(await columnTexts(rows, STATUS_COLUMN))).toEqual(new Set(['Paid']))
  await expect(rows.first()).toContainText('paid on')
})

test('INV_002_AC5_AC6 search narrows the list and the total follows', async ({ page }) => {
  await page.goto('/invoices?view=all')
  const before = await listTotal(page)

  await page.getByLabel('Search invoice number or customer').fill('Deccan')
  await expect(page).toHaveURL(/q=Deccan/)
  await expect(table(page).locator('tbody tr').first()).toContainText('Deccan Printing Works')
  const after = await listTotal(page)
  expect(after.count).toBeGreaterThan(0)
  expect(after.count).toBeLessThan(before.count)
})

test('INV_002_AC4_AC7 sorting is in the URL, survives reload, and Back restores the view', async ({ page }) => {
  await page.goto('/invoices?view=all')
  await table(page).getByRole('button', { name: 'Amount' }).click()
  await expect(page).toHaveURL(/sort=amount/)
  await table(page).getByRole('button', { name: 'Amount' }).click()
  await expect(page).toHaveURL(/order=desc/)
  await expect(page.getByRole('columnheader', { name: 'Amount' })).toHaveAttribute('aria-sort', 'descending')

  await page.reload()
  await expect(page.getByRole('columnheader', { name: 'Amount' })).toHaveAttribute('aria-sort', 'descending')

  await page.goBack()
  await expect(page).toHaveURL(/sort=amount/)
  await expect(page).not.toHaveURL(/order=desc/)
})

test('INV_002_AC9 export downloads the current view as Excel', async ({ page }) => {
  await page.goto('/invoices?view=outstanding')

  const download = page.waitForEvent('download')
  await page.getByRole('link', { name: 'Export to Excel' }).click()

  expect((await download).suggestedFilename()).toMatch(/^invoices-\d{4}-\d{2}-\d{2}\.xlsx$/)
})

test('INV_002 invoice list is accessible and fits a laptop screen without sideways scrolling', async ({ page }) => {
  await page.goto('/invoices?view=all')
  await expect(table(page)).toBeVisible()
  const layout = await table(page).evaluate((el) => ({
    overflow: el.scrollWidth - (el.parentElement?.clientWidth ?? 0),
    columns: [...el.querySelectorAll('thead th')].map(
      (th) => `${th.textContent}:${Math.round(th.getBoundingClientRect().width)}`,
    ),
  }))
  expect(layout.overflow, JSON.stringify(layout)).toBeLessThanOrEqual(1)
  await page.screenshot({ path: 'test-results/inv-002-list.png', fullPage: true })

  await expectNoSeriousA11yIssues(page)
})
