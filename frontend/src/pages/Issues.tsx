import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, fmtDate } from '../api'
import { CatLabel, ErrorBox, Loading, Page, SevBadge, usePoll } from '../ui'

export default function Issues() {
  const nav = useNavigate()
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [rows, setRows] = useState<any[] | null>(null)
  const [err, setErr] = useState('')
  const [showAll, setShowAll] = useState(false)
  usePoll(() => { api('/issues').then(setRows).catch((e) => setErr(e.message)) }, 8000)
  if (err) return <ErrorBox error={err} />
  if (!rows) return <Loading />
  const list = showAll ? rows : rows.filter((r) => r.count >= 3 || ['critical', 'high'].includes(r.max_severity))
  return (
    <Page title="Quality issues" sub="Complaints clustered by meaning, product and lot: recurring failures surface here"
      actions={<label className="row small" style={{ margin: 0 }}><input type="checkbox" checked={showAll} onChange={(e) => setShowAll(e.target.checked)} /> include small clusters</label>}>
      <div className="card" style={{ padding: 8 }}>
        <table>
          <thead><tr><th>Issue</th><th>Category</th><th>Lots</th><th className="num">Complaints</th><th>Severity</th><th>Last seen</th><th>Status</th></tr></thead>
          <tbody>
            {list.map((i) => (
              <tr key={i.id} className="click" onClick={() => nav(`/issues/${i.id}`)}>
                <td><b>{i.title}</b></td><td className="small"><CatLabel c={i.category} /></td>
                <td className="small">{i.lots.join(', ') || '—'}</td><td className="num">{i.count}</td>
                <td><SevBadge s={i.max_severity} /></td><td className="small">{fmtDate(i.last_seen)}</td><td><span className="badge">{i.status}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Page>
  )
}
