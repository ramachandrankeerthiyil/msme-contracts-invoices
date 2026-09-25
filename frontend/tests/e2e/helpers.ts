import { readFileSync } from 'node:fs'
import path from 'node:path'

import AxeBuilder from '@axe-core/playwright'
import { expect, type APIRequestContext, type Page } from '@playwright/test'

export const SAMPLES = process.env.SAMPLES_DIR ?? path.resolve(__dirname, '../../../samples')
export const sample = (name: string) => path.join(SAMPLES, name)

const XLSX = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'

/** Uploads the (freshly regenerated) sample so a spec has known data. Idempotent. */
export async function uploadSample(request: APIRequestContext, name = 'invoices-sample.xlsx') {
  const response = await request.post('/api/invoices/uploads', {
    multipart: { file: { name, mimeType: XLSX, buffer: readFileSync(sample(name)) } },
  })
  expect(response.status()).toBe(201)
}

export async function expectNoSeriousA11yIssues(page: Page) {
  const results = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa'])
    .analyze()
  const serious = results.violations.filter((v) => v.impact === 'serious' || v.impact === 'critical')
  expect(serious, JSON.stringify(serious.map((v) => [v.id, v.nodes.map((n) => n.target)]), null, 2)).toEqual([])
}

/** "Total: ₹9,94,150.75 across 9 invoices" → { amount: '₹9,94,150.75', count: 9 } */
export async function listTotal(page: Page) {
  const text = (await page.getByText(/^Total: /).textContent()) ?? ''
  const match = /Total: (₹[\d,.]+) across ([\d,]+) invoices?/.exec(text)
  expect(match, text).not.toBeNull()
  return { amount: match![1]!, count: Number(match![2]!.replace(/,/g, '')) }
}
