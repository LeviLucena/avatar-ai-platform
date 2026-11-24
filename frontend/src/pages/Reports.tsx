import { useCallback, useEffect, useState } from 'react'
import Markdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { api, fmtDate } from '../api'
import { useAuth } from '../auth'
import { Engine, ErrorBox, Loading, Page } from '../ui'

export default function Reports() {
  const { user } = useAuth()
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [list, setList] = useState<any[] | null>(null)
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [rep, setRep] = useState<any>(null)
  const [err, setErr] = useState('')
  const [busy, setBusy] = useState(false)
  const [days, setDays] = useState(7)

  const open = useCallback((id: number) => { api(`/reports/${id}`).then(setRep).catch((e) => setErr(e.message)) }, [])
  const load = useCallback((selectFirst = false) => {
    api('/reports').then((r) => { setList(r); if (selectFirst && r.length) open(r[0].id) }).catch((e) => setErr(e.message))
  }, [open])
  useEffect(() => { load(true) }, [load])

  const generate = async () => {
    setBusy(true); setErr('')
    try {
      const { job_id } = await api('/reports/generate', { body: { days } })
      for (let n = 0; n < 60; n++) {
        const j = await api(`/jobs/${job_id}`)
        if (j.status === 'done') { load(false); open(j.result.report_id); break }
        if (j.status === 'failed') throw new Error(j.error)
        await new Promise((r) => setTimeout(r, 1000))
      }
      load(false)
    } catch (e) { setErr((e as Error).message) } finally { setBusy(false) }
  }

  if (!list) return <Loading />
  const canGen = ['quality', 'executive', 'admin'].includes(user!.role)
  return (
    <Page title="Management reports" sub="Numbers computed in code; the AI only writes the narrative. A new report is also generated every Monday."
      actions={canGen && <>
        <select value={days} onChange={(e) => setDays(+e.target.value)} style={{ width: 130 }}><option value={7}>Last 7 days</option><option value={14}>Last 14 days</option><option value={30}>Last 30 days</option></select>
        <button className="btn" data-tour="generate" disabled={busy} onClick={generate}>{busy ? 'Generating…' : 'Generate report'}</button></>}>
      {err && <ErrorBox error={err} />}
      <div className="split" style={{ gridTemplateColumns: '280px minmax(0,1fr)' }}>
        <div className="card" style={{ padding: 8 }}>
          {list.length === 0 && <p className="muted" style={{ padding: 10 }}>No reports yet.</p>}
          {list.map((r) => (
            <div key={r.id} className="item" style={{ padding: 10, cursor: 'pointer', borderBottom: '1px solid var(--cream-2)', background: rep?.id === r.id ? 'var(--cream-2)' : undefined }} onClick={() => open(r.id)}>
              <b>{r.period_start} → {r.period_end}</b>
              <div className="small muted">{r.total} complaints · {fmtDate(r.created_at)} <Engine e={r.engine} /></div>
            </div>
          ))}
        </div>
        <div className="card md" data-tour="report">
          {rep ? <Markdown remarkPlugins={[remarkGfm]}>{rep.content_md}</Markdown> : <p className="muted">Select a report.</p>}
        </div>
      </div>
    </Page>
  )
}
