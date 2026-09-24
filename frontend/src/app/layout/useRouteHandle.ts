import { useMatches } from 'react-router'

import type { RouteHandle } from '../types'

/** The handle of the deepest matched route that defines a page title. */
export function useRouteHandle(): RouteHandle | undefined {
  const matches = useMatches()
  for (let i = matches.length - 1; i >= 0; i--) {
    const handle = matches[i]?.handle as RouteHandle | undefined
    if (handle?.title) return handle
  }
  return undefined
}
