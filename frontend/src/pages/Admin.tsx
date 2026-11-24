import { useState } from 'react'
import { api, fmtDate } from '../api'
import { ErrorBox, Loading, Page, usePoll } from '../ui'

type Tab = 'audit' | 'jobs' | 'users' | 'system'

export default function Admin() {
  const [tab, setTab] = useState<Tab>('audit')
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [rows, setRows] = useState<any>(null)
  const [err, setErr] = useState('')
  const path = { audit: '/admin/audit?limit=120', jobs: '/admin/jobs', users: '/admin/users', system: '/system' }[tab]
  usePoll(() => { api(path).then(setRows).catch((e) => setErr(e.message)) }, 5000, [tab])
  const go = (t: Tab) => { setRows(null); setTab(t) }
  if (err) return <ErrorBox error={err} />
  return (
    <Page title="Admin & audit" sub="Who did what, background jobs and platform health">
      <div className="tabs">{(['audit', 'jobs', 'users', 'system'] as Tab[]).map((t) => <button key={t} className={`tab ${tab === t ? 'on' : ''}`} onClick={() => go(t)}>{t}</button>)}</div>
      {!rows ? <Loading /> : (
        <div className="card" style={{ padding: 8 }}>
          {tab === 'audit' && (
            <table><thead><tr><th>Time</th><th>Actor</th><th>Action</th><th>Detail</th></tr></thead><tbody>
              {/* eslint-disable-next-line @typescript-eslint/no-explicit-any */}
              {rows.map((r: any) => <tr key={r.id}><td className="small">{fmtDate(r.ts)}</td><td className="small">{r.actor}</td><td><code>{r.action}</code></td><td className="small muted">{JSON.stringify(r.detail)}</td></tr>)}
            </tbody></table>
          )}
          {tab === 'jobs' && (
            <table><thead><tr><th>#</th><th>Kind</th><th>Status</th><th>Attempts</th><th>Created</th><th>Error</th></tr></thead><tbody>
              {/* eslint-disable-next-line @typescript-eslint/no-explicit-any */}
              {rows.map((r: any) => <tr key={r.id}><td>{r.id}</td><td><code>{r.kind}</code></td><td><span className={`badge ${r.status === 'failed' ? 'critical' : ''}`}>{r.status}</span></td><td>{r.attempts}</td><td className="small">{fmtDate(r.created_at)}</td><td className="small">{r.error}</td></tr>)}
            </tbody></table>
          )}
          {tab === 'users' && (
            <table><thead><tr><th>Name</th><th>Email</th><th>Role</th></tr></thead><tbody>
              {/* eslint-disable-next-line @typescript-eslint/no-explicit-any */}
              {rows.map((r: any) => <tr key={r.id}><td>{r.name}</td><td>{r.email}</td><td><span className="badge">{r.role}</span></td></tr>)}
            </tbody></table>
          )}
          {tab === 'system' && (
            <dl className="kv" style={{ padding: 14 }}>
              <dt>LLM engine</dt><dd><b>{rows.engine}</b> {rows.engine === 'heuristic' && <span className="muted">(set NVIDIA_API_KEY in backend/.env to use Nemotron)</span>}</dd>
              <dt>Fast model</dt><dd>{rows.model_fast}</dd><dt>Smart model</dt><dd>{rows.model_smart}</dd>
              <dt>Complaints</dt><dd>{rows.complaints}</dd><dt>Queued jobs</dt><dd>{rows.queued_jobs}</dd>
              <dt>Note</dt><dd>{rows.disclaimer}</dd>
            </dl>
          )}
        </div>
      )}
    </Page>
  )
}
