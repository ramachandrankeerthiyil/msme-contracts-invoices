import { House, type LucideIcon } from 'lucide-react'
import { useId } from 'react'
import { Link, useLocation } from 'react-router'

import { cn } from '@/lib/utils'

import { modules } from '../modules'
import type { NavItem } from '../types'
import { findActiveNavTarget } from './nav'

const HOME: NavItem = { label: 'Home', to: '/', icon: House }
const NAV_TARGETS = [HOME.to, ...modules.flatMap((module) => module.nav.map((item) => item.to))]

interface NavLinksProps {
  label: string
  onNavigate?: () => void
}

/** Main navigation, shared by the desktop sidebar and the mobile menu (PLT-001 AC2, AC3). */
export function NavLinks({ label, onNavigate }: NavLinksProps) {
  const { pathname } = useLocation()
  const active = findActiveNavTarget(pathname, NAV_TARGETS)
  const idPrefix = useId()

  return (
    <nav aria-label={label} className="p-4">
      <ul className="flex flex-col gap-1">
        <li>
          <NavLink item={HOME} active={active === HOME.to} onNavigate={onNavigate} />
        </li>
        {modules.map((module) => {
          const headingId = `${idPrefix}-${module.id}`
          return (
            <li key={module.id} className="mt-6">
              <p
                id={headingId}
                className="px-4 pb-2 text-small font-semibold tracking-wider text-text-muted uppercase"
              >
                {module.label}
              </p>
              <ul aria-labelledby={headingId} className="flex flex-col gap-1">
                {module.nav.map((item) => (
                  <li key={item.to}>
                    <NavLink item={item} active={active === item.to} onNavigate={onNavigate} />
                  </li>
                ))}
              </ul>
            </li>
          )
        })}
      </ul>
    </nav>
  )
}

function NavLink({
  item,
  active,
  onNavigate,
}: {
  item: NavItem
  active: boolean
  onNavigate?: () => void
}) {
  const Icon: LucideIcon = item.icon
  return (
    <Link
      to={item.to}
      onClick={onNavigate}
      aria-current={active ? 'page' : undefined}
      className={cn(
        'relative flex h-12 items-center gap-3 rounded-md px-4 text-body text-text transition-colors',
        'hover:bg-surface-strong',
        active &&
          'bg-surface-strong font-semibold before:absolute before:inset-y-2 before:left-0 before:w-1 before:rounded-full before:bg-primary',
      )}
    >
      <Icon aria-hidden className={cn('size-5 shrink-0', active ? 'text-primary' : 'text-text-muted')} />
      {item.label}
    </Link>
  )
}
