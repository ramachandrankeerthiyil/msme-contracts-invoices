import { expect, test, type Page } from '@playwright/test'

import { expectNoSeriousA11yIssues, uploadSample } from './helpers'

// "Talk to Me" (AST-001) against the running stack. scripts/e2e.sh starts the assistant with the
// deterministic stand-in model (ASSISTANT_LLM=fake): real lookups, no Claude API calls.

const box = (page: Page) =>
  page.getByRole('textbox', { name: 'Ask a question about your contracts or invoices' })
// The stand-in writes word by word (so Stop can be tested); a long table takes several seconds.
const ANSWER_MS = 30_000
const answers = (page: Page) => page.getByRole('article', { name: "Talk to Me's answer" })

test.beforeEach(async ({ page, request }) => {
  test.setTimeout(90_000)
  await uploadSample(request)
  await page.goto('/assistant')
})

test('AST-001 AC1-AC7, AC9, AC11, AC13, AC16: suggestion, streamed answer with links, follow-up', async ({
  page,
}) => {
  await expect(page.getByRole('heading', { level: 1, name: 'Talk to Me' })).toBeVisible()
  await expect(page.getByText('Talk to Me can make mistakes.', { exact: false })).toBeVisible()
  await expectNoSeriousA11yIssues(page)

  await page.getByRole('button', { name: 'Which invoices are unpaid as of today?' }).click()

  const first = answers(page).first()
  await expect(first.getByText(/Checked unpaid invoices \(\d+\)/)).toBeVisible()
  await expect(first.getByText(/You have \d+ invoices worth ₹[\d,]+\.\d\d/)).toBeVisible()
  await expect(page.getByRole('button', { name: 'Copy answer' })).toBeVisible({ timeout: ANSWER_MS })
  await expect(page.getByRole('status')).toContainText('Answer ready.')
  await expect(box(page)).toBeFocused()
  await expectNoSeriousA11yIssues(page)

  // A follow-up keeps the conversation.
  await box(page).fill('What risks are in the Bluewave contract?')
  await box(page).press('Enter')
  const second = answers(page).nth(1)
  await expect(second.getByText('Read “', { exact: false })).toBeVisible()
  await expect(second.getByText('not legal advice', { exact: false })).toBeVisible({ timeout: ANSWER_MS })
  await expect(page.getByRole('log').getByText('Which invoices are unpaid as of today?')).toBeVisible()

  // Links open the record inside the app.
  const invoiceLink = first.getByRole('link').first()
  const number = await invoiceLink.textContent()
  await invoiceLink.click()
  await expect(page).toHaveURL(/\/invoices\?view=all&q=INV-/)
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('All invoices')
  await expect(page.getByRole('cell', { name: number ?? '' })).toBeVisible()

  // Back again: the conversation is still there (sessionStorage, AC8).
  await page.goBack()
  await expect(answers(page)).toHaveCount(2)
})

test('AST-001 AC4: Stop keeps the partial answer', async ({ page }) => {
  await box(page).fill('Which invoices are unpaid as of today?')
  await page.getByRole('button', { name: 'Send' }).click()
  await expect(answers(page).getByText('You have', { exact: false })).toBeVisible()

  await page.getByRole('button', { name: 'Stop' }).click()

  await expect(answers(page).getByText('(stopped)')).toBeVisible()
  await expect(page.getByRole('button', { name: 'Send' })).toBeVisible()
})

test('AST-001 AC8, AC10: refresh keeps the conversation; New conversation clears it', async ({ page }) => {
  await box(page).fill('Please mark INV-2601 as paid')
  await box(page).press('Enter')
  await expect(answers(page).getByText("can't change anything", { exact: false })).toBeVisible({ timeout: ANSWER_MS })

  await page.reload()
  await expect(answers(page)).toHaveCount(1)

  await page.getByRole('button', { name: 'New conversation' }).click()
  await expect(page.getByRole('heading', { name: 'How can I help today?' })).toBeVisible()
  await page.reload()
  await expect(answers(page)).toHaveCount(0)
})

test('AST-001 AC13: usable at phone width', async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 812 })
  await page.getByRole('button', { name: 'What is due this week?' }).click()
  await expect(answers(page).getByRole('button', { name: 'Copy answer' })).toBeVisible({ timeout: ANSWER_MS })

  const composer = box(page)
  await expect(composer).toBeInViewport()
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth)
  expect(overflow).toBe(false)
  await expectNoSeriousA11yIssues(page)
})
