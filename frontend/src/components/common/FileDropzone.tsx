import { CloudUpload, FolderOpen, OctagonAlert } from 'lucide-react'
import { useRef, useState, type DragEvent } from 'react'

import { Button } from '@/components/ui/button'
import { formatFileSize } from '@/lib/format'
import { cn } from '@/lib/utils'

interface FileDropzoneProps {
  /** Accepted extensions, e.g. ['.xlsx']. */
  accept: string[]
  /** How accepted types are described to users, e.g. 'an Excel file (.xlsx)'. */
  acceptLabel: string
  maxBytes: number
  title: string
  helpText: string
  onFile: (file: File) => void
  disabled?: boolean
}

/**
 * Drag-and-drop area plus a "Choose file" button (INV-001 AC1, reused by CON-001). The same
 * type and size checks as the API run before upload, with the same plain-language messages.
 */
export function FileDropzone({
  accept,
  acceptLabel,
  maxBytes,
  title,
  helpText,
  onFile,
  disabled,
}: FileDropzoneProps) {
  const input = useRef<HTMLInputElement>(null)
  const [dragging, setDragging] = useState(false)
  const [error, setError] = useState<string>()

  function handle(file: File) {
    const dot = file.name.lastIndexOf('.')
    const extension = dot >= 0 ? file.name.slice(dot).toLowerCase() : ''
    if (!accept.includes(extension)) {
      setError(`This file type isn't supported. Please choose ${acceptLabel}.`)
      return
    }
    if (file.size > maxBytes) {
      setError(`This file is larger than ${formatFileSize(maxBytes)}. Please choose a smaller file.`)
      return
    }
    setError(undefined)
    onFile(file)
  }

  function onDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault()
    setDragging(false)
    const file = event.dataTransfer.files[0]
    if (file && !disabled) handle(file)
  }

  return (
    <div className="flex flex-col gap-4">
      <div
        onDragOver={(event) => {
          event.preventDefault()
          setDragging(true)
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        className={cn(
          'flex flex-col items-center gap-3 rounded-lg border-2 border-dashed px-6 py-10 text-center transition-colors',
          dragging ? 'border-primary bg-primary-soft' : 'border-border bg-surface',
        )}
      >
        <span className="grid size-16 place-items-center rounded-full bg-primary-soft text-primary">
          <CloudUpload aria-hidden className="size-8" />
        </span>
        <p className="text-h3">{title}</p>
        <p className="text-text-muted">or</p>
        <Button variant="secondary" disabled={disabled} onClick={() => input.current?.click()}>
          <FolderOpen aria-hidden />
          Choose file
        </Button>
        <p className="text-small text-text-muted">{helpText}</p>
        <input
          ref={input}
          type="file"
          hidden
          accept={accept.join(',')}
          data-testid="file-input"
          onChange={(event) => {
            const file = event.target.files?.[0]
            if (file) handle(file)
            event.target.value = ''
          }}
        />
      </div>
      {error && (
        <p role="alert" className="flex items-start gap-2 font-semibold text-danger">
          <OctagonAlert aria-hidden className="mt-1 size-5 shrink-0" />
          {error}
        </p>
      )}
    </div>
  )
}
