import { useEffect } from 'react'
import { useRouteError } from 'react-router'

import { PageHeader } from '@/app/layout/PageHeader'
import { ErrorAlert } from '@/components/common/ErrorAlert'

/** Shown inside the shell when a page fails to render, so navigation keeps working. */
export function RouteErrorPage() {
  const error = useRouteError()

  useEffect(() => {
    console.error('[ui] page failed to render', error)
  }, [error])

  return (
    <>
      <PageHeader title="Something went wrong" action={null} />
      <ErrorAlert error={error} onRetry={() => window.location.reload()} retryLabel="Reload page" />
    </>
  )
}
