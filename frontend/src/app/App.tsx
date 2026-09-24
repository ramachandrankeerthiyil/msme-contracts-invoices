import { QueryClientProvider } from '@tanstack/react-query'
import { createBrowserRouter } from 'react-router'
import { RouterProvider } from 'react-router/dom'

import { AppErrorBoundary } from './AppErrorBoundary'
import { createQueryClient } from './queryClient'
import { routes } from './router'

const router = createBrowserRouter(routes)
const queryClient = createQueryClient()

export function App() {
  return (
    <AppErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <RouterProvider router={router} />
      </QueryClientProvider>
    </AppErrorBoundary>
  )
}
