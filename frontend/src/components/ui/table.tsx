import type { ReactNode, TdHTMLAttributes, ThHTMLAttributes } from 'react'

import { cn } from '@/lib/utils'

// Data table styling from ui-design-system.md: sticky header, 56px rows, zebra rows,
// right-aligned numbers.

export function Table({ caption, children }: { caption: string; children: ReactNode }) {
  return (
    <div className="overflow-x-auto rounded-lg border border-border">
      <table className="w-full border-collapse text-left text-small">
        <caption className="sr-only">{caption}</caption>
        {children}
      </table>
    </div>
  )
}

export function THead({ children }: { children: ReactNode }) {
  return <thead className="sticky top-0 bg-surface">{children}</thead>
}

export function TBody({ children }: { children: ReactNode }) {
  return <tbody className="[&>tr:nth-child(even)]:bg-surface">{children}</tbody>
}

export function Tr({ children }: { children: ReactNode }) {
  return <tr className="border-b border-border last:border-b-0">{children}</tr>
}

interface CellProps {
  numeric?: boolean
}

export function Th({ numeric, className, ...props }: CellProps & ThHTMLAttributes<HTMLTableCellElement>) {
  return (
    <th
      scope="col"
      className={cn('h-14 border-b border-border px-4 font-semibold whitespace-nowrap text-text', numeric && 'text-right', className)}
      {...props}
    />
  )
}

export function Td({ numeric, className, ...props }: CellProps & TdHTMLAttributes<HTMLTableCellElement>) {
  return <td className={cn('h-14 px-4 py-2', numeric && 'text-right tabular-nums', className)} {...props} />
}
