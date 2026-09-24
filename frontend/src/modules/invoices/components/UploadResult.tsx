import { ArrowRight, Upload } from 'lucide-react'
import { useEffect, useRef } from 'react'

import { STATUS_STYLES, StatusIcon, type StatusVariant } from '@/components/common/StatusBadge'
import { Button, ButtonLink } from '@/components/ui/button'
import { Table, TBody, Td, Th, THead, Tr } from '@/components/ui/table'
import { cn } from '@/lib/utils'

import type { UploadSummary } from '../api'
import { uploadSummaryText } from './uploadSummaryText'

interface UploadResultProps {
  summary: UploadSummary
  onUploadAnother: () => void
}

/** Result of an invoice upload (INV-001 AC9). */
export function UploadResult({ summary, onUploadAnother }: UploadResultProps) {
  const heading = useRef<HTMLHeadingElement>(null)
  const saved = summary.status === 'completed'
  const variant: StatusVariant = saved ? 'success' : 'warning'

  // Announce the result: move focus to its heading once it appears.
  useEffect(() => heading.current?.focus(), [])

  return (
    <div className="flex flex-col gap-8">
      <div className={cn('flex gap-4 rounded-lg border p-6', STATUS_STYLES[variant].badge, saved ? 'border-success' : 'border-warning')}>
        <StatusIcon variant={variant} className="size-8" />
        <div>
          <h2 ref={heading} tabIndex={-1} className="text-h2 text-text outline-none">
            {saved ? 'Upload complete' : 'No invoices were saved'}
          </h2>
          <p className="mt-1 text-text">{uploadSummaryText(summary)}</p>
          {!saved && <p className="mt-1 text-text">Please fix the rows below and upload the file again.</p>}
        </div>
      </div>

      <dl className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Stat label="New invoices" value={summary.rows_created} />
        <Stat label="Updated invoices" value={summary.rows_updated} />
        <Stat label="Replaced by a later row" value={summary.rows_overwritten} />
        <Stat label="Rows that need fixing" value={summary.rows_rejected} warn={summary.rows_rejected > 0} />
      </dl>

      {summary.rejections.length > 0 && (
        <section aria-labelledby="rejections-heading" className="flex flex-col gap-3">
          <h3 id="rejections-heading" className="text-h3">
            Rows that need fixing
          </h3>
          <p className="text-text-muted">
            Fix these rows in your spreadsheet and upload it again.
            {saved && ' All the other rows have been saved.'}
          </p>
          <Table caption="Rows that need fixing">
            <THead>
              <Tr>
                <Th numeric>Row</Th>
                <Th>Invoice number</Th>
                <Th>What&apos;s wrong</Th>
              </Tr>
            </THead>
            <TBody>
              {summary.rejections.map((rejection) => (
                <Tr key={rejection.row}>
                  <Td numeric>{rejection.row}</Td>
                  <Td>{rejection.invoice_number ?? '—'}</Td>
                  <Td>{rejection.reason}</Td>
                </Tr>
              ))}
            </TBody>
          </Table>
        </section>
      )}

      {summary.overwrites.length > 0 && (
        <details className="rounded-lg border border-border bg-surface p-4">
          <summary className="cursor-pointer font-semibold">
            Rows replaced by a later row ({summary.overwrites.length})
          </summary>
          <p className="mt-2 text-text-muted">
            These invoice numbers appeared more than once in your file. The last row was kept.
          </p>
          <ul className="mt-2 list-disc pl-6">
            {summary.overwrites.map((overwrite) => (
              <li key={overwrite.row}>
                Row {overwrite.row} replaced row {overwrite.replaced_row} ({overwrite.invoice_number})
              </li>
            ))}
          </ul>
        </details>
      )}

      <div className="flex flex-col gap-3 sm:flex-row">
        <ButtonLink to="/invoices">
          View invoices
          <ArrowRight aria-hidden />
        </ButtonLink>
        <Button variant="secondary" onClick={onUploadAnother}>
          <Upload aria-hidden />
          Upload another file
        </Button>
      </div>
    </div>
  )
}

function Stat({ label, value, warn }: { label: string; value: number; warn?: boolean }) {
  return (
    <div className={cn('rounded-lg border p-4', warn ? 'border-warning bg-warning-bg' : 'border-border bg-bg')}>
      <dt className="text-small text-text-muted">{label}</dt>
      <dd className={cn('text-h2 tabular-nums', warn && 'text-warning')}>{value.toLocaleString('en-IN')}</dd>
    </div>
  )
}
