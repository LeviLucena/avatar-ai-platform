import { useCallback, useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { api, fmtDate } from '../api'
import { useAuth } from '../auth'
import { ErrorBox, Loading, Page, SevBadge, StatusBadge } from '../ui'

export default function IssueDetail() {
  const { id } = useParams()
  const nav = useNavigate()
  const { user } = useAuth()
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [i, setI] = useState<any>(null)
  const [err, setErr] = useState('')
  const load = useCallback(() => { api(`/issues/${id}`).then(setI).catch((e) => setErr(e.message)) }, [id])
  useEffect(() => { load() }, [load])
  if (err) return <ErrorBox error={err} />
  if (!i) return <Loading />
  const setStatus = async (status: string) => { await api(`/issues/${id}`, { method: 'PATCH', body: { status } }); load() }
  return (
    <Page title={i.title} sub={`${i.count} complaints · first seen ${fmtDate(i.first_seen)} · last ${fmtDate(i.last_seen)}`}
      actions={<><button className="btn secondary" onClick={() => nav(-1)}>← Back</button><SevBadge s={i.max_severity} />
        {['quality', 'admin'].includes(user!.role) && (
          <select value={i.status} onChange={(e) => setStatus(e.target.value)} style={{ width: 160 }}>
            <option value="open">open</option><option value="investigating">investigating</option><option value="resolved">resolved</option>
          </select>)}</>}>
      <div className="grid g2">
        <div className="card">
          <h2>Complaints over time</h2>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={i.timeline.map((t: { date: string; count: number }) => ({ ...t, label: t.date.slice(5) }))}>
              <CartesianGrid strokeDasharray="3 3" stroke="#eee6d2" /><XAxis dataKey="label" tick={{ fontSize: 11 }} />
              <YAxis allowDecimals={false} tick={{ fontSize: 11 }} /><Tooltip /><Bar dataKey="count" fill="#d9622b" radius={[6, 6, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
        <div className="card" data-tour="lot-production">
          <h2>Production records for affected lots</h2>
          {i.production.length === 0 ? <p className="muted">No lot codes linked to this issue yet.</p> : (
            <table>
              <thead><tr><th>Lot</th><th>Line</th><th>Date</th><th className="num">Units</th><th className="num">Defects</th></tr></thead>
              <tbody>{/* eslint-disable-next-line @typescript-eslint/no-explicit-any */}
                {i.production.map((p: any, k: number) => (
                  <tr key={k}><td>{p.lot}</td><td>{p.line}</td><td>{p.date}</td><td className="num">{p.produced.toLocaleString()}</td>
                    <td className="num"><b style={{ color: p.defect_rate_pct > 2 ? 'var(--sev-critical)' : undefined }}>{p.defect_rate_pct}%</b></td></tr>
                ))}
              </tbody>
            </table>
          )}
          <p className="small muted">Plant defect rate is normally ≈1%. A higher rate on a complained-about lot supports a stock hold.</p>
        </div>
      </div>
      <div className="card" style={{ marginTop: 16, padding: 8 }}>
        <h2 style={{ padding: '8px 10px 0' }}>Complaints in this cluster</h2>
        <table>
          <thead><tr><th>#</th><th>Received</th><th>Summary</th><th>Lot</th><th>Severity</th><th>Status</th></tr></thead>
          <tbody>{/* eslint-disable-next-line @typescript-eslint/no-explicit-any */}
            {i.complaints.map((c: any) => (
              <tr key={c.id} className="click" onClick={() => nav(`/complaints/${c.id}`)}>
                <td>{c.id}</td><td className="small">{fmtDate(c.received_at)}</td><td>{c.summary}</td><td className="small">{c.lot_code}</td>
                <td><SevBadge s={c.severity} /></td><td><StatusBadge s={c.status} /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Page>
  )
}
