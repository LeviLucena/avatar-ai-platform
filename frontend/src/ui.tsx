import { useEffect, useRef, type ReactNode } from 'react'
import { CATEGORY_LABEL } from './api'

const LABEL: Record<string, string> = { nemotron: 'Nemotron', claude: 'Claude' }
export const SevBadge = ({ s }: { s: string }) => <span className={`badge ${s}`}>{s}</span>
export const CatLabel = ({ c }: { c: string }) => <>{CATEGORY_LABEL[c] ?? c}</>
export const StatusBadge = ({ s }: { s: string }) => <span className={`badge status-${s}`}>{s.replace('_', ' ')}</span>
export const Engine = ({ e }: { e: string }) =>
  e ? (
    <span className={`badge engine ${e === 'heuristic' ? '' : 'claude'}`} title={e === 'heuristic' ? 'Deterministic fallback (no API key or API error)' : `Analysed by ${LABEL[e] ?? e}`}>
      {e === 'heuristic' ? 'heuristic' : `✦ ${LABEL[e] ?? e}`}
    </span>
  ) : null

export function Kpi({ label, value, tone }: { label: string; value: ReactNode; tone?: 'alert' | 'warn' }) {
  return (
    <div className={`card kpi ${tone ?? ''}`}>
      <div className="v">{value}</div>
      <div className="l">{label}</div>
    </div>
  )
}

export function Page({ title, sub, actions, children }: { title: string; sub?: string; actions?: ReactNode; children: ReactNode }) {
  return (
    <>
      <div className="topbar">
        <div>
          <h1>{title}</h1>
          {sub && <div className="sub">{sub}</div>}
        </div>
        <div className="row">{actions}</div>
      </div>
      {children}
    </>
  )
}

export function Loading() {
  return <div className="muted dots">Loading<span>.</span><span>.</span><span>.</span></div>
}

export function ErrorBox({ error }: { error: string }) {
  return <div className="callout crit">⚠ {error}</div>
}

/** Re-run `fn` every `ms` (and once on mount). */
export function usePoll(fn: () => void, ms: number, deps: unknown[] = []) {
  const ref = useRef(fn)
  ref.current = fn
  useEffect(() => {
    ref.current()
    const id = setInterval(() => ref.current(), ms)
    return () => clearInterval(id)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)
}
