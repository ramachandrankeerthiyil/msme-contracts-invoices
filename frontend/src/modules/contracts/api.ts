import { apiFetch } from '@/lib/api/client'
import { apiUpload } from '@/lib/api/upload'

import { type ContractQuery, toApiParams, type View } from './query'

// Mirrors contract-service's API (specs/contracts, CON-001 … CON-003).

export type Lifecycle = 'in_force' | 'not_started' | 'no_end_date' | 'expired' | 'processing' | 'failed'
export type ProcessingStatus = 'uploaded' | 'extracting_text' | 'analysing' | 'completed' | 'failed'
export type Severity = 'high' | 'medium' | 'low'
export type TermCategory =
  | 'payment'
  | 'termination'
  | 'renewal'
  | 'liability'
  | 'confidentiality'
  | 'governing_law'
  | 'other'

export interface ContractListItem {
  id: string
  title: string
  file_name: string
  parties: string[]
  start_date: string | null
  end_date: string | null
  days_until_end: number | null
  lifecycle: Lifecycle
  at_risk: boolean
  at_risk_reasons: string[]
  high_risk_count: number
  uploaded_at: string
  processing_status: ProcessingStatus
}

export type ViewCounts = Record<View, number>

export interface ContractPage {
  today: string
  items: ContractListItem[]
  total: number
  page: number
  page_size: number
  counts: ViewCounts
}

interface Quoted {
  source_text: string
  source_verified: boolean
}

export interface ContractDetail {
  today: string
  id: string
  title: string
  file_name: string
  file_type: 'pdf' | 'docx'
  uploaded_at: string
  processing_status: ProcessingStatus
  error_message: string | null
  lifecycle: Lifecycle
  at_risk: boolean
  at_risk_reasons: string[]
  high_risk_count: number
  start_date: string | null
  end_date: string | null
  days_until_end: number | null
  summary: string | null
  parties: { name: string; role: string }[]
  key_dates: ({ label: string; date: string; days_from_today: number } & Quoted)[]
  terms: ({ category: TermCategory; summary: string } & Quoted)[]
  risks: ({ severity: Severity; title: string; description: string } & Quoted)[]
  extraction_model: string | null
  processed_at: string | null
}

export interface DashboardData {
  today: string
  has_data: true
  counts: { total: number; in_force: number; at_risk: number; expired: number; not_started: number; no_end_date: number }
  at_risk_breakdown: { expiring_soon: number; high_risk: number }
  by_lifecycle: { lifecycle: Lifecycle; count: number }[]
  needs_attention: ContractListItem[]
  unread: { processing: number; failed: number }
  links: Record<string, { view: View }>
}

export type Dashboard = DashboardData | { today: string; has_data: false }

export const CONTRACT_FILE_TYPES = ['.pdf', '.docx']
export const CONTRACT_MAX_BYTES = 20 * 1024 * 1024

export const contractKeys = {
  all: ['contracts'] as const,
  list: (query: ContractQuery) => [...contractKeys.all, 'list', query] as const,
  detail: (id: string) => [...contractKeys.all, 'detail', id] as const,
  dashboard: () => [...contractKeys.all, 'dashboard'] as const,
}

export function isProcessing(status: ProcessingStatus | undefined): boolean {
  return status === 'uploaded' || status === 'extracting_text' || status === 'analysing'
}

export function listContracts(query: ContractQuery) {
  return apiFetch<ContractPage>(`/contracts?${toApiParams(query)}`)
}

export function getContract(id: string) {
  return apiFetch<ContractDetail>(`/contracts/${encodeURIComponent(id)}`)
}

export function getDashboard() {
  return apiFetch<Dashboard>('/contracts/dashboard')
}

export function uploadContract(file: File, onProgress?: (fraction: number) => void) {
  return apiUpload<{ id: string; processing_status: ProcessingStatus }>('/contracts/uploads', file, {
    onProgress,
  })
}

export function retryContract(id: string) {
  return apiFetch<{ id: string; processing_status: ProcessingStatus }>(
    `/contracts/${encodeURIComponent(id)}/retry`,
    { method: 'POST' },
  )
}

export function fileUrl(id: string): string {
  return `/api/contracts/${encodeURIComponent(id)}/file`
}
