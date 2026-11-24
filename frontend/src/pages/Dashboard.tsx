import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { api, SEV_COLOR } from '../api'
import { Engine, ErrorBox, Kpi, Loading, Page, SevBadge, usePoll } from '../ui'

export default function Dashboard() {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [d, setD] = useState<any>(null)
  const [err, setErr] = useState('')
  usePoll(() => { api('/dashboard').then(setD).catch((e) => setErr(e.message)) }, 8000)
  if (err) return <ErrorBox error={err} />
  if (!d) return <Loading />
  const k = d.kpis
  const canSeeComplaints = ['support', 'quality', 'executive', 'admin'].includes(d.role)

  return (
    <Page title="Dashboard" sub={`Customer quality overview · last 30 days · viewing as ${d.role}`} actions={<Engine e={d.llm_engine} />}>
      <div className="grid g4" style={{ marginBottom: 16 }}>
        <Kpi label="Complaints (30 days)" value={k.complaints_30d} />
        <Kpi label="Critical, not yet answered" value={k.critical_open} tone={k.critical_open ? 'alert' : undefined} />
        <Kpi label="Escalated, open" value={k.escalated_open} tone={k.escalated_open ? 'warn' : undefined} />
        <Kpi label="Recurring quality issues" value={k.recurring_issues} tone={k.recurring_issues ? 'warn' : undefined} />
        <Kpi label="Replies awaiting approval" value={k.awaiting_approval} />
        <Kpi label="Avg sentiment (7 days)" value={k.avg_sentiment_7d} />
        <Kpi label="Auto-triaged by AI" value={`${k.auto_triaged_pct}%`} />
        <Kpi label="Complaints (7 days)" value={k.complaints_7d} />
      </div>

      <div className="grid g2">
        <div className="card">
          <h2>Complaints per day, by severity</h2>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={d.series.map((s: { date: string }) => ({ ...s, label: s.date.slice(5) }))}>
              <CartesianGrid strokeDasharray="3 3" stroke="#eee6d2" />
              <XAxis dataKey="label" tick={{ fontSize: 11 }} interval={3} />
              <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
              <Tooltip />
              <Legend />
              {(['low', 'medium', 'high', 'critical'] as const).map((s) => <Bar key={s} dataKey={s} stackId="a" fill={SEV_COLOR[s]} />)}
            </BarChart>
          </ResponsiveContainer>
        </div>
        <div className="card">
          <h2>By category</h2>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={d.by_category} layout="vertical" margin={{ left: 30 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#eee6d2" />
              <XAxis type="number" allowDecimals={false} tick={{ fontSize: 11 }} />
              <YAxis type="category" dataKey="label" width={140} tick={{ fontSize: 11 }} />
              <Tooltip />
              <Bar dataKey="count" fill="#3f7d55" radius={[0, 6, 6, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="grid g2" style={{ marginTop: 16 }}>
        <div className="card">
          <h2>Top open quality issues</h2>
          <table>
            <thead><tr><th>Issue</th><th className="num">Complaints</th><th>Severity</th></tr></thead>
            <tbody>
              {d.top_issues.map((i: { id: number; title: string; count: number; severity: string; lots: string[] }) => (
                <tr key={i.id}>
                  <td>{canSeeComplaints ? <Link to={`/issues/${i.id}`}>{i.title}</Link> : i.title}<div className="muted small">{i.lots.join(', ')}</div></td>
                  <td className="num">{i.count}</td>
                  <td><SevBadge s={i.severity} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="card">
          <h2>Lots with most complaints</h2>
          <table>
            <thead><tr><th>Lot</th><th className="num">Complaints</th></tr></thead>
            <tbody>
              {d.top_lots.map((l: { lot: string; complaints: number }) => (
                <tr key={l.lot}><td>{canSeeComplaints ? <Link to={`/complaints?lot=${l.lot}`}>{l.lot}</Link> : l.lot}</td><td className="num">{l.complaints}</td></tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {(d.operations || d.finance) && (
        <div className="grid g2" style={{ marginTop: 16 }}>
          {d.operations && (
            <div className="card">
              <h2>Operations snapshot (14 days)</h2>
              <div className="row" style={{ gap: 28, marginBottom: 10 }}>
                <div className="kpi"><div className="v">{d.operations.defect_rate_14d_pct}%</div><div className="l">Defect rate</div></div>
                <div className="kpi"><div className="v">{d.operations.yield_14d_pct}%</div><div className="l">Yield vs plan</div></div>
                <div className="kpi"><div className="v">{d.operations.late_pos}</div><div className="l">Late POs</div></div>
              </div>
              <h3>Below reorder point</h3>
              {d.operations.low_stock_items.length === 0 ? <div className="muted small">None</div> : (
                <ul style={{ margin: '6px 0 0', paddingLeft: 18 }}>
                  {d.operations.low_stock_items.map((i: { name: string; qty: number; unit: string; reorder_point: number }) => <li key={i.name}>{i.name}: {i.qty} {i.unit} <span className="muted">(reorder at {i.reorder_point})</span></li>)}
                </ul>
              )}
            </div>
          )}
          {d.finance && (
            <div className="card">
              <h2>Finance snapshot</h2>
              <div className="row" style={{ gap: 28 }}>
                <div className="kpi"><div className="v">${Math.round(d.finance.overdue_ar_total).toLocaleString()}</div><div className="l">Overdue receivables</div></div>
                <div className="kpi"><div className="v">{d.finance.overdue_ar_count}</div><div className="l">Overdue invoices</div></div>
              </div>
              <p className="muted small">Ask the Ops assistant for the invoice list.</p>
            </div>
          )}
        </div>
      )}
    </Page>
  )
}
