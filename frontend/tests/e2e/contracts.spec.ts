import { expect, test, type Page } from '@playwright/test'

import { expectNoSeriousA11yIssues, expiringContractPdf, makePdf } from './helpers'

// CON-001 … CON-003 end to end. scripts/e2e.sh runs the stack with CONTRACT_EXTRACTOR=fake
// (no AI calls) and removes the "e2e-" contracts afterwards.

const PDF = 'application/pdf'

async function uploadContract(page: Page, name: string, buffer: Buffer) {
  await page.goto('/contracts/upload')
  await page.getByTestId('file-input').setInputFiles({ name, mimeType: PDF, buffer })
  await page.getByRole('button', { name: 'Upload contract' }).click()
}

test('CON_001_AC8_CON_002_AC5 upload → progress → the contract, fully read', async ({ page }) => {
  const title = `E2E Services Agreement ${Date.now()}`
  await uploadContract(page, 'e2e-services.pdf', expiringContractPdf(title))

  await expect(page).toHaveURL(/\/contracts\/[0-9a-f-]{36}$/)
  await expect(page.getByRole('heading', { level: 1 })).toHaveText(title, { timeout: 20_000 })

  await expect(page.getByText('Extracted by AI')).toBeVisible()
  await expect(page.getByText(/^At risk: Expires in 2 days · 1 high risk$/)).toBeVisible()
  const parties = page.getByRole('region', { name: 'Parties' })
  await expect(parties).toContainText('Kaveri Agro Foods Private Limited')
  await expect(parties).toContainText('Bluewave Logistics LLP')
  const risks = page.getByRole('region', { name: 'Risks' })
  await expect(risks.getByRole('heading', { name: 'High risks' })).toBeVisible()
  await expect(risks).toContainText('without limit')
  await expect(page.getByRole('region', { name: 'Terms' }).getByRole('heading', { name: 'Payment' })).toBeVisible()

  const download = page.waitForEvent('download')
  await page.getByRole('link', { name: 'Download original' }).click()
  expect((await download).suggestedFilename()).toBe('e2e-services.pdf')

  await page.screenshot({ path: 'test-results/con-002-detail.png', fullPage: true })
  await expectNoSeriousA11yIssues(page)
})

test('CON_001_AC3a uploading the same file again links to the first one', async ({ page }) => {
  const buffer = expiringContractPdf(`E2E Duplicate ${Date.now()}`)
  await uploadContract(page, 'e2e-duplicate.pdf', buffer)
  await expect(page).toHaveURL(/\/contracts\/[0-9a-f-]{36}$/)
  const firstUrl = page.url()

  await uploadContract(page, 'e2e-duplicate-again.pdf', buffer)

  await expect(page.getByText(/^This contract was already uploaded on /)).toBeVisible()
  await page.getByRole('link', { name: 'Open the existing contract' }).click()
  await expect(page).toHaveURL(firstUrl)
})

test('CON_001_AC6_AC9 a contract that cannot be read explains why and offers Try again', async ({ page }) => {
  // File names containing "fail" make the stand-in extractor fail every attempt.
  await uploadContract(page, 'e2e-fail.pdf', expiringContractPdf(`E2E Failure ${Date.now()}`))

  const heading = page.getByText("We couldn't read this contract", { exact: true })
  await expect(heading).toBeVisible({ timeout: 20_000 })
  await expect(page.getByText(/Please try again, or check the file\./)).toBeVisible()
  await page.getByRole('button', { name: 'Try again' }).click()
  await expect(heading).toBeVisible({ timeout: 20_000 })
})

test('CON_001_AC6 a scanned (image-only) PDF is explained in plain words', async ({ page }) => {
  await uploadContract(page, 'e2e-scan.pdf', makePdf([`${Date.now()}`]))

  await expect(page.getByText(/looks like a scanned image/)).toBeVisible({ timeout: 20_000 })
})

test('CON_001_AC1 wrong file types are refused before upload', async ({ page }) => {
  await page.goto('/contracts/upload')
  await page.getByTestId('file-input').setInputFiles({ name: 'notes.txt', mimeType: 'text/plain', buffer: Buffer.from('x') })

  await expect(page.getByRole('alert')).toHaveText(
    "This file type isn't supported. Please choose a PDF or Word (.docx) file.",
  )
})

test('CON_002_AC1_AC2 the list finds a contract by party and fits a laptop screen', async ({ page }) => {
  const title = `E2E Searchable ${Date.now()}`
  await uploadContract(page, 'e2e-search.pdf', expiringContractPdf(title))
  await expect(page.getByRole('heading', { level: 1 })).toHaveText(title, { timeout: 20_000 })

  await page.goto('/contracts?view=at_risk')
  await page.getByLabel('Search contract title or party').fill(title)
  await expect(page).toHaveURL(/q=E2E/)
  const table = page.getByRole('table', { name: 'Contracts' })
  await expect(table.locator('tbody tr')).toHaveCount(1)
  await expect(table).toContainText('Bluewave Logistics LLP')

  const overflow = await table.evaluate((el) => el.scrollWidth - (el.parentElement?.clientWidth ?? 0))
  expect(overflow).toBeLessThanOrEqual(1)
  await expectNoSeriousA11yIssues(page)
})

test('CON_003_AC3 every dashboard card matches the list it opens', async ({ page }) => {
  await uploadContract(page, 'e2e-dashboard.pdf', expiringContractPdf(`E2E Dashboard ${Date.now()}`))
  await expect(page.getByText('Extracted by AI')).toBeVisible({ timeout: 20_000 })

  for (const label of ['Total contracts', 'In force', 'At risk', 'Expired', 'Not yet started', 'No end date']) {
    await page.goto('/contracts/dashboard')
    // KPI cards are named "<label>: <number>. …" (the Needs-attention links start "At risk: <title>").
    const card = page.getByRole('link', { name: new RegExp(`^${label}: [\\d,]+\\.`) })
    const value = Number(/: ([\d,]+)\./.exec((await card.getAttribute('aria-label')) ?? '')?.[1]?.replace(/,/g, ''))
    await card.click()
    await expect(page.getByRole('table', { name: 'Contracts' }).or(page.getByText(/^No contracts in this view$/))).toBeVisible()
    const rows = await page.getByRole('table', { name: 'Contracts' }).locator('tbody tr').count().catch(() => 0)
    expect(rows, label).toBe(value)
  }
})

test('CON_003 dashboard and Home show contract figures', async ({ page }) => {
  // Tests run in parallel on a possibly empty database: make sure one contract exists.
  await uploadContract(page, 'e2e-figures.pdf', expiringContractPdf(`E2E Figures ${Date.now()}`))
  await expect(page.getByText('Extracted by AI')).toBeVisible({ timeout: 20_000 })

  await page.goto('/contracts/dashboard')
  await expect(page.getByText(/^Figures as of/)).toBeVisible()
  await expect(page.getByRole('region', { name: 'Needs review' })).toBeVisible()
  await expect(page.getByRole('table', { name: 'Number of read contracts in each status' })).toBeVisible()
  await page.screenshot({ path: 'test-results/con-003-dashboard.png', fullPage: true })
  await expectNoSeriousA11yIssues(page)

  await page.goto('/')
  await expect(page.getByRole('region', { name: 'Contracts' }).getByRole('link', { name: /^In force: / })).toBeVisible()
  await expect(page.getByRole('region', { name: 'Invoices' }).getByRole('link', { name: /^Need follow-up: / })).toBeVisible()
})
