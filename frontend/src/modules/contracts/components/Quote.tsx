import { TriangleAlert } from 'lucide-react'

/** A quote from the contract (CON-002 AC6), flagged when it couldn't be found in the file. */
export function Quote({ text, verified }: { text: string; verified: boolean }) {
  return (
    <figure className="mt-2">
      <figcaption className="text-small text-text-muted">From the contract:</figcaption>
      <blockquote className="mt-1 border-l-4 border-border pl-4 text-small italic">“{text}”</blockquote>
      {!verified && (
        <p className="mt-1 flex items-start gap-2 text-small text-warning">
          <TriangleAlert aria-hidden className="mt-0.5 size-4 shrink-0" />
          We couldn&apos;t find this exact wording in the file — please check the original.
        </p>
      )}
    </figure>
  )
}
