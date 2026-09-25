import { useQueryClient } from '@tanstack/react-query'
import { ArrowRight, FileText, Info, Upload } from 'lucide-react'
import { useState } from 'react'
import { useNavigate } from 'react-router'

import { PageHeader } from '@/app/layout/PageHeader'
import { ErrorAlert } from '@/components/common/ErrorAlert'
import { FileDropzone } from '@/components/common/FileDropzone'
import { Button, ButtonLink } from '@/components/ui/button'
import { ApiError } from '@/lib/api/client'
import { formatFileSize } from '@/lib/format'

import { CONTRACT_FILE_TYPES, CONTRACT_MAX_BYTES, contractKeys, uploadContract } from '../api'

type Phase =
  | { kind: 'choose' }
  | { kind: 'selected'; file: File; error?: unknown }
  | { kind: 'uploading'; file: File; progress: number }

/** Upload a contract (CON-001 AC1, AC3a, AC8). The detail page then shows the reading progress. */
export function UploadContractPage() {
  const [phase, setPhase] = useState<Phase>({ kind: 'choose' })
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  async function upload(file: File) {
    setPhase({ kind: 'uploading', file, progress: 0 })
    try {
      const accepted = await uploadContract(file, (progress) =>
        setPhase((current) => (current.kind === 'uploading' ? { ...current, progress } : current)),
      )
      void queryClient.invalidateQueries({ queryKey: contractKeys.all })
      navigate(`/contracts/${accepted.id}`)
    } catch (error) {
      setPhase({ kind: 'selected', file, error })
    }
  }

  return (
    <>
      <PageHeader description="We read the contract and pick out what matters for your business." />
      <section className="flex flex-col gap-6 rounded-lg border border-border bg-bg p-6 shadow-card sm:p-8">
        <div className="flex flex-col gap-3">
          <h2 className="text-h2">Choose your contract</h2>
          <ol className="flex flex-col gap-1 text-text-muted">
            <li>1. We read the contract.</li>
            <li>2. We pick out the parties, key dates, terms and risks.</li>
            <li>3. You see the results — usually in under a minute.</li>
          </ol>
        </div>

        {phase.kind === 'choose' ? (
          <FileDropzone
            accept={CONTRACT_FILE_TYPES}
            acceptLabel="a PDF or Word (.docx) file"
            maxBytes={CONTRACT_MAX_BYTES}
            title="Drag your contract here"
            helpText="PDF or Word (.docx), up to 20 MB"
            onFile={(file) => setPhase({ kind: 'selected', file })}
          />
        ) : (
          <SelectedContract
            file={phase.file}
            uploading={phase.kind === 'uploading'}
            progress={phase.kind === 'uploading' ? phase.progress : 0}
            error={phase.kind === 'selected' ? phase.error : undefined}
            onUpload={() => void upload(phase.file)}
            onChooseAnother={() => setPhase({ kind: 'choose' })}
          />
        )}
      </section>
    </>
  )
}

interface SelectedContractProps {
  file: File
  uploading: boolean
  progress: number
  error?: unknown
  onUpload: () => void
  onChooseAnother: () => void
}

function SelectedContract({ file, uploading, progress, error, onUpload, onChooseAnother }: SelectedContractProps) {
  const percent = Math.round(progress * 100)
  const duplicate = error instanceof ApiError && error.code === 'DUPLICATE_CONTRACT' ? error : undefined
  const existingId = duplicate?.details.contract_id as string | undefined

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-4 rounded-lg border border-border bg-surface p-5 sm:flex-row sm:items-center">
        <FileText aria-hidden className="size-10 shrink-0 text-primary" />
        <div className="min-w-0 flex-1">
          <p className="truncate font-semibold">{file.name}</p>
          <p className="text-small text-text-muted">{formatFileSize(file.size)}</p>
        </div>
        {!uploading && !duplicate && (
          <div className="flex flex-col gap-3 sm:flex-row">
            <Button onClick={onUpload}>
              <Upload aria-hidden />
              Upload contract
            </Button>
            <Button variant="secondary" onClick={onChooseAnother}>
              Choose a different file
            </Button>
          </div>
        )}
      </div>

      {uploading && (
        <div aria-live="polite">
          <p className="font-semibold">Uploading… {percent}%</p>
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

      {duplicate ? (
        <div role="alert" className="flex gap-4 rounded-lg border border-info bg-info-bg p-6">
          <Info aria-hidden className="size-7 shrink-0 text-info" />
          <div className="flex flex-col gap-3">
            <p className="text-h3 text-text">{duplicate.message}</p>
            <div className="flex flex-col gap-3 sm:flex-row">
              {existingId && (
                <ButtonLink to={`/contracts/${existingId}`}>
                  Open the existing contract
                  <ArrowRight aria-hidden />
                </ButtonLink>
              )}
              <Button variant="secondary" onClick={onChooseAnother}>
                Choose a different file
              </Button>
            </div>
          </div>
        </div>
      ) : (
        error !== undefined && <ErrorAlert error={error} title="We couldn't use this file" />
      )}
    </div>
  )
}
