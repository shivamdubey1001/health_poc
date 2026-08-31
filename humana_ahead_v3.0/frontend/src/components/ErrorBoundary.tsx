import { Component, type ErrorInfo, type ReactNode } from 'react'
import { AlertTriangle, RotateCcw } from 'lucide-react'

type Props = { children: ReactNode }
type State = { error: Error | null }

/**
 * Catches render-time faults so one unexpected null cannot white-screen the
 * whole application. This matters more here than in a typical app: a refresh
 * would otherwise be the only recovery, and mid-demo that is unrecoverable.
 */
export default class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null }

  static getDerivedStateFromError(error: Error): State {
    return { error }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('Humana Ahead render error:', error, info.componentStack)
  }

  render() {
    if (!this.state.error) return this.props.children
    return (
      <div className="card m-6" role="alert" aria-live="assertive">
        <div className="flex items-start gap-3">
          <AlertTriangle className="mt-0.5 shrink-0 text-rose-700" size={22} />
          <div className="min-w-0">
            <h2 className="section-title">Something went wrong on this screen</h2>
            <p className="mt-2 text-sm leading-6 text-muted">
              The rest of the application is still running and no data was lost. Assessment
              results are stored server-side, so returning to a page will reload them.
            </p>
            <pre className="mt-3 max-h-40 overflow-auto rounded-lg bg-panel p-3 text-xs text-muted">
              {this.state.error.message}
            </pre>
            <div className="mt-4 flex gap-2">
              <button className="btn-primary" onClick={() => this.setState({ error: null })}>
                <RotateCcw size={16} /> Try again
              </button>
              <button className="btn-secondary" onClick={() => window.location.reload()}>
                Reload the application
              </button>
            </div>
          </div>
        </div>
      </div>
    )
  }
}
