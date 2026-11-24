import { useState, type FormEvent } from 'react'
import { api } from '../api'

/** Public, unauthenticated page: what a company website's "Contact us" form would look like. */
export default function PublicContact() {
  const [f, setF] = useState({ name: '', email: '', subject: '', message: '' })
  const [done, setDone] = useState(false)
  const [err, setErr] = useState('')
  const [busy, setBusy] = useState(false)
  const submit = async (e: FormEvent) => {
    e.preventDefault(); setBusy(true); setErr('')
    try { await api('/ingest/web', { body: f }); setDone(true) } catch (x) { setErr((x as Error).message) } finally { setBusy(false) }
  }
  return (
    <div className="login-wrap">
      <div className="card" style={{ width: 'min(560px,100%)', padding: 28 }}>
        <div className="chips" style={{ marginBottom: 12 }}><span className="badge engine">Demo customer page</span></div>
        <h1>Tell us what happened</h1>
        <p className="muted">Your message goes straight to our Customer Care team. Please include the product name and the lot code printed on the package if you can.</p>
        {done ? (
          <div className="callout" style={{ marginTop: 14 }}>✅ Thank you, we received your message and will be in touch soon. <div className="small muted" style={{ marginTop: 6 }}><a href="/login">Staff sign-in</a></div></div>
        ) : (
          <form onSubmit={submit} style={{ marginTop: 14 }}>
            <div className="field"><label>Your name</label><input type="text" required value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} /></div>
            <div className="field"><label>Email</label><input type="email" required value={f.email} onChange={(e) => setF({ ...f, email: e.target.value })} /></div>
            <div className="field"><label>Subject</label><input type="text" value={f.subject} onChange={(e) => setF({ ...f, subject: e.target.value })} /></div>
            <div className="field"><label>Message</label><textarea required minLength={10} value={f.message} onChange={(e) => setF({ ...f, message: e.target.value })} /></div>
            {err && <div className="callout crit" style={{ marginBottom: 10 }}>{err}</div>}
            <button className="btn" disabled={busy}>{busy ? 'Sending…' : 'Send'}</button>
          </form>
        )}
        <p className="disclaimer muted" style={{ marginTop: 18 }}>Independent concept demo with fictional data. Not affiliated with any company.</p>
      </div>
    </div>
  )
}
