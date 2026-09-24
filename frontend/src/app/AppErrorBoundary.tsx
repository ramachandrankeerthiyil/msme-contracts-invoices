import { Component, type ErrorInfo, type ReactNode } from 'react'

import { ErrorAlert } from '@/components/common/ErrorAlert'

interface State {
  error: unknown
  hasError: boolean
}

/** Last-resort boundary for errors outside the router (PLT-002 AC8/AC11). */
export class AppErrorBoundary extends Component<{ children: ReactNode }, State> {
  state: State = { error: undefined, hasError: false }

  static getDerivedStateFromError(error: unknown): State {
    return { error, hasError: true }
  }

  componentDidCatch(error: unknown, info: ErrorInfo): void {
    console.error('[ui] unhandled render error', error, info.componentStack)
  }

  render(): ReactNode {
    if (this.state.hasError) {
      return (
        <main className="mx-auto max-w-content p-8">
          <ErrorAlert error={this.state.error} onRetry={() => window.location.reload()} retryLabel="Reload page" />
        </main>
      )
    }
    return this.props.children
  }
}
