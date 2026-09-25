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

const MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September',
  'October', 'November', 'December']

/** A date `offset` days from today, written as contracts do: "27 September 2026". */
export function longDate(offset: number): string {
  const day = new Date()
  day.setDate(day.getDate() + offset)
  return `${day.getDate()} ${MONTHS[day.getMonth()]} ${day.getFullYear()}`
}

/**
 * A minimal text PDF (Helvetica, one page), so each test uploads a unique contract. Every file
 * name used with it starts with "e2e-", which scripts/e2e.sh removes afterwards.
 */
export function makePdf(lines: string[]): Buffer {
  const escape = (text: string) => text.replace(/\\/g, '\\\\').replace(/\(/g, '\\(').replace(/\)/g, '\\)')
  const stream = ['BT', '/F1 10 Tf', '14 TL', '40 800 Td', ...lines.map((l) => `(${escape(l)}) '`), 'ET'].join('\n')
  const objects = [
    '<< /Type /Catalog /Pages 2 0 R >>',
    '<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
    '<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>',
    '<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',
    `<< /Length ${Buffer.byteLength(stream)} >>\nstream\n${stream}\nendstream`,
  ]
  let pdf = '%PDF-1.4\n'
  const offsets: number[] = []
  objects.forEach((body, index) => {
    offsets.push(Buffer.byteLength(pdf))
    pdf += `${index + 1} 0 obj\n${body}\nendobj\n`
  })
  const xref = Buffer.byteLength(pdf)
  pdf += `xref\n0 ${objects.length + 1}\n0000000000 65535 f \n`
  pdf += offsets.map((offset) => `${String(offset).padStart(10, '0')} 00000 n \n`).join('')
  pdf += `trailer\n<< /Size ${objects.length + 1} /Root 1 0 R >>\nstartxref\n${xref}\n%%EOF\n`
  return Buffer.from(pdf, 'latin1')
}

/** A contract the stand-in extractor reads as: in force, ends in 2 days, one high risk. */
export function expiringContractPdf(title: string): Buffer {
  return makePdf([
    title,
    `This Agreement is made on ${longDate(-200)} between Kaveri Agro Foods Private Limited`,
    '(the "Client") and Bluewave Logistics LLP (the "Service Provider").',
    `This Agreement commences on ${longDate(-200)} and remains in force until ${longDate(2)}.`,
    'Invoices are payable within sixty (60) days of receipt.',
    'The Client shall indemnify the Service Provider against all losses without limit.',
    'Either party shall keep all information confidential during the term.',
    'This Agreement is governed by the laws of India.',
    `Reference ${title} ${Date.now()} ${Math.random()}`,
  ])
}

/** "Total: ₹9,94,150.75 across 9 invoices" → { amount: '₹9,94,150.75', count: 9 } */
export async function listTotal(page: Page) {
  const text = (await page.getByText(/^Total: /).textContent()) ?? ''
  const match = /Total: (₹[\d,.]+) across ([\d,]+) invoices?/.exec(text)
  expect(match, text).not.toBeNull()
  return { amount: match![1]!, count: Number(match![2]!.replace(/,/g, '')) }
}
