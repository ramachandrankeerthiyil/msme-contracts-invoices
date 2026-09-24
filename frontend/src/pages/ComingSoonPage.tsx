import { Hammer, House } from 'lucide-react'

import { PageHeader } from '@/app/layout/PageHeader'
import { useRouteHandle } from '@/app/layout/useRouteHandle'
import { EmptyState } from '@/components/common/EmptyState'
import { ButtonLink } from '@/components/ui/button'

/** Placeholder for module pages not built yet, so navigation works end to end from day one. */
export function ComingSoonPage() {
  const handle = useRouteHandle()
  return (
    <>
      <PageHeader />
      <EmptyState
        icon={Hammer}
        title="This page is being built"
        description={`${handle?.title ?? 'This page'} will be available in an upcoming update.`}
        action={
          <ButtonLink to="/" variant="secondary">
            <House aria-hidden />
            Go to Home
          </ButtonLink>
        }
      />
    </>
  )
}
