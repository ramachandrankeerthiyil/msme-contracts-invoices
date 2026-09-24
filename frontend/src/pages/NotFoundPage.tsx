import { FileText, House, ReceiptIndianRupee, SearchX } from 'lucide-react'

import { PageHeader } from '@/app/layout/PageHeader'
import { EmptyState } from '@/components/common/EmptyState'
import { ButtonLink } from '@/components/ui/button'

/** PLT-001 AC9. */
export function NotFoundPage() {
  return (
    <>
      <PageHeader />
      <EmptyState
        icon={SearchX}
        title="We couldn't find that page"
        description="The link may be out of date, or the address may have a typo. Try one of these instead:"
        action={
          <ul className="flex flex-col gap-3 sm:flex-row">
            <li>
              <ButtonLink to="/">
                <House aria-hidden />
                Home
              </ButtonLink>
            </li>
            <li>
              <ButtonLink to="/contracts/dashboard" variant="secondary">
                <FileText aria-hidden />
                Contract dashboard
              </ButtonLink>
            </li>
            <li>
              <ButtonLink to="/invoices/dashboard" variant="secondary">
                <ReceiptIndianRupee aria-hidden />
                Invoice dashboard
              </ButtonLink>
            </li>
          </ul>
        }
      />
    </>
  )
}
