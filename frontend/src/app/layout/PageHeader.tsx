import { useEffect, type ReactNode } from 'react'

import { ButtonLink } from '@/components/ui/button'
import { cn } from '@/lib/utils'

import { APP_NAME } from '../constants'
import { Breadcrumbs } from './Breadcrumbs'
import { useRouteHandle } from './useRouteHandle'

interface PageHeaderProps {
  /** Overrides the route's title, e.g. with a contract's name. */
  title?: string
  /** Overrides the last breadcrumb label. */
  crumb?: string
  /** Overrides the route's primary action; pass `null` for none. */
  action?: ReactNode
  description?: string
}

/**
 * Breadcrumb + h1 + primary action, the same on every page (PLT-001 AC4). Also sets the
 * document title. The h1 receives focus after navigation (AC8).
 */
export function PageHeader({ title, crumb, action, description }: PageHeaderProps) {
  const handle = useRouteHandle()
  const pageTitle = title ?? handle?.title ?? ''
  const crumbs = handle?.parents ? [...handle.parents, { label: crumb ?? handle.crumb }] : []

  const routeAction = handle?.action
  const primaryAction =
    action !== undefined
      ? action
      : routeAction && (
          <ButtonLink to={routeAction.to}>
            <routeAction.icon aria-hidden />
            {routeAction.label}
          </ButtonLink>
        )

  useEffect(() => {
    document.title = `${pageTitle} · ${APP_NAME}`
  }, [pageTitle])

  return (
    <div className="mb-8 border-b border-border pb-6">
      {crumbs.length > 0 && <Breadcrumbs crumbs={crumbs} />}
      <div
        className={cn(
          'flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between',
          crumbs.length > 0 && 'mt-3',
        )}
      >
        <h1 id="page-title" tabIndex={-1} className="text-h1 outline-none">
          {pageTitle}
        </h1>
        {primaryAction}
      </div>
      {description && <p className="mt-2 max-w-prose text-text-muted">{description}</p>}
    </div>
  )
}
