import { useQueryClient } from '@tanstack/react-query'
import { Download, FileSpreadsheet, LoaderCircle, Upload } from 'lucide-react'
import { useState } from 'react'

import { PageHeader } from '@/app/layout/PageHeader'
import { ErrorAlert } from '@/components/common/ErrorAlert'
import { FileDropzone } from '@/components/common/FileDropzone'
import { Button, buttonClasses } from '@/components/ui/button'
import { formatFileSize } from '@/lib/format'

import {
  INVOICE_FILE_TYPES,
  INVOICE_MAX_BYTES,
  invoiceKeys,
  OPTIONAL_COLUMNS,
  REQUIRED_COLUMNS,
  TEMPLATE_URL,
  uploadInvoices,
  type UploadSummary,
} from '../api'
import { RecentUploads } from '../components/RecentUploads'
import { UploadResult } from '../components/UploadResult'

type Phase =
  | { kind: 'choose' }
  | { kind: 'selected'; file: File; error?: unknown }
  | { kind: 'uploading'; file: File; progress: number }
  | { kind: 'done'; summary: UploadSummary }

/** Upload invoices (INV-001): choose → selected → uploading → result. */
export function UploadInvoicesPage() {
  const [phase, setPhase] = useState<Phase>({ kind: 'choose' })
  const queryClient = useQueryClient()

  async function upload(file: File) {
    setPhase({ kind: 'uploading', file, progress: 0 })
    try {
      const summary = await uploadInvoices(file, (progress) =>
        setPhase((current) => (current.kind === 'uploading' ? { ...current, progress } : current)),
      )
      setPhase({ kind: 'done', summary })
      void queryClient.invalidateQueries({ queryKey: invoiceKeys.all })
    } catch (error) {
      setPhase({ kind: 'selected', file, error })
    }
  }

  return (
    <>
      <PageHeader description="Add new invoices or update existing ones from your Excel spreadsheet." />
      <div className="flex flex-col gap-10">
        <section className="rounded-lg border border-border bg-bg p-6 shadow-card sm:p-8">
          {phase.kind === 'done' ? (
            <UploadResult summary={phase.summary} onUploadAnother={() => setPhase({ kind: 'choose' })} />
          ) : (
            <div className="flex flex-col gap-6">
              <FileRequirements />
              {phase.kind === 'choose' ? (
                <FileDropzone
                  accept={INVOICE_FILE_TYPES}
                  acceptLabel="an Excel file (.xlsx)"
                  maxBytes={INVOICE_MAX_BYTES}
                  title="Drag your Excel file here"
                  helpText="Excel (.xlsx), up to 10 MB."
                  onFile={(file) => setPhase({ kind: 'selected', file })}
                />
              ) : (
                <SelectedFile
                  file={phase.file}
                  uploading={phase.kind === 'uploading'}
                  progress={phase.kind === 'uploading' ? phase.progress : 0}
                  error={phase.kind === 'selected' ? phase.error : undefined}
                  onUpload={() => void upload(phase.file)}
                  onChooseAnother={() => setPhase({ kind: 'choose' })}
                />
              )}
            </div>
          )}
        </section>
        <RecentUploads />
      </div>
    </>
  )
}

function FileRequirements() {
  return (
    <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
      <div>
        <h2 className="text-h2">Choose your invoice file</h2>
        <p className="mt-2 text-text-muted">Your spreadsheet needs these columns on its first sheet:</p>
        <ul className="mt-3 flex flex-wrap gap-2" aria-label="Required columns">
          {REQUIRED_COLUMNS.map((column) => (
            <li key={column} className="rounded-full bg-info-bg px-3 py-1 text-small font-semibold text-info">
              {column}
              {column === 'Paid Date' && ' (leave blank if unpaid)'}
            </li>
          ))}
        </ul>
        <p className="mt-4 text-text-muted">Optional:</p>
        <ul className="mt-2 flex flex-wrap gap-2" aria-label="Optional columns">
          {OPTIONAL_COLUMNS.map((column) => (
            <li key={column} className="rounded-full bg-surface-strong px-3 py-1 text-small font-semibold text-text">
              {column} (needed to send email reminders)
            </li>
          ))}
        </ul>
      </div>
      <a href={TEMPLATE_URL} download className={buttonClasses('secondary', 'self-start')}>
        <Download aria-hidden />
        Download template
      </a>
    </div>
  )
}

interface SelectedFileProps {
  file: File
  uploading: boolean
  progress: number
  error?: unknown
  onUpload: () => void
  onChooseAnother: () => void
}

function SelectedFile({ file, uploading, progress, error, onUpload, onChooseAnother }: SelectedFileProps) {
  const percent = Math.round(progress * 100)
  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-4 rounded-lg border border-border bg-surface p-5 sm:flex-row sm:items-center">
        <FileSpreadsheet aria-hidden className="size-10 shrink-0 text-primary" />
        <div className="min-w-0 flex-1">
          <p className="truncate font-semibold">{file.name}</p>
          <p className="text-small text-text-muted">{formatFileSize(file.size)}</p>
        </div>
        {!uploading && (
          <div className="flex flex-col gap-3 sm:flex-row">
            <Button onClick={onUpload}>
              <Upload aria-hidden />
              Upload invoices
            </Button>
            <Button variant="secondary" onClick={onChooseAnother}>
              Choose a different file
            </Button>
          </div>
        )}
      </div>

      {uploading && (
        <div aria-live="polite">
          <p className="flex items-center gap-3 font-semibold">
            {percent >= 100 ? (
              <>
                <LoaderCircle aria-hidden className="size-5 animate-spin text-primary" />
                Checking your invoices…
              </>
            ) : (
              `Uploading… ${percent}%`
            )}
          </p>
          <div
            role="progressbar"
            aria-label="Upload progress"
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuenow={percent}
            className="mt-3 h-3 w-full overflow-hidden rounded-full bg-surface-strong"
          >
            <div className="h-full rounded-full bg-primary transition-all" style={{ width: `${percent}%` }} />
          </div>
        </div>
      )}

      {error !== undefined && <ErrorAlert error={error} title="We couldn't use this file" />}
    </div>
  )
}
