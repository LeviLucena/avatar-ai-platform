import { useEffect, useRef, useState } from 'react'
import Markdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { api } from '../api'
import { useAuth } from '../auth'
import { Engine, Page } from '../ui'

type Trace = { tool: string; ok: boolean; error?: string; rows?: number }
type Msg = { role: 'user' | 'assistant'; content: string; trace?: Trace[]; engine?: string }

const SUGGEST: Record<string, string[]> = {
  operations: ['Which items are below reorder point?', 'Defect rate and yield for the last 14 days', 'Which purchase orders are late?', 'Show production for lot CC-2611-B'],
  quality: ['Production data for lot CC-2611-B', 'Open recurring issues this week', 'What is the procedure for a foreign object complaint?'],
  finance: ['Show overdue invoices', 'Which purchase orders are open?', 'Sales by customer last 30 days'],
  sales: ['Sales by product last 30 days', 'Revenue by customer', 'Show overdue invoices'],
  support: ['Complaint statistics for the last 7 days', 'What is the refund policy?', 'Show overdue invoices'],
  executive: ['Summarize complaints and recurring issues this week', 'Which items are below reorder point?', 'Show overdue invoices', 'Revenue by product'],
  admin: ['Which items are below reorder point?', 'Complaint statistics this week', 'Show overdue invoices'],
}

export default function Assistant() {
  const { user } = useAuth()
  const [msgs, setMsgs] = useState<Msg[]>([])
  const [q, setQ] = useState('')
  const [busy, setBusy] = useState(false)
  const [tools, setTools] = useState<string[]>([])
  const end = useRef<HTMLDivElement>(null)
  useEffect(() => { api('/ops/tools').then((t) => setTools(t.allowed)) }, [])
  useEffect(() => { end.current?.scrollIntoView({ behavior: 'smooth' }) }, [msgs, busy])

  const ask = async (text: string) => {
    if (!text.trim() || busy) return
    const history = msgs.map((m) => ({ role: m.role, content: m.content }))
    setMsgs((m) => [...m, { role: 'user', content: text }]); setQ(''); setBusy(true)
    try {
      const r = await api('/ops/ask', { body: { question: text, history } })
      setMsgs((m) => [...m, { role: 'assistant', content: r.answer, trace: r.trace, engine: r.engine }])
    } catch (e) {
      setMsgs((m) => [...m, { role: 'assistant', content: `⚠ ${(e as Error).message}` }])
    } finally { setBusy(false) }
  }

  return (
    <Page title="Ops assistant" sub="An agent that answers from live company data through permissioned, read-only tools — no free-form SQL">
      <div className="split" style={{ gridTemplateColumns: 'minmax(0,1fr) 280px' }}>
        <div className="card" data-tour="assistant">
          <div className="chat">
            {msgs.length === 0 && (
              <div>
                <p className="muted">Ask about inventory, production, sales, invoices, purchase orders, complaints or procedures. Try:</p>
                <div className="chips">{(SUGGEST[user!.role] ?? SUGGEST.admin).map((s) => <button key={s} className="chip" onClick={() => ask(s)}>{s}</button>)}</div>
              </div>
            )}
            {msgs.map((m, i) => (
              <div key={i} className={`bubble ${m.role === 'user' ? 'user' : 'bot'}`}>
                {m.role === 'user' ? m.content : <Markdown remarkPlugins={[remarkGfm]}>{m.content}</Markdown>}
                {m.trace && m.trace.length > 0 && (
                  <div className="trace">
                    {m.trace.map((t, k) => <span key={k} className={t.ok ? '' : 'bad'} title={t.error}>{t.ok ? '⚙' : '⛔'} {t.tool}{t.ok ? '' : ' denied'}</span>)}
                    {m.engine && <Engine e={m.engine} />}
                  </div>
                )}
              </div>
            ))}
            {busy && <div className="bubble bot dots">Thinking<span>.</span><span>.</span><span>.</span></div>}
            <div ref={end} />
          </div>
          <form className="row" onSubmit={(e) => { e.preventDefault(); ask(q) }} style={{ marginTop: 8 }}>
            <input type="text" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Ask a question…" style={{ flex: 1 }} />
            <button className="btn" disabled={busy || !q.trim()}>Ask</button>
          </form>
        </div>
        <div className="card">
          <h3>Tools your role can use</h3>
          <p className="small muted">The tool list is filtered by role before it reaches the model, and re-checked on every call.</p>
          <ul style={{ paddingLeft: 18, margin: 0 }}>{tools.map((t) => <li key={t} className="small"><code>{t}</code></li>)}</ul>
          <p className="small muted" style={{ marginTop: 12 }}>Switch role (sign out → another demo account) and ask the same question to see access control in action.</p>
        </div>
      </div>
    </Page>
  )
}
