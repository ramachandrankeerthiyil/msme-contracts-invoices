import type { DashboardData, InvoiceItem, InvoicePage } from './api'

// Fixtures shaped like invoice-service responses (sample data as seen on 25 Sep 2026).

export function invoiceItem(overrides: Partial<InvoiceItem> = {}): InvoiceItem {
  return {
    id: 'id-2606',
    invoice_number: 'INV-2606',
    customer_name: 'Deccan Printing Works',
    date_raised: '2026-07-16',
    due_date: '2026-08-15',
    amount: '125000.00',
    paid_date: null,
    status: 'outstanding',
    days_until_due: -41,
    record_status: 'new',
    record_updated_at: null,
    ...overrides,
  }
}

export const INVOICE_PAGE: InvoicePage = {
  today: '2026-09-25',
  items: [
    invoiceItem(),
    invoiceItem({
      id: 'id-2611',
      invoice_number: 'INV-2611',
      customer_name: 'Bluewave Logistics LLP',
      due_date: '2026-09-25',
      amount: '76250.00',
      status: 'at_risk',
      days_until_due: 0,
      record_status: 'updated',
      record_updated_at: '2026-09-24T17:11:02Z',
    }),
    invoiceItem({
      id: 'id-2603',
      invoice_number: 'INV-2603',
      customer_name: 'Bluewave Logistics LLP',
      due_date: '2026-09-14',
      amount: '96400.00',
      paid_date: '2026-09-12',
      status: 'paid',
      days_until_due: null,
    }),
  ],
  total: 9,
  page: 1,
  page_size: 25,
  total_amount: '994150.75',
  counts: { follow_up: 9, outstanding: 5, at_risk: 4, open: 3, paid: 5, all: 17 },
}

export const EMPTY_PAGE: InvoicePage = {
  ...INVOICE_PAGE,
  items: [],
  total: 0,
  total_amount: '0.00',
  counts: { follow_up: 0, outstanding: 0, at_risk: 0, open: 0, paid: 0, all: 0 },
}

export const DASHBOARD: DashboardData = {
  today: '2026-09-25',
  has_data: true,
  week: { start: '2026-09-24', end: '2026-09-30', anchor_uploaded_at: '2026-09-24T11:41:02Z' },
  value_this_week: '557250.00',
  invoices_this_week: 6,
  follow_up: { total: 9, outstanding: 5, at_risk: 4 },
  value_by_status: [
    { status: 'outstanding', amount: '142000.00', count: 1 },
    { status: 'at_risk', amount: '396750.00', count: 4 },
    { status: 'open', amount: '0.00', count: 0 },
    { status: 'paid', amount: '18500.00', count: 1 },
  ],
  top_follow_up: [
    {
      id: 'id-2606',
      invoice_number: 'INV-2606',
      customer_name: 'Deccan Printing Works',
      amount: '125000.00',
      due_date: '2026-08-15',
      days_until_due: -41,
      status: 'outstanding',
    },
  ],
  links: {
    this_week: { view: 'all', due_from: '2026-09-24', due_to: '2026-09-30' },
    follow_up: { view: 'follow_up', due_to: '2026-09-30' },
  },
}
