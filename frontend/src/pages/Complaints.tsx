import { useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { api, CATEGORY_LABEL, fmtDate } from '../api'
import { CatLabel, Engine, ErrorBox, Loading, Page, SevBadge, StatusBadge, usePoll } from '../ui'

export default function Complaints() {
  const nav = useNavigate()
  const [sp, setSp] = useSearchParams()
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [data, setData] = useState<any>(null)
  const [err, setErr] = useState('')
  const [page, setPage] = useState(1)
  const f = { severity: sp.get('severity') ?? '', status: sp.get('status') ?? '', category: sp.get('category') ?? '', q: sp.get('q') ?? '', lot: sp.get('lot') ?? '' }
  const set = (k: string, v: string) => { const n = new URLSearchParams(sp); v ? n.set(k, v) : n.delete(k); setSp(n); setPage(1) }

  usePoll(() => {
    const qs = new URLSearchParams({ page: String(page), page_size: '20' })
    Object.entries(f).forEach(([k, v]) => v && qs.set(k, v))
    api(`/complaints?${qs}`).then(setData).catch((e) => setErr(e.message))
  }, 5000, [sp, page])

  if (err) return <ErrorBox error={err} />
  return (
    <Page title="Complaints" sub="Every message that reached the inbox or the website form, triaged by AI">
      <div className="card" style={{ marginBottom: 14 }}>
        <div className="row">
          <input type="text" placeholder="Search text, subject, customer…" value={f.q} onChange={(e) => set('q', e.target.value)} style={{ flex: 2, minWidth: 220 }} />
          <select value={f.severity} onChange={(e) => set('severity', e.target.value)} style={{ flex: 1, minWidth: 130 }}>
            <option value="">All severities</option>{['critical', 'high', 'medium', 'low'].map((s) => <option key={s}>{s}</option>)}
          </select>
          <select value={f.status} onChange={(e) => set('status', e.target.value)} style={{ flex: 1, minWidth: 130 }}>
            <option value="">All statuses</option>{['new', 'escalated', 'draft_ready', 'sent', 'failed'].map((s) => <option key={s}>{s}</option>)}
          </select>
          <select value={f.category} onChange={(e) => set('category', e.target.value)} style={{ flex: 1, minWidth: 160 }}>
            <option value="">All categories</option>{Object.entries(CATEGORY_LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
          {f.lot && <span className="badge engine">lot {f.lot} <button className="linkbtn" onClick={() => set('lot', '')}>✕</button></span>}
        </div>
      </div>
      <div className="card" style={{ padding: 8 }}>
        {!data ? <Loading /> : (
          <>
            <table>
              <thead><tr><th>#</th><th>Received</th><th>Summary</th><th>Category</th><th>Product / lot</th><th>Severity</th><th>Status</th><th>AI</th></tr></thead>
              <tbody>
                {/* eslint-disable-next-line @typescript-eslint/no-explicit-any */}
                {data.items.map((c: any) => (
                  <tr key={c.id} className="click" onClick={() => nav(`/complaints/${c.id}`)}>
                    <td>{c.id}</td>
                    <td className="small">{fmtDate(c.received_at)}<div className="muted">{c.source}</div></td>
                    <td style={{ maxWidth: 340 }}><b>{c.customer_name || c.customer_email}</b><div className="muted small">{c.summary || c.subject}</div></td>
                    <td className="small"><CatLabel c={c.category} /></td>
                    <td className="small">{c.product ?? '—'}<div className="muted">{c.lot_code}</div></td>
                    <td><SevBadge s={c.severity} />{c.escalated && <div className="small muted">↑ {c.route_to}</div>}</td>
                    <td><StatusBadge s={c.status} /></td>
                    <td><Engine e={c.engine} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
            {data.items.length === 0 && <div className="muted" style={{ padding: 20 }}>No complaints match these filters.</div>}
            <div className="row" style={{ justifyContent: 'space-between', padding: '10px 12px' }}>
              <span className="muted small">{data.total} total</span>
              <div className="row">
                <button className="btn secondary small" disabled={page <= 1} onClick={() => setPage(page - 1)}>← Prev</button>
                <span className="small">Page {page}</span>
                <button className="btn secondary small" disabled={page * 20 >= data.total} onClick={() => setPage(page + 1)}>Next →</button>
              </div>
            </div>
          </>
        )}
      </div>
    </Page>
  )
}
