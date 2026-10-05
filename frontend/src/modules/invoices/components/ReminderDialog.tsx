import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Mail, OctagonAlert } from 'lucide-react'
import { type FormEvent, type ReactNode, type RefObject, useEffect, useRef, useState } from 'react'

import { ErrorAlert } from '@/components/common/ErrorAlert'
import { InlineAlert } from '@/components/common/InlineAlert'
import { Button, ButtonLink } from '@/components/ui/button'
import { Dialog, DialogContent } from '@/components/ui/dialog'
import { Skeleton } from '@/components/ui/skeleton'
import { ApiError } from '@/lib/api/client'
import { formatDate, formatINR } from '@/lib/format'
import { cn } from '@/lib/utils'

import { getReminderDraft, type InvoiceItem, invoiceKeys, type ReminderDraft, sendReminder } from '../api'
import { noEmailMessage, type ReminderErrors, validateReminder } from '../reminder'
import { invoiceDueHint } from '../status'

const INPUT = 'w-full rounded-md border bg-bg text-body'

function isNotRemindable(error: unknown): error is ApiError {
  return error instanceof ApiError && error.code === 'INVOICE_NOT_REMINDABLE'
}

interface ReminderDialogProps {
  /** The invoice being reminded, or null when the dialog is closed. */
  invoice: InvoiceItem | null
  onClose: () => void
  /** The button that opened the dialog: it gets focus back when the dialog closes (AC13). */
  returnFocusRef: RefObject<HTMLElement | null>
}

/**
 * Review and send a payment reminder (INV-004). Opening it only fetches a draft; nothing is sent
 * until the user clicks "Send reminder".
 */
export function ReminderDialog({ invoice, onClose, returnFocusRef }: ReminderDialogProps) {
  const [sending, setSending] = useState(false)

  return (
    <Dialog
      open={invoice !== null}
      onOpenChange={(open) => {
        if (!open && !sending) onClose()
      }}
    >
      {invoice && (
        <DialogContent
          title="Send email reminder"
          description={`${invoice.invoice_number} · ${invoice.customer_name} · ${formatINR(invoice.amount)} · ${invoiceDueHint(invoice)}`}
          locked={sending}
          onCloseAutoFocus={(event) => {
            event.preventDefault()
            returnFocusRef.current?.focus()
          }}
        >
          <ReminderBody invoice={invoice} onClose={onClose} onSendingChange={setSending} />
        </DialogContent>
      )}
    </Dialog>
  )
}

interface BodyProps {
  invoice: InvoiceItem
  onClose: () => void
  onSendingChange: (sending: boolean) => void
}

function useRefreshInvoiceList() {
  const queryClient = useQueryClient()
  return () => queryClient.invalidateQueries({ queryKey: [...invoiceKeys.all, 'list'] })
}

function ReminderBody({ invoice, onClose, onSendingChange }: BodyProps) {
  const refreshList = useRefreshInvoiceList()
  // Always a fresh draft, so "days overdue" is current and a paid invoice is noticed (AC9).
  const draft = useQuery({
    queryKey: invoiceKeys.reminderDraft(invoice.id),
    queryFn: () => getReminderDraft(invoice.id),
    gcTime: 0,
    staleTime: 0,
    refetchOnMount: 'always',
  })
  const stale = isNotRemindable(draft.error)

  useEffect(() => {
    if (stale) void refreshList()
    // eslint-disable-next-line react-hooks/exhaustive-deps -- refresh once when this is first seen
  }, [stale])

  if (draft.isPending) return <DraftSkeleton />
  if (stale) return <NoReminderSent error={draft.error} onClose={onClose} />
  if (draft.isError) {
    return (
      <div className="flex flex-col gap-6">
        <ErrorAlert
          error={draft.error}
          title="We couldn't prepare the reminder"
          onRetry={() => void draft.refetch()}
        />
        <Footer>
          <Button variant="secondary" onClick={onClose}>
            Close
          </Button>
        </Footer>
      </div>
    )
  }
  if (draft.data.to === null) return <NoEmailOnFile customerName={draft.data.customer_name} onClose={onClose} />
  return (
    <ReminderEditor invoice={invoice} draft={draft.data} onClose={onClose} onSendingChange={onSendingChange} />
  )
}

function DraftSkeleton() {
  return (
    <div className="flex flex-col gap-4" aria-busy="true" aria-label="Preparing your reminder">
      <Skeleton className="h-12 w-full" />
      <Skeleton className="h-12 w-full" />
      <Skeleton className="h-64 w-full" />
    </div>
  )
}

function Footer({ children }: { children: ReactNode }) {
  return <div className="flex flex-wrap gap-3">{children}</div>
}

/** AC9: the invoice is no longer overdue (paid, or otherwise changed), so nothing can be sent. */
function NoReminderSent({ error, onClose }: { error: unknown; onClose: () => void }) {
  return (
    <div className="flex flex-col gap-6">
      <ErrorAlert error={error} title="No reminder sent" />
      <Footer>
        <Button variant="secondary" onClick={onClose}>
          Close
        </Button>
      </Footer>
    </div>
  )
}

