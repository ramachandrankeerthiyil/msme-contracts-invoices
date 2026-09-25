import { useQuery } from '@tanstack/react-query'
import { ReceiptIndianRupee, Upload } from 'lucide-react'

import { EmptyState } from '@/components/common/EmptyState'
import { QueryBoundary } from '@/components/common/QueryBoundary'
import { ButtonLink } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'

import { getDashboard, invoiceKeys } from '../api'
import { InvoiceKpis } from './InvoiceKpis'

/** Invoice headline numbers on Home (PLT-001 AC5); loads and fails on its own (AC10). */
export function InvoicesOverview() {
  const query = useQuery({ queryKey: invoiceKeys.dashboard(), queryFn: getDashboard })
  return (
    <QueryBoundary query={query} loading={<Skeleton className="h-64 w-full" />}>
      {(data) =>
        data.has_data ? (
          <InvoiceKpis data={data} />
        ) : (
          <EmptyState
            icon={ReceiptIndianRupee}
            title="No invoices yet"
            description="Upload your invoice spreadsheet to see what is outstanding and what needs follow-up this week."
            action={
              <ButtonLink to="/invoices/upload">
                <Upload aria-hidden />
                Upload invoices
              </ButtonLink>
            }
          />
        )
      }
    </QueryBoundary>
  )
}
