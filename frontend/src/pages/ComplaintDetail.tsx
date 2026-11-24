import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api, fmtDate } from '../api'
import { useAuth } from '../auth'
import { CatLabel, Engine, ErrorBox, Loading, Page, SevBadge, StatusBadge } from '../ui'

export default function ComplaintDetail() {
  const { id } = useParams()
  const nav = useNavigate()
  const { user } = useAuth()
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [c, setC] = useState<any>(null)
  const [draft, setDraft] = useState('')
  const [err, setErr] = useState('')
  const [msg, setMsg] = useState('')
  const [busy, setBusy] = useState(false)

  const load = useCallback(() => {
    api(`/complaints/${id}`).then((r) => { setC(r); setDraft(r.draft_response) }).catch((e) => setErr(e.message))
  }, [id])
  useEffect(() => { load() }, [load])

  // while the pipeline is still working on a fresh complaint, poll until it is triaged
  useEffect(() => {
    if (!c || c.status !== 'new') return
    const t = setTimeout(load, 1500)
    return () => clearTimeout(t)
  }, [c, load])

  if (err) return <ErrorBox error={err} />
  if (!c) return <Loading />

  const canEdit = ['support', 'quality', 'admin'].includes(user!.role) && c.status !== 'sent'
  const needsQuality = ['high', 'critical'].includes(c.severity) && !['quality', 'admin'].includes(user!.role)

  const run = async (fn: () => Promise<unknown>, ok: string) => {
    setBusy(true); setMsg(''); setErr('')
    try { await fn(); setMsg(ok); load() } catch (e) { setErr((e as Error).message) } finally { setBusy(false) }
  }

  return (
    <Page
      title={`Complaint #${c.id}`}
      sub={`${c.source === 'email' ? 'Email' : 'Web form'} · ${fmtDate(c.received_at)} · ${c.customer_name || 'Unknown'} <${c.customer_email}>`}
      actions={<><button className="btn secondary" onClick={() => nav(-1)}>← Back</button><StatusBadge s={c.status} /></>}
    >
      {c.status === 'new' && <div className="callout warn" style={{ marginBottom: 14 }}>The AI pipeline is still processing this complaint…</div>}
      {c.status === 'failed' && <div className="callout crit" style={{ marginBottom: 14 }}>Processing failed: {c.error}</div>}
      {c.escalated && (
        <div className={`callout ${c.severity === 'critical' ? 'crit' : 'warn'}`} style={{ marginBottom: 14 }}>
          <b>Escalated to {c.route_to}.</b> Rules that triggered this:
          <ul>{c.escalation_reasons.map((r: string) => <li key={r}>{r}</li>)}</ul>
        </div>
      )}

      <div className="split">
        <div className="grid">
          <div className="card">
            <h2>{c.subject || '(no subject)'}</h2>
            <p className="msg">{c.body}</p>
          </div>

          <div className="card">
            <div className="row" style={{ justifyContent: 'space-between' }}><h2>AI analysis</h2><Engine e={c.engine} /></div>
            <dl className="kv">
              <dt>Category</dt><dd><CatLabel c={c.category} /></dd>
              <dt>Severity</dt><dd><SevBadge s={c.severity} /> {c.health_risk && <span className="badge critical">health risk</span>}</dd>
              <dt>Sentiment</dt><dd>{c.sentiment > 0.2 ? '🙂 positive' : c.sentiment < -0.2 ? '😠 negative' : '😐 neutral'} ({c.sentiment})</dd>
              <dt>Product</dt><dd>{c.product ?? '—'}</dd>
              <dt>Lot code</dt><dd>{c.lot_code ? <Link to={`/complaints?lot=${c.lot_code}`}>{c.lot_code}</Link> : '—'}</dd>
              <dt>Summary</dt><dd>{c.summary}</dd>
              <dt>Issue cluster</dt><dd>{c.issue ? <Link to={`/issues/${c.issue.id}`}>{c.issue.title} · {c.issue.count} complaints</Link> : '—'}</dd>
            </dl>
            {c.lot_production && (
              <div className="callout" style={{ marginTop: 12 }}>
                <b>Manufacturing record for lot {c.lot_production.lot}</b><br />
                Produced {c.lot_production.date} on {c.lot_production.line} ({c.lot_production.facility}) · {c.lot_production.produced.toLocaleString()} units ·
                defect rate <b>{c.lot_production.defect_rate_pct}%</b>
              </div>
            )}
          </div>

          {c.similar.length > 0 && (
            <div className="card">
              <h2>Similar complaints</h2>
              <table><tbody>
                {/* eslint-disable-next-line @typescript-eslint/no-explicit-any */}
                {c.similar.map((s: any) => (
                  <tr key={s.id} className="click" onClick={() => nav(`/complaints/${s.id}`)}>
                    <td>#{s.id}</td><td>{s.summary}<div className="muted small">{s.lot_code}</div></td><td className="num">{Math.round(s.score * 100)}%</td>
                  </tr>
                ))}
              </tbody></table>
            </div>
          )}
        </div>

        <div className="card">
          <h2>Draft reply</h2>
          {c.draft_flags.length > 0 && <div className="callout warn" style={{ marginBottom: 10 }}>Guardrails: {c.draft_flags.join('; ')}</div>}
          <textarea value={draft} onChange={(e) => setDraft(e.target.value)} readOnly={!canEdit} style={{ minHeight: 260 }} />
          {c.draft_citations.length > 0 && (
            <p className="small muted">Grounded in: {/* eslint-disable-next-line @typescript-eslint/no-explicit-any */}
              {c.draft_citations.map((x: any) => `${x.doc} › ${x.heading}`).join(' · ')}</p>
          )}
          {c.status === 'sent' ? (
            <div className="callout">✅ Sent (simulated) on {fmtDate(c.sent_at)} · approved by {c.approved_by}</div>
          ) : canEdit ? (
            <>
              <div className="row" style={{ marginTop: 8 }}>
                <button className="btn secondary" disabled={busy || draft === c.draft_response} onClick={() => run(() => api(`/complaints/${c.id}`, { method: 'PATCH', body: { draft_response: draft } }), 'Draft saved')}>Save draft</button>
                <button className="btn" disabled={busy || needsQuality} onClick={() => run(async () => {
                  if (draft !== c.draft_response) await api(`/complaints/${c.id}`, { method: 'PATCH', body: { draft_response: draft } })
                  await api(`/complaints/${c.id}/approve`, { method: 'POST', body: {} })
                }, 'Approved and sent')}>Approve &amp; send</button>
                <button className="btn secondary" disabled={busy} onClick={() => run(() => api(`/complaints/${c.id}/reprocess`, { method: 'POST', body: {} }), 'Reprocessing…')}>Re-run AI</button>
              </div>
              {needsQuality && <p className="small muted">High/critical replies must be approved by the Quality role. Sign in as quality@demo.local to approve.</p>}
              <p className="small muted">Replies are never sent automatically: a human always approves. Outbound email is simulated in this demo.</p>
            </>
          ) : <p className="small muted">Your role can read this complaint but not edit or send replies.</p>}
          {msg && <div className="callout" style={{ marginTop: 10 }}>✓ {msg}</div>}
        </div>
      </div>
    </Page>
  )
}
