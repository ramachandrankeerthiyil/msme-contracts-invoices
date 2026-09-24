import { useEffect, useRef } from 'react'
import { Outlet, useLocation } from 'react-router'

import { Header } from './Header'
import { NavLinks } from './NavLinks'

/** After moving to another page, put keyboard/screen-reader focus on its heading (AC8). */
function useFocusHeadingOnNavigation() {
  const { pathname } = useLocation()
  const previous = useRef(pathname)

  useEffect(() => {
    if (previous.current === pathname) return
    previous.current = pathname
    const target = document.getElementById('page-title') ?? document.getElementById('content')
    target?.focus()
  }, [pathname])
}

/** Header + sidebar + main content, around every page (PLT-001 AC1). */
export function AppShell() {
  useFocusHeadingOnNavigation()

  return (
    <div className="flex min-h-screen flex-col bg-bg text-text">
      <a
        href="#content"
        className="sr-only focus:not-sr-only focus:fixed focus:top-4 focus:left-4 focus:z-50 focus:rounded-md focus:bg-primary focus:px-5 focus:py-3 focus:font-semibold focus:text-on-primary"
      >
        Skip to content
      </a>
      <Header />
      <div className="flex flex-1">
        <div className="hidden w-66 shrink-0 border-r border-border bg-surface lg:block">
          <div className="sticky top-18">
            <NavLinks label="Main" />
          </div>
        </div>
        <main id="content" tabIndex={-1} className="min-w-0 flex-1 outline-none">
          <div className="mx-auto w-full max-w-content px-4 py-6 sm:px-8 sm:py-8">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  )
}
