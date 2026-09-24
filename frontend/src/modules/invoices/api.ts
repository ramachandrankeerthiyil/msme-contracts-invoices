import { apiFetch } from '@/lib/api/client'
import { apiUpload } from '@/lib/api/upload'

// Mirrors invoice-service's API (specs/invoices/module.md "API").

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

export const invoiceKeys = {
  all: ['invoices'] as const,
  uploads: () => [...invoiceKeys.all, 'uploads'] as const,
}

export function uploadInvoices(file: File, onProgress?: (fraction: number) => void) {
  return apiUpload<UploadSummary>('/invoices/uploads', file, { onProgress })
}

export function listUploads(pageSize = 5) {
  return apiFetch<Page<UploadListItem>>(`/invoices/uploads?page_size=${pageSize}`)
}
