import { FileCheck2 } from 'lucide-react'
import { Link } from 'react-router'

import { APP_NAME } from '../constants'
import { MobileNav } from './MobileNav'

export function Header() {
  return (
    <header className="sticky top-0 z-30 h-18 shrink-0 border-b border-border bg-bg">
      <div className="flex h-full items-center gap-4 px-4 sm:px-8">
        <MobileNav />
        <Link to="/" className="flex min-w-0 items-center gap-3 rounded-md">
          <span className="grid size-10 shrink-0 place-items-center rounded-md bg-primary text-on-primary">
            <FileCheck2 aria-hidden className="size-6" />
          </span>
          <span className="truncate text-body font-bold sm:text-h3">{APP_NAME}</span>
        </Link>
      </div>
    </header>
  )
}
