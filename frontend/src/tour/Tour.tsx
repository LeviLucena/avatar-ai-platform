import { createContext, useCallback, useContext, useEffect, useMemo, useState, type CSSProperties, type ReactNode } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { can } from '../auth'
import { STEPS } from './steps'

type Ctx = { start: () => void; active: boolean }
const TourCtx = createContext<Ctx>({ start: () => {}, active: false })
export const useTour = () => useContext(TourCtx)

type Rect = { top: number; left: number; width: number; height: number }
const PAD = 8
const CARD_W = 380

const clamp = (v: number, lo: number, hi: number) => Math.max(lo, Math.min(hi, v))

export function TourProvider({ role, email, children }: { role: string; email: string; children: ReactNode }) {
  const steps = useMemo(() => STEPS.filter((s) => !s.section || can(role, s.section)), [role])
  const [active, setActive] = useState(false)
  const [i, setI] = useState(0)
  const [rect, setRect] = useState<Rect | null>(null)
  const [welcome, setWelcome] = useState(false)
  const nav = useNavigate()
  const loc = useLocation()
  const seenKey = `qa_tour_seen:${email}`
  const step = steps[i]
  const last = i === steps.length - 1

  // one-time invitation for each user on this browser
  useEffect(() => {
    if (localStorage.getItem(seenKey)) return
    const t = setTimeout(() => setWelcome(true), 800)
    return () => clearTimeout(t)
  }, [seenKey])

  const start = useCallback(() => {
    localStorage.setItem(seenKey, '1')
    setWelcome(false)
    setI(0)
    setActive(true)
  }, [seenKey])

  const close = useCallback(() => {
    localStorage.setItem(seenKey, '1')
    setActive(false)
    setRect(null)
  }, [seenKey])

  const next = useCallback(() => (last ? close() : setI((n) => n + 1)), [last, close])
  const prev = useCallback(() => setI((n) => Math.max(0, n - 1)), [])

  // go to the page that belongs to the current step (some routes need a real record)
  useEffect(() => {
    if (!active || !step?.route) return
    let cancelled = false
    ;(async () => {
      try {
        const path = typeof step.route === 'string' ? step.route : await step.route!()
        if (!cancelled && window.location.pathname !== path) nav(path)
      } catch {
        /* stay on the current page; the step falls back to a centred card */
      }
    })()
    return () => {
      cancelled = true
    }
  }, [active, step, nav])

  // keep the spotlight on the target while the page loads, scrolls or resizes
  useEffect(() => {
    setRect(null)
    if (!active || !step?.target) return
    const selector = step.target
    let scrolled = false
    const tick = () => {
      const el = document.querySelector(selector) as HTMLElement | null
      if (!el) return
      if (!scrolled) {
        el.scrollIntoView({ block: 'center', behavior: 'smooth' })
        scrolled = true
      }
      const r = el.getBoundingClientRect()
      setRect((p) =>
        p && Math.abs(p.top - r.top) < 1 && Math.abs(p.left - r.left) < 1 && Math.abs(p.width - r.width) < 1 && Math.abs(p.height - r.height) < 1
          ? p
          : { top: r.top, left: r.left, width: r.width, height: r.height },
      )
    }
    tick()
    const id = setInterval(tick, 150)
    return () => clearInterval(id)
  }, [active, step, loc.pathname])

  useEffect(() => {
    if (!active) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') close()
      else if (e.key === 'ArrowRight') next()
      else if (e.key === 'ArrowLeft') prev()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [active, close, next, prev])

  // card position: below the target, else above, else pinned to a corner (very tall targets)
  const vw = window.innerWidth
  const vh = window.innerHeight
  const w = Math.min(CARD_W, vw - 32)
  let cardStyle: CSSProperties = { top: '50%', left: '50%', transform: 'translate(-50%, -50%)', width: w }
  if (rect) {
    const left = clamp(rect.left, 16, vw - w - 16)
    const spaceBelow = vh - (rect.top + rect.height)
    if (rect.height > vh * 0.55) {
      // very tall target: put the card beside it (not over it) when there is room, else in a corner
      if (rect.left - PAD - 16 >= w + 16) cardStyle = { top: clamp(rect.top, 16, vh - 320), left: rect.left - PAD - 16 - w, width: w }
      else if (vw - (rect.left + rect.width) - PAD - 16 >= w + 16) cardStyle = { top: clamp(rect.top, 16, vh - 320), left: rect.left + rect.width + PAD + 16, width: w }
      else cardStyle = { bottom: 24, right: 24, width: w }
    } else if (spaceBelow >= 270) cardStyle = { top: rect.top + rect.height + PAD + 12, left, width: w }
    else if (rect.top >= 270) cardStyle = { bottom: vh - rect.top + PAD + 12, left, width: w }
    else cardStyle = { bottom: 24, right: 24, width: w }
  }

  return (
    <TourCtx.Provider value={{ start, active }}>
      {children}

      {welcome && !active && (
        <div className="tour-dim" role="dialog" aria-label="Guided tour invitation">
          <div className="tour-card" style={{ top: '50%', left: '50%', transform: 'translate(-50%, -50%)', width: Math.min(420, vw - 32) }}>
            <h3>Welcome!</h3>
            <p>Want a 3-minute guided tour of what this platform does and how it works?</p>
            <div className="tour-actions">
              <button className="btn secondary small" onClick={() => { localStorage.setItem(seenKey, '1'); setWelcome(false) }}>Maybe later</button>
              <button className="btn small" onClick={start}>Start the tour</button>
            </div>
          </div>
        </div>
      )}

      {active && step && (
        <div className="tour-layer" role="dialog" aria-label="Guided tour">
          {rect ? (
            <div
              className="tour-spot"
              style={{ top: rect.top - PAD, left: rect.left - PAD, width: rect.width + PAD * 2, height: rect.height + PAD * 2 }}
            />
          ) : (
            <div className="tour-dim" />
          )}
          <div className="tour-card" style={cardStyle}>
            <div className="tour-progress">
              <span>{i + 1} / {steps.length}</span>
              <button className="linkbtn" onClick={close}>Skip tour</button>
            </div>
            <h3>{step.title}</h3>
            <p>{step.body}</p>
            <div className="tour-actions">
              <button className="btn secondary small" onClick={prev} disabled={i === 0}>Back</button>
              <button className="btn small" onClick={next}>{last ? 'Finish' : 'Next'}</button>
            </div>
          </div>
        </div>
      )}
    </TourCtx.Provider>
  )
}
