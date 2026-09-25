import { apiFetch } from '@/lib/api/client'
import { apiUpload } from '@/lib/api/upload'

import { type InvoiceQuery, toApiParams, type View } from './query'

// Mirrors invoice-service's API (specs/invoices/module.md "API").

// --- INV-001: uploads ----------------------------------------------------------------------

export interface UploadListItem {
  id: string
  file_name: string
  uploaded_at: string
  status: 'completed' | 'no_valid_rows'
  rows_total: number
  rows_created: number
  rows_updated: number
  rows_overwritten: number
  rows_rejected: number
}

export interface Rejection {
  row: number
  invoice_number: string | null
  reason: string
}

export interface Overwrite {
  row: number
  replaced_row: number
  invoice_number: string
}

export interface UploadSummary extends UploadListItem {
  rejections: Rejection[]
  overwrites: Overwrite[]
}

export interface Page<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

export const INVOICE_FILE_TYPES = ['.xlsx']
export const INVOICE_MAX_BYTES = 10 * 1024 * 1024
export const TEMPLATE_URL = '/api/invoices/template'
export const REQUIRED_COLUMNS = [
  'Invoice Number',
  'Customer Name',
  'Date Raised',
  'Due Date',
  'Amount',
  'Paid Date',
] as const

// --- INV-002: list -------------------------------------------------------------------------

export type InvoiceStatus = 'outstanding' | 'at_risk' | 'open' | 'paid'

export interface InvoiceItem {
  id: string
  invoice_number: string
  customer_name: string
  date_raised: string
  due_date: string
  amount: string
  paid_date: string | null
  status: InvoiceStatus
  days_until_due: number | null
  record_status: 'new' | 'updated'
  record_updated_at: string | null
}

export type ViewCounts = Record<View, number>

export interface InvoicePage extends Page<InvoiceItem> {
  today: string
  total_amount: string
  counts: ViewCounts
}

// --- INV-003: dashboard --------------------------------------------------------------------

export interface ListLink {
  view: View
  due_from?: string
  due_to?: string
}

export interface TopFollowUpItem {
  id: string
  invoice_number: string
  customer_name: string
  amount: string
  due_date: string
  days_until_due: number | null
  status: InvoiceStatus
}

export interface StatusValue {
  status: InvoiceStatus
  amount: string
  count: number
}

export interface DashboardData {
  today: string
  has_data: true
  week: { start: string; end: string; anchor_uploaded_at: string }
  value_this_week: string
  invoices_this_week: number
  follow_up: { total: number; outstanding: number; at_risk: number }
  value_by_status: StatusValue[]
  top_follow_up: TopFollowUpItem[]
  links: { this_week: ListLink; follow_up: ListLink }
}

export type Dashboard = DashboardData | { today: string; has_data: false }

// --- calls ---------------------------------------------------------------------------------

export const invoiceKeys = {
  all: ['invoices'] as const,
  uploads: () => [...invoiceKeys.all, 'uploads'] as const,
  list: (query: InvoiceQuery) => [...invoiceKeys.all, 'list', query] as const,
  dashboard: () => [...invoiceKeys.all, 'dashboard'] as const,
}

export function uploadInvoices(file: File, onProgress?: (fraction: number) => void) {
  return apiUpload<UploadSummary>('/invoices/uploads', file, { onProgress })
}

export function listUploads(pageSize = 5) {
  return apiFetch<Page<UploadListItem>>(`/invoices/uploads?page_size=${pageSize}`)
}

export function listInvoices(query: InvoiceQuery) {
  return apiFetch<InvoicePage>(`/invoices?${toApiParams(query)}`)
}

export function exportUrl(query: InvoiceQuery): string {
  return `/api/invoices/export?${toApiParams(query, { paged: false })}`
}

export function getDashboard() {
  return apiFetch<Dashboard>('/invoices/dashboard')
}
