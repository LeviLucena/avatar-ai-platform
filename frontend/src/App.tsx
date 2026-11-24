import { useState, type ReactNode } from 'react'
import { Navigate, NavLink, Outlet, Route, Routes, useNavigate } from 'react-router-dom'
import { api, fmtDate } from './api'
import { can, useAuth } from './auth'
import { Loading, usePoll } from './ui'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Complaints from './pages/Complaints'
import ComplaintDetail from './pages/ComplaintDetail'
import Issues from './pages/Issues'
import IssueDetail from './pages/IssueDetail'
import Reports from './pages/Reports'
import Assistant from './pages/Assistant'
import Knowledge from './pages/Knowledge'
import Intake from './pages/Intake'
import Admin from './pages/Admin'
import PublicContact from './pages/PublicContact'

function Bell() {
  const [open, setOpen] = useState(false)
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [data, setData] = useState<any>({ unread: 0, items: [] })
  const nav = useNavigate()
  usePoll(() => { api('/notifications').then(setData).catch(() => {}) }, 6000)
  const markRead = async () => {
    await api('/notifications/read-all', { method: 'POST', body: {} })
    setData({ ...data, unread: 0, items: data.items.map((i: object) => ({ ...i, read: true })) })
  }
  return (
    <div className="bell">
      <button className="btn secondary" onClick={() => setOpen(!open)} aria-label="Notifications">🔔{data.unread > 0 && <span className="dot">{data.unread}</span>}</button>
      {open && (
        <div className="dropdown">
          <div className="row" style={{ justifyContent: 'space-between', padding: '10px 14px' }}>
            <b>Notifications</b>
            <button className="linkbtn" style={{ color: 'var(--green-600)' }} onClick={markRead}>Mark all read</button>
          </div>
          {data.items.length === 0 && <div className="muted small" style={{ padding: 14 }}>Nothing for your role yet.</div>}
          {/* eslint-disable-next-line @typescript-eslint/no-explicit-any */}
          {data.items.map((n: any) => (
            <div key={n.id} className={`item ${n.read ? '' : 'unread'}`} onClick={() => { setOpen(false); if (n.complaint_id) nav(`/complaints/${n.complaint_id}`) }}>
              <div><span className={`badge ${n.level === 'critical' ? 'critical' : n.level === 'warning' ? 'high' : ''}`}>{n.level}</span> <b>{n.title}</b></div>
              <div className="muted small">{n.body}</div>
              <div className="muted small">{fmtDate(n.created_at)}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function Layout() {
  const { user, logout } = useAuth()
  const role = user!.role
  const link = (to: string, label: string, icon: string, section?: string) =>
    (!section || can(role, section)) && <NavLink to={to} end={to === '/'}>{icon} {label}</NavLink>
  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">
            <svg width="22" height="22" viewBox="0 0 32 32"><path d="M6 25c0-10 7-16 20-16-1 11-7 18-20 16z" fill="#6ba368" /><path d="M6 25c4-7 9-11 15-13" stroke="#fbf7ee" strokeWidth="2" fill="none" /></svg>
          </div>
          <div><b>Quality AI</b><small>Concept demo</small></div>
        </div>
        <nav className="nav">
          {link('/', 'Dashboard', '▦')}
          {link('/complaints', 'Complaints', '✉', 'complaints')}
          {link('/issues', 'Quality issues', '⚠', 'issues')}
          {link('/reports', 'Reports', '▤', 'reports')}
          {link('/assistant', 'Ops assistant', '✦')}
          {link('/knowledge', 'Knowledge base', '§')}
          {link('/intake', 'Intake & simulate', '⇪', 'intake')}
          {link('/admin', 'Admin & audit', '⚙', 'admin')}
        </nav>
        <div className="spacer" />
        <div className="userbox">
          <div><b>{user!.name}</b></div>
          <div className="role">{role}</div>
          <button className="linkbtn" onClick={logout}>Sign out</button>
          <p className="disclaimer">Independent concept demo with fictional data. Not affiliated with, or endorsed by, any company. Colors are inspired by natural-food branding, not an official palette.</p>
        </div>
      </aside>
      <main className="main">
        <div className="row" style={{ justifyContent: 'flex-end', marginBottom: 6 }}><Bell /></div>
        <Outlet />
      </main>
    </div>
  )
}

function Protected({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth()
  if (loading) return <div className="main"><Loading /></div>
  if (!user) return <Navigate to="/login" replace />
  return <>{children}</>
}

function Guard({ section, children }: { section: string; children: ReactNode }) {
  const { user } = useAuth()
  if (!can(user?.role, section)) return <div className="callout warn">Your role (<b>{user?.role}</b>) does not have access to this section.</div>
  return <>{children}</>
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/contact" element={<PublicContact />} />
      <Route element={<Protected><Layout /></Protected>}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/complaints" element={<Guard section="complaints"><Complaints /></Guard>} />
        <Route path="/complaints/:id" element={<Guard section="complaints"><ComplaintDetail /></Guard>} />
        <Route path="/issues" element={<Guard section="issues"><Issues /></Guard>} />
        <Route path="/issues/:id" element={<Guard section="issues"><IssueDetail /></Guard>} />
        <Route path="/reports" element={<Guard section="reports"><Reports /></Guard>} />
        <Route path="/assistant" element={<Assistant />} />
        <Route path="/knowledge" element={<Knowledge />} />
        <Route path="/intake" element={<Guard section="intake"><Intake /></Guard>} />
        <Route path="/admin" element={<Guard section="admin"><Admin /></Guard>} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
