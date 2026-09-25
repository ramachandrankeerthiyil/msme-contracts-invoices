import { ChevronLeft, ChevronRight } from 'lucide-react'

import { Button } from '@/components/ui/button'

interface PaginationProps {
  page: number
  pageSize: number
  total: number
  onPage: (page: number) => void
}

/** "Showing 1–25 of 140" with Previous / Next (ui-design-system.md "Data table"). */
export function Pagination({ page, pageSize, total, onPage }: PaginationProps) {
  if (total === 0) return null
  const first = (page - 1) * pageSize + 1
  const last = Math.min(page * pageSize, total)
  const pages = Math.ceil(total / pageSize)

  return (
    <nav aria-label="Pagination" className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
      <p className="text-text-muted">
        Showing {first.toLocaleString('en-IN')}–{last.toLocaleString('en-IN')} of{' '}
        {total.toLocaleString('en-IN')}
      </p>
      {pages > 1 && (
        <div className="flex gap-3">
          <Button variant="secondary" disabled={page <= 1} onClick={() => onPage(page - 1)}>
            <ChevronLeft aria-hidden />
            Previous
          </Button>
          <Button variant="secondary" disabled={page >= pages} onClick={() => onPage(page + 1)}>
            Next
            <ChevronRight aria-hidden />
          </Button>
        </div>
      )}
    </nav>
  )
}
