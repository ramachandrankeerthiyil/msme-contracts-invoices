import type { RouteObject } from 'react-router'

import { HomePage } from '@/pages/HomePage'
import { NotFoundPage } from '@/pages/NotFoundPage'
import { RouteErrorPage } from '@/pages/RouteErrorPage'

import { AppShell } from './layout/AppShell'
import { modules } from './modules'
import type { RouteHandle } from './types'

const homeHandle: RouteHandle = { title: 'Overview', crumb: 'Home' }
const notFoundHandle: RouteHandle = { title: 'Page not found', crumb: 'Page not found' }

export const routes: RouteObject[] = [
  {
    path: '/',
    element: <AppShell />,
    children: [
      {
        // Page render errors are shown inside the shell (PLT-001 AC10).
        errorElement: <RouteErrorPage />,
        children: [
          { index: true, element: <HomePage />, handle: homeHandle },
          ...modules.flatMap((module) => module.routes),
          { path: '*', element: <NotFoundPage />, handle: notFoundHandle },
        ],
      },
    ],
  },
]
