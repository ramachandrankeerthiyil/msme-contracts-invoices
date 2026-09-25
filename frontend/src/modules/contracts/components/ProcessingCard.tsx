import { CircleCheck, Circle, LoaderCircle } from 'lucide-react'

import { cn } from '@/lib/utils'

import type { ProcessingStatus } from '../api'

const STEPS: { label: string; doneWhen: ProcessingStatus[]; activeWhen: ProcessingStatus[] }[] = [
  { label: 'Uploaded', doneWhen: ['uploaded', 'extracting_text', 'analysing'], activeWhen: [] },
  { label: 'Reading the document', doneWhen: ['analysing'], activeWhen: ['uploaded', 'extracting_text'] },
  { label: 'Finding parties, dates, terms and risks', doneWhen: [], activeWhen: ['analysing'] },
]

/** Progress while a contract is being read (CON-001 AC8). */
export function ProcessingCard({ status }: { status: ProcessingStatus }) {
  return (
    <section
      aria-labelledby="processing-heading"
      aria-live="polite"
      className="flex flex-col gap-4 rounded-lg border border-border bg-surface p-6"
    >
      <h2 id="processing-heading" className="text-h2">
        Reading your contract…
      </h2>
      <ol className="flex flex-col gap-3">
        {STEPS.map((step) => {
          const done = step.doneWhen.includes(status)
          const active = step.activeWhen.includes(status)
          const Icon = done ? CircleCheck : active ? LoaderCircle : Circle
          return (
            <li key={step.label} className={cn('flex items-center gap-3', !done && !active && 'text-text-muted')}>
              <Icon
                aria-hidden
                className={cn('size-6 shrink-0', done && 'text-success', active && 'animate-spin text-primary')}
              />
              <span className={cn(active && 'font-semibold')}>{step.label}</span>
              <span className="sr-only">{done ? '(done)' : active ? '(in progress)' : '(waiting)'}</span>
            </li>
          )
        })}
      </ol>
      <p className="text-text-muted">
        This usually takes under a minute. You can leave this page — we&apos;ll keep going.
      </p>
    </section>
  )
}
