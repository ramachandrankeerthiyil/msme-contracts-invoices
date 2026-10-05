import * as RadixDialog from '@radix-ui/react-dialog'
import type { ReactNode } from 'react'

import { cn } from '@/lib/utils'

// Centred modal built on Radix Dialog: focus trap, Escape to close, and focus returns to the
// element that opened it (ui-design-system.md "Dialog", INV-004 AC13).
export const Dialog = RadixDialog.Root

interface DialogContentProps {
  title: string
  /** Short summary read out with the title; shown under it. */
  description?: ReactNode
  children: ReactNode
  /** Block Escape and outside clicks, e.g. while a request is in flight. */
  locked?: boolean
  /** Where focus goes on close. Needed when the dialog has no Radix trigger of its own. */
  onCloseAutoFocus?: (event: Event) => void
  className?: string
}

export function DialogContent({
  title,
  description,
  children,
  locked,
  onCloseAutoFocus,
  className,
}: DialogContentProps) {
  const keepOpen = (event: Event) => {
    if (locked) event.preventDefault()
  }
  return (
    <RadixDialog.Portal>
      <RadixDialog.Overlay className="fixed inset-0 z-40 bg-overlay" />
      <RadixDialog.Content
        {...(description ? {} : { 'aria-describedby': undefined })}
        onCloseAutoFocus={onCloseAutoFocus}
        onEscapeKeyDown={keepOpen}
        onPointerDownOutside={keepOpen}
        onInteractOutside={keepOpen}
        className={cn(
          'fixed top-1/2 left-1/2 z-50 max-h-[90vh] w-[calc(100%-2rem)] max-w-2xl -translate-x-1/2 -translate-y-1/2',
          'overflow-y-auto rounded-lg border border-border bg-bg p-6 shadow-panel outline-none sm:p-8',
          className,
        )}
      >
        <RadixDialog.Title className="text-h2">{title}</RadixDialog.Title>
        {description && (
          <RadixDialog.Description asChild>
            <p className="mt-2 text-text-muted">{description}</p>
          </RadixDialog.Description>
        )}
        <div className="mt-6">{children}</div>
      </RadixDialog.Content>
    </RadixDialog.Portal>
  )
}
