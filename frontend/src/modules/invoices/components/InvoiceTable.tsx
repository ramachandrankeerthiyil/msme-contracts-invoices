import { StatusBadge } from '@/components/common/StatusBadge'
import { SortableTh, Table, TBody, Td, Th, THead, Tr } from '@/components/ui/table'
import { formatDate, formatINR } from '@/lib/format'
import { cn } from '@/lib/utils'

import type { InvoiceItem } from '../api'
import type { InvoiceQuery, SortKey } from '../query'
import { dueHintClass, invoiceDueHint, STATUS_META } from '../status'

// Six columns so the table fits a laptop screen without sideways scrolling: the raised date sits
// under the invoice number, and the paid date is in the Due column's hint ("paid on 12 Sep 2026").
const COLUMNS: { key: SortKey | null; label: string; numeric?: boolean }[] = [
  { key: 'invoice_number', label: 'Invoice' },
  { key: 'customer_name', label: 'Customer' },
  { key: 'due_date', label: 'Due' },
  { key: 'amount', label: 'Amount', numeric: true },
  { key: 'status', label: 'Status' },
  { key: null, label: 'Record' },
]

interface InvoiceTableProps {
  items: InvoiceItem[]
  query: InvoiceQuery
  onSort: (key: SortKey) => void
  /** Previous results shown while new ones load. */
  stale?: boolean
}

/** The invoice table (INV-002 AC1, AC1a, AC4). */
export function InvoiceTable({ items, query, onSort, stale }: InvoiceTableProps) {
  return (
    <div aria-busy={stale || undefined} className={cn('transition-opacity', stale && 'opacity-60')}>
      <Table caption="Invoices">
        <THead>
          <Tr>
            {COLUMNS.map((column) =>
              column.key ? (
                <SortableTh
                  key={column.key}
                  label={column.label}
                  numeric={column.numeric}
                  active={query.sort === column.key}
                  ascending={query.order === 'asc'}
                  onSort={() => onSort(column.key as SortKey)}
                />
              ) : (
                <Th key={column.label}>{column.label}</Th>
              ),
            )}
          </Tr>
        </THead>
        <TBody>
          {items.map((item) => (
            <Tr key={item.id}>
              <Td>
                <div className="font-semibold whitespace-nowrap">{item.invoice_number}</div>
                <div className="text-small text-text-muted">Raised {formatDate(item.date_raised)}</div>
              </Td>
              <Td className="min-w-40">{item.customer_name}</Td>
              <Td>
                <div className="whitespace-nowrap">{formatDate(item.due_date)}</div>
                <div className={cn('text-small', dueHintClass(item.status))}>{invoiceDueHint(item)}</div>
              </Td>
              <Td numeric className="whitespace-nowrap">
                {formatINR(item.amount)}
              </Td>
              <Td>
                <StatusBadge variant={STATUS_META[item.status].variant} label={STATUS_META[item.status].label} />
              </Td>
              <Td>
                {item.record_status === 'updated' && item.record_updated_at ? (
                  <StatusBadge variant="info" label={`Updated on ${formatDate(item.record_updated_at)}`} wrap />
                ) : (
                  <span className="text-text-muted">New</span>
                )}
              </Td>
            </Tr>
          ))}
        </TBody>
      </Table>
    </div>
  )
}
