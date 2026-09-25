import { CalendarRange, Download, Search, X } from 'lucide-react'
import { useEffect, useState } from 'react'

import { Button, buttonClasses } from '@/components/ui/button'
import { formatDate, formatDateRange } from '@/lib/format'

import { exportUrl } from '../api'
import type { InvoiceQuery } from '../query'

const SEARCH_DELAY_MS = 300

interface InvoiceToolbarProps {
  query: InvoiceQuery
  onChange: (patch: Partial<InvoiceQuery>) => void
}

/** Search, "updated only", due-date range chip and export (INV-002 AC5, AC9). */
export function InvoiceToolbar({ query, onChange }: InvoiceToolbarProps) {
  const [text, setText] = useState(query.q)

  // Follow the URL when it changes elsewhere (Back button, Clear filters).
  useEffect(() => setText(query.q), [query.q])

  // Apply the search once typing pauses.
  useEffect(() => {
    if (text.trim() === query.q) return
    const timer = setTimeout(() => onChange({ q: text.trim() }), SEARCH_DELAY_MS)
    return () => clearTimeout(timer)
  }, [text, query.q, onChange])

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-col gap-4">
        <form
          role="search"
          className="flex w-full max-w-xl flex-col gap-2"
          onSubmit={(event) => {
            event.preventDefault()
            onChange({ q: text.trim() })
          }}
        >
          <label htmlFor="invoice-search" className="font-semibold">
            Search invoice number or customer
          </label>
          <div className="relative">
            <Search
              aria-hidden
              className="pointer-events-none absolute top-1/2 left-4 size-5 -translate-y-1/2 text-text-muted"
            />
            <input
              id="invoice-search"
              type="text"
              value={text}
              onChange={(event) => setText(event.target.value)}
              placeholder="e.g. INV-2606 or Deccan"
              autoComplete="off"
              className="h-12 w-full rounded-md border border-border bg-bg pr-14 pl-12 text-body placeholder:text-text-muted"
            />
            {text && (
              <button
                type="button"
                aria-label="Clear search"
                onClick={() => {
                  setText('')
                  onChange({ q: '' })
                }}
                className="absolute top-1/2 right-0.5 grid size-11 -translate-y-1/2 place-items-center rounded-md text-text-muted hover:bg-surface-strong"
              >
                <X aria-hidden className="size-5" />
              </button>
            )}
          </div>
        </form>

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
