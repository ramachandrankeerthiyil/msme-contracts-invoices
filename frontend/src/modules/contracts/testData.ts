import type { ContractDetail, ContractListItem, ContractPage, DashboardData } from './api'

// Fixtures shaped like contract-service responses (today = 25 Sep 2026).

export function contractItem(overrides: Partial<ContractListItem> = {}): ContractListItem {
  return {
    id: 'c-msa',
    title: 'Master Services Agreement',
    file_name: 'contract-msa-bluewave.docx',
    parties: ['Kaveri Agro Foods Private Limited', 'Bluewave Logistics LLP'],
    start_date: '2025-10-02',
    end_date: '2026-09-27',
    days_until_end: 2,
    lifecycle: 'in_force',
    at_risk: true,
    at_risk_reasons: ['Expires in 2 days', '4 high risks'],
    high_risk_count: 4,
    uploaded_at: '2026-09-25T10:00:00Z',
    processing_status: 'completed',
    ...overrides,
  }
}

export const CONTRACT_PAGE: ContractPage = {
  today: '2026-09-25',
  items: [
    contractItem(),
    contractItem({
      id: 'c-supply',
      title: 'Supply Agreement',
      file_name: 'contract-supply-sharma.docx',
      parties: ['Sharma Textiles Private Limited', 'Deccan Printing Works'],
      start_date: '2026-04-02',
      end_date: '2027-04-02',
      days_until_end: 189,
      at_risk: false,
      at_risk_reasons: [],
      high_risk_count: 0,
    }),
  ],
  total: 2,
  page: 1,
  page_size: 25,
  counts: { all: 2, in_force: 2, at_risk: 1, not_started: 0, expired: 0, no_end_date: 0, processing: 1, failed: 0 },
}

export const EMPTY_CONTRACTS: ContractPage = {
  ...CONTRACT_PAGE,
  items: [],
  total: 0,
  counts: { all: 0, in_force: 0, at_risk: 0, not_started: 0, expired: 0, no_end_date: 0, processing: 0, failed: 0 },
}

export function contractDetail(overrides: Partial<ContractDetail> = {}): ContractDetail {
  return {
    today: '2026-09-25',
    id: 'c-msa',
    title: 'Master Services Agreement',
    file_name: 'contract-msa-bluewave.docx',
    file_type: 'docx',
    uploaded_at: '2026-09-25T10:00:00Z',
    processing_status: 'completed',
    error_message: null,
    lifecycle: 'in_force',
    at_risk: true,
    at_risk_reasons: ['Expires in 2 days', '1 high risk'],
    high_risk_count: 1,
    start_date: '2025-10-02',
    end_date: '2026-09-27',
    days_until_end: 2,
    summary: 'Cold-chain logistics for packaged foods.',
    parties: [
      { name: 'Kaveri Agro Foods Private Limited', role: 'Client' },
      { name: 'Bluewave Logistics LLP', role: 'Service Provider' },
    ],
    key_dates: [
      { label: 'Start', date: '2025-10-02', days_from_today: -358, source_text: '2 October 2025', source_verified: true },
      { label: 'Expiry', date: '2026-09-27', days_from_today: 2, source_text: '27 September 2026', source_verified: true },
    ],
    terms: [
      { category: 'payment', summary: 'Invoices payable within 60 days', source_text: 'payable within sixty (60) days', source_verified: true },
      { category: 'termination', summary: 'Provider may leave on 7 days notice', source_text: 'by giving seven (7) days', source_verified: false },
    ],
    risks: [
      { severity: 'medium', title: 'Auto-renewal', description: 'Renews for 2 years unless you give notice.', source_text: 'shall automatically renew', source_verified: true },
      { severity: 'high', title: 'Unlimited indemnity', description: 'You cover all their losses, without limit.', source_text: 'without limit', source_verified: true },
    ],
    extraction_model: 'claude-sonnet-5',
    processed_at: '2026-09-25T10:00:40Z',
    ...overrides,
  }
}

export const CONTRACT_DASHBOARD: DashboardData = {
  today: '2026-09-25',
  has_data: true,
  counts: { total: 2, in_force: 2, at_risk: 1, expired: 0, not_started: 0, no_end_date: 0 },
  at_risk_breakdown: { expiring_soon: 1, high_risk: 1 },
  by_lifecycle: [
    { lifecycle: 'in_force', count: 2 },
    { lifecycle: 'not_started', count: 0 },
    { lifecycle: 'no_end_date', count: 0 },
    { lifecycle: 'expired', count: 0 },
  ],
  needs_attention: [contractItem()],
  unread: { processing: 1, failed: 1 },
  links: {
    total: { view: 'all' },
    in_force: { view: 'in_force' },
    at_risk: { view: 'at_risk' },
    expired: { view: 'expired' },
    not_started: { view: 'not_started' },
    no_end_date: { view: 'no_end_date' },
    processing: { view: 'processing' },
    failed: { view: 'failed' },
  },
}
