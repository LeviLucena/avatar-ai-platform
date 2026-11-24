import { useEffect, useState, type FormEvent } from 'react'
import { Navigate } from 'react-router-dom'
import { api } from '../api'
import { useAuth } from '../auth'

export default function Login() {
  const { user, login } = useAuth()
  const [email, setEmail] = useState('quality@demo.local')
  const [password, setPassword] = useState('demo1234')
  const [err, setErr] = useState('')
  const [busy, setBusy] = useState(false)
  const [demo, setDemo] = useState<{ email: string; name: string; role: string }[]>([])

  useEffect(() => { api('/auth/demo-users').then((d) => setDemo(d.users)).catch(() => {}) }, [])
  if (user) return <Navigate to="/" replace />

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    setBusy(true); setErr('')
    try { await login(email, password) } catch (x) { setErr((x as Error).message) } finally { setBusy(false) }
  }

  return (
    <div className="login-wrap">
      <div className="login">
        <div className="hero">
          <div>
            <div className="chips" style={{ marginBottom: 18 }}><span className="badge engine claude">✦ Nemotron-powered</span><span className="badge engine">Concept demo</span></div>
            <h1>Customer quality, from inbox to insight.</h1>
            <p style={{ opacity: 0.85, lineHeight: 1.55 }}>Complaints arrive by email and web form. AI agents classify them, spot recurring failures, draft replies from company policy, escalate critical cases and brief management every week.</p>
          </div>
          <p className="disclaimer">Independent portfolio project with fictional data. Not affiliated with any company.</p>
        </div>
        <form className="form" onSubmit={submit}>
          <h2 style={{ marginBottom: 16 }}>Sign in</h2>
          <div className="field"><label>Email</label><input type="email" value={email} onChange={(e) => setEmail(e.target.value)} /></div>
          <div className="field"><label>Password</label><input type="password" value={password} onChange={(e) => setPassword(e.target.value)} /></div>
          {err && <div className="callout crit" style={{ marginBottom: 12 }}>{err}</div>}
          <button className="btn" disabled={busy} style={{ width: '100%' }}>{busy ? 'Signing in…' : 'Sign in'}</button>
          <p className="muted small" style={{ marginTop: 18 }}>Demo accounts (password <code>demo1234</code>). Each role sees different data:</p>
          <div className="chips">
            {demo.map((d) => <button type="button" key={d.email} className="chip" onClick={() => { setEmail(d.email); setPassword('demo1234') }}>{d.role}</button>)}
          </div>
          <p className="small" style={{ marginTop: 18 }}><a href="/contact">Preview the public customer contact form →</a></p>
        </form>
      </div>
    </div>
  )
}
