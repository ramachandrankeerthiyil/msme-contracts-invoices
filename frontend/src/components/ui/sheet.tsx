import * as Dialog from '@radix-ui/react-dialog'
import type { ReactNode } from 'react'

import { cn } from '@/lib/utils'

// Slide-in side panel built on Radix Dialog: focus trap, Escape to close, and focus returns to
// the trigger on close (PLT-001 AC7).
export const Sheet = Dialog.Root
export const SheetTrigger = Dialog.Trigger
export const SheetClose = Dialog.Close

interface SheetContentProps {
  title: string
  children: ReactNode
  className?: string
  onCloseAutoFocus?: (event: Event) => void
}

export function SheetContent({ title, children, className, onCloseAutoFocus }: SheetContentProps) {
  return (
    <Dialog.Portal>
      <Dialog.Overlay className="fixed inset-0 z-40 bg-overlay" />
      <Dialog.Content
        aria-describedby={undefined}
        onCloseAutoFocus={onCloseAutoFocus}
        className={cn(
          'fixed inset-y-0 left-0 z-50 flex w-80 max-w-[85vw] flex-col overflow-y-auto',
          'border-r border-border bg-surface shadow-panel outline-none',
          className,
        )}
      >
        <Dialog.Title className="sr-only">{title}</Dialog.Title>
        {children}
      </Dialog.Content>
    </Dialog.Portal>
  )
}
