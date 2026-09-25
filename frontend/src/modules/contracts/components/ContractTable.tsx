import { Link } from 'react-router'

import { StatusBadge } from '@/components/common/StatusBadge'
import { SortableTh, Table, TBody, Td, THead, Tr } from '@/components/ui/table'
import { formatDate } from '@/lib/format'
import { cn } from '@/lib/utils'

import type { ContractListItem } from '../api'
import type { ContractQuery, SortKey } from '../query'
import { endHint, LIFECYCLE_META } from '../status'

// Six columns so the table fits a laptop screen: parties sit under the title (CON-002 AC1).
const COLUMNS: { key: SortKey; label: string; numeric?: boolean }[] = [
  { key: 'title', label: 'Contract' },
  { key: 'start_date', label: 'Start' },
  { key: 'end_date', label: 'End' },
  { key: 'status', label: 'Status' },
  { key: 'high_risks', label: 'High risks', numeric: true },
  { key: 'uploaded_at', label: 'Uploaded' },
]

interface ContractTableProps {
  items: ContractListItem[]
  query: ContractQuery
  onSort: (key: SortKey) => void
  stale?: boolean
}

export function ContractTable({ items, query, onSort, stale }: ContractTableProps) {
  return (
    <div aria-busy={stale || undefined} className={cn('transition-opacity', stale && 'opacity-60')}>
      <Table caption="Contracts">
        <THead>
          <Tr>
            {COLUMNS.map((column) => (
              <SortableTh
                key={column.key}
                label={column.label}
                numeric={column.numeric}
                active={query.sort === column.key}
                ascending={query.order === 'asc'}
                onSort={() => onSort(column.key)}
              />
            ))}
          </Tr>
        </THead>
        <TBody>
          {items.map((item) => {
            const read = item.processing_status === 'completed'
            return (
              <Tr key={item.id}>
                <Td className="min-w-56">
                  <Link to={`/contracts/${item.id}`} className="link">
                    {item.title}
                  </Link>
                  {item.parties.length > 0 && (
                    <div className="text-small text-text-muted">{item.parties.join(' · ')}</div>
                  )}
                </Td>
                <Td className="whitespace-nowrap">{item.start_date ? formatDate(item.start_date) : '—'}</Td>
                <Td>
                  {item.end_date && <div className="whitespace-nowrap">{formatDate(item.end_date)}</div>}
                  {read && (
                    <div
                      className={cn(
                        'text-small',
                        item.lifecycle === 'expired'
                          ? 'text-danger'
                          : item.at_risk_reasons.some((r) => r.startsWith('Expires'))
                            ? 'font-semibold text-warning'
                            : 'text-text-muted',
                      )}
                    >
                      {endHint(item.days_until_end)}
                    </div>
                  )}
                </Td>
                <Td>
                  <div className="flex flex-col items-start gap-1">
                    <StatusBadge variant={LIFECYCLE_META[item.lifecycle].variant} label={LIFECYCLE_META[item.lifecycle].label} />
                    {item.at_risk && (
                      <>
                        <StatusBadge variant="warning" label="At risk" />
                        <span className="text-small text-warning">{item.at_risk_reasons.join(' · ')}</span>
                      </>
                    )}
                  </div>
                </Td>
                <Td numeric className={cn(item.high_risk_count > 0 && 'font-semibold text-danger')}>
                  {read ? item.high_risk_count : '—'}
                </Td>
                <Td className="whitespace-nowrap">{formatDate(item.uploaded_at)}</Td>
              </Tr>
            )
          })}
        </TBody>
      </Table>
    </div>
  )
}
