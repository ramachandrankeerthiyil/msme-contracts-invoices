import { CalendarRange, Download, X } from 'lucide-react'

import { SearchField } from '@/components/common/SearchField'
import { Button, buttonClasses } from '@/components/ui/button'
import { formatDate, formatDateRange } from '@/lib/format'

import { exportUrl } from '../api'
import type { InvoiceQuery } from '../query'

interface InvoiceToolbarProps {
  query: InvoiceQuery
  onChange: (patch: Partial<InvoiceQuery>) => void
}

/** Search, "updated only", due-date range chip and export (INV-002 AC5, AC9). */
export function InvoiceToolbar({ query, onChange }: InvoiceToolbarProps) {
  return (
    <div className="flex flex-col gap-4">
      <SearchField
        id="invoice-search"
        label="Search invoice number or customer"
        placeholder="e.g. INV-2606 or Deccan"
        value={query.q}
        onSearch={(q) => onChange({ q })}
      />

      <div className="flex flex-wrap items-center justify-between gap-4">
        <label className="inline-flex min-h-12 cursor-pointer items-center gap-3 font-semibold">
          <input
            type="checkbox"
            checked={query.updated}
            onChange={(event) => onChange({ updated: event.target.checked })}
            className="size-6 accent-primary"
          />
          Only show updated invoices
        </label>
        <a href={exportUrl(query)} download className={buttonClasses('secondary')}>
          <Download aria-hidden />
          Export to Excel
        </a>
      </div>

      {(query.dueFrom || query.dueTo) && (
        <div className="flex flex-wrap items-center gap-3">
          <span className="inline-flex items-center gap-2 rounded-full bg-info-bg px-4 py-2 font-semibold text-info">
            <CalendarRange aria-hidden className="size-5" />
            {dueRangeLabel(query.dueFrom, query.dueTo)}
          </span>
          <Button
            variant="secondary"
            aria-label="Clear due date filter"
            onClick={() => onChange({ dueFrom: undefined, dueTo: undefined })}
          >
            <X aria-hidden />
            Clear
          </Button>
        </div>
      )}
    </div>
  )
}

function dueRangeLabel(from?: string, to?: string): string {
  if (from && to) return `Due ${formatDateRange(from, to)}`
  if (to) return `Due on or before ${formatDate(to)}`
  return `Due on or after ${formatDate(from ?? '')}`
}
