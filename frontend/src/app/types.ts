import type { LucideIcon } from 'lucide-react'
import type { RouteObject } from 'react-router'

export interface Crumb {
  label: string
  to?: string
}

export interface PageAction {
  label: string
  to: string
  icon: LucideIcon
}

/** Attached to every page route as `handle` (PLT-001 AC4, AC6). */
export interface RouteHandle {
  /** Page h1 and document title. */
  title: string
  /** Last breadcrumb label (often shorter than the title, e.g. "Dashboard"). */
  crumb: string
  /** Breadcrumb ancestors. Pages without parents (Home, Not found) show no breadcrumb. */
  parents?: Crumb[]
  /** The page's primary action, shown top right of the page header. */
  action?: PageAction
}

export interface NavItem {
  label: string
  to: string
  icon: LucideIcon
}

/**
 * A business module plugs into the shell by exporting one of these and adding it to the
 * registry in `app/modules.ts`. The shell code itself never changes.
 */
export interface ModuleDefinition {
  id: string
  label: string
  nav: NavItem[]
  routes: RouteObject[]
}
