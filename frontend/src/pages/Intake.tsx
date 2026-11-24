import { useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api'
import { ErrorBox, Page } from '../ui'

export default function Intake() {
  const nav = useNavigate()
  const [n, setN] = useState(5)
  const [msg, setMsg] = useState('')
  const [err, setErr] = useState('')
  const [busy, setBusy] = useState(false)
  const file = useRef<HTMLInputElement>(null)

  const wrap = async (fn: () => Promise<{ ids: number[] }>) => {
    setBusy(true); setErr(''); setMsg('')
    try {
      const r = await fn()
      setMsg(`${r.ids.length} complaint(s) queued. The background worker is classifying them now: open the inbox to watch them appear.`)
    } catch (e) { setErr((e as Error).message) } finally { setBusy(false) }
  }
  return (
    <Page title="Intake & simulation" sub="Three ways complaints enter the system. Each one goes through the same queue and the same AI pipeline.">
      {err && <ErrorBox error={err} />}
      {msg && <div className="callout" style={{ marginBottom: 14 }}>✓ {msg} <button className="linkbtn" style={{ color: 'var(--green-600)' }} onClick={() => nav('/complaints')}>Open inbox →</button></div>}
      <div className="grid g3">
        <div className="card">
          <h2>1 · Simulate incoming mail</h2>
          <p className="muted small">Generates random, realistic (fictional) complaints, including the occasional critical one.</p>
          <div className="row"><input type="text" value={n} onChange={(e) => setN(Math.max(1, Math.min(50, +e.target.value || 1)))} style={{ width: 80 }} />
            <button className="btn" disabled={busy} onClick={() => wrap(() => api(`/ingest/simulate?n=${n}`, { method: 'POST', body: {} }))}>Simulate</button></div>
        </div>
        <div className="card">
          <h2>2 · Upload .eml files</h2>
          <p className="muted small">Export messages from any mail client and drop them here. Sender, subject and body are parsed automatically.</p>
          <input ref={file} type="file" accept=".eml,message/rfc822" multiple />
          <div style={{ marginTop: 10 }}>
            <button className="btn" disabled={busy} onClick={() => {
              const fl = file.current?.files
              if (!fl?.length) return setErr('Choose at least one .eml file')
              const fd = new FormData(); Array.from(fl).forEach((f) => fd.append('files', f))
              wrap(() => api('/ingest/eml', { form: fd }))
            }}>Upload</button>
          </div>
        </div>
        <div className="card">
          <h2>3 · Customer web form</h2>
          <p className="muted small">The public page a website would embed. It posts to an open endpoint with validation.</p>
          <a className="btn secondary" href="/contact" target="_blank" rel="noreferrer" style={{ display: 'inline-block', textDecoration: 'none' }}>Open public form ↗</a>
        </div>
      </div>
      <div className="card" style={{ marginTop: 16 }}>
        <h2>Email webhook (for an inbound-mail provider)</h2>
        <p className="muted small">Point your provider's inbound parse webhook here. The shared secret is set with <code>INGEST_KEY</code>.</p>
        <pre className="callout" style={{ overflowX: 'auto', margin: 0 }}>{`curl -X POST http://localhost:8000/api/ingest/email \\
  -H "X-Ingest-Key: dev-ingest-key" -H "Content-Type: application/json" \\
  -d '{"from_name":"Jane Doe","from_email":"jane@example.com",
       "subject":"Plastic in my bowl","body":"Found hard plastic in my Chipotle Chicken Bowl, lot CC-2611-B."}'`}</pre>
      </div>
    </Page>
  )
}