/** AC6: no address in the sheet, so there is nobody to send to. */
function NoEmailOnFile({ customerName, onClose }: { customerName: string; onClose: () => void }) {
  return (
    <div className="flex flex-col gap-6">
      <InlineAlert variant="info" title="No email address on file">
        <p>{noEmailMessage(customerName)}</p>
      </InlineAlert>
      <Footer>
        <ButtonLink to="/invoices/upload">Upload invoices</ButtonLink>
        <Button variant="secondary" onClick={onClose}>
          Close
        </Button>
      </Footer>
    </div>
  )
}

interface EditorProps extends BodyProps {
  draft: ReminderDraft
}

function ReminderEditor({ invoice, draft, onClose, onSendingChange }: EditorProps) {
  const refreshList = useRefreshInvoiceList()
  const [subject, setSubject] = useState(draft.subject)
  const [message, setMessage] = useState(draft.message)
  const [errors, setErrors] = useState<ReminderErrors>({})
  const subjectRef = useRef<HTMLInputElement>(null)
  const messageRef = useRef<HTMLTextAreaElement>(null)
  const sentRef = useRef<HTMLDivElement>(null)

  const mutation = useMutation({
    mutationFn: () => sendReminder(invoice.id, { subject: subject.trim(), message: message.trim() }),
    onSuccess: () => void refreshList(),
    onError: (error) => {
      if (isNotRemindable(error)) void refreshList()
    },
  })

  useEffect(() => {
    onSendingChange(mutation.isPending)
    return () => onSendingChange(false)
  }, [mutation.isPending, onSendingChange])

  // The form disappears on success, so move focus to the confirmation (AC13).
  useEffect(() => {
    if (mutation.isSuccess) sentRef.current?.focus()
  }, [mutation.isSuccess])

  function submit(event: FormEvent) {
    event.preventDefault()
    if (mutation.isPending) return
    const found = validateReminder({ subject, message })
    setErrors(found)
    if (found.subject) subjectRef.current?.focus()
    else if (found.message) messageRef.current?.focus()
    else mutation.mutate()
  }

  if (mutation.isSuccess) {
    return (
      <div ref={sentRef} tabIndex={-1} className="flex flex-col gap-6 outline-none">
        <InlineAlert variant="success" role="status" title={`Reminder sent to ${mutation.data.to}`}>
          <p>Your client will receive it shortly. You can close this window.</p>
        </InlineAlert>
        <Footer>
          <Button onClick={onClose}>Close</Button>
        </Footer>
      </div>
    )
  }
  if (isNotRemindable(mutation.error)) return <NoReminderSent error={mutation.error} onClose={onClose} />

  return (
    <form onSubmit={submit} noValidate className="flex flex-col gap-5">
      {draft.last_reminder_at && (
        <InlineAlert variant="warning">
          <p>A reminder for this invoice was already sent on {formatDate(draft.last_reminder_at)}.</p>
        </InlineAlert>
      )}
      {mutation.isError && <ErrorAlert error={mutation.error} title="Reminder not sent" />}

      <Field id="reminder-to" label="To">
        <input
          id="reminder-to"
          type="text"
          readOnly
          value={draft.to ?? ''}
          className={cn(INPUT, 'h-12 border-border bg-surface px-4')}
        />
      </Field>
      <Field id="reminder-subject" label="Subject" error={errors.subject}>
        <input
          id="reminder-subject"
          ref={subjectRef}
          type="text"
          value={subject}
          readOnly={mutation.isPending}
          onChange={(event) => setSubject(event.target.value)}
          {...fieldA11y('reminder-subject', errors.subject)}
          className={cn(INPUT, 'h-12 px-4', errors.subject ? 'border-danger' : 'border-border')}
        />
      </Field>
      <Field id="reminder-message" label="Message" error={errors.message}>
        <textarea
          id="reminder-message"
          ref={messageRef}
          rows={12}
          value={message}
          readOnly={mutation.isPending}
          onChange={(event) => setMessage(event.target.value)}
          {...fieldA11y('reminder-message', errors.message)}
          className={cn(INPUT, 'resize-y p-4 leading-relaxed', errors.message ? 'border-danger' : 'border-border')}
        />
      </Field>

      <Footer>
        <Button type="submit" disabled={mutation.isPending}>
          <Mail aria-hidden />
          {mutation.isPending ? 'Sending…' : 'Send reminder'}
        </Button>
        <Button variant="secondary" onClick={onClose} disabled={mutation.isPending}>
          Cancel
        </Button>
      </Footer>
    </form>
  )
}

function fieldA11y(id: string, error?: string) {
  return { 'aria-invalid': error ? true : undefined, 'aria-describedby': error ? `${id}-error` : undefined }
}

function Field({ id, label, error, children }: { id: string; label: string; error?: string; children: ReactNode }) {
  return (
    <div className="flex flex-col gap-2">
      <label htmlFor={id} className="font-semibold">
        {label}
      </label>
      {children}
      {error && (
        <p id={`${id}-error`} className="flex items-center gap-2 text-small font-semibold text-danger">
          <OctagonAlert aria-hidden className="size-4 shrink-0" />
          {error}
        </p>
      )}
    </div>
  )
}
