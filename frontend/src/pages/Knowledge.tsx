import { useEffect, useState } from 'react'
import Markdown from 'react-markdown'
import { api } from '../api'
import { useAuth } from '../auth'
import { ErrorBox, Loading, Page } from '../ui'

export default function Knowledge() {
  const { user } = useAuth()
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [docs, setDocs] = useState<any[] | null>(null)
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [doc, setDoc] = useState<any>(null)
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [hits, setHits] = useState<any[] | null>(null)
  const [q, setQ] = useState('')
  const [err, setErr] = useState('')
  const [form, setForm] = useState({ title: '', content: '' })
  const load = () => api('/knowledge').then(setDocs).catch((e) => setErr(e.message))
  useEffect(() => { load() }, [])

  const search = async () => { if (q.trim().length > 1) setHits(await api('/knowledge/search', { body: { query: q } })) }
  const add = async () => {
    setErr('')
    try { await api('/knowledge', { body: form }); setForm({ title: '', content: '' }); load() } catch (e) { setErr((e as Error).message) }
  }
  if (!docs) return <Loading />
  return (
    <Page title="Knowledge base" sub="Company procedures and policies. Reply drafts and the assistant retrieve from these documents (RAG).">
      {err && <ErrorBox error={err} />}
      <div className="split" style={{ gridTemplateColumns: '300px minmax(0,1fr)' }}>
        <div className="grid">
          <div className="card" style={{ padding: 8 }}>
            {docs.map((d) => (
              <div key={d.id} style={{ padding: 10, cursor: 'pointer', borderBottom: '1px solid var(--cream-2)', background: doc?.id === d.id ? 'var(--cream-2)' : undefined }}
                onClick={() => api(`/knowledge/${d.id}`).then(setDoc)}>
                <b>{d.title}</b><div className="small muted">{d.chunks} chunks · {d.source}</div>
              </div>
            ))}
          </div>
          {['quality', 'admin'].includes(user!.role) && (
            <div className="card">
              <h3>Add / update a document</h3>
              <div className="field"><label>Title (same title = update)</label><input type="text" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} /></div>
              <div className="field"><label>Markdown content (use ## headings)</label><textarea value={form.content} onChange={(e) => setForm({ ...form, content: e.target.value })} /></div>
              <button className="btn" disabled={form.title.length < 3 || form.content.length < 20} onClick={add}>Save &amp; index</button>
            </div>
          )}
        </div>
        <div className="grid">
          <div className="card">
            <h3>Semantic search</h3>
            <form className="row" onSubmit={(e) => { e.preventDefault(); search() }}>
              <input type="text" value={q} onChange={(e) => setQ(e.target.value)} placeholder="e.g. customer got hives after a cookie" style={{ flex: 1 }} />
              <button className="btn">Search</button>
            </form>
            {/* eslint-disable-next-line @typescript-eslint/no-explicit-any */}
            {hits?.map((h: any, i: number) => (
              <div key={i} className="callout" style={{ marginTop: 10 }}>
                <b>{h.doc} › {h.heading}</b> <span className="muted small">score {h.score}</span>
                <div className="small msg" style={{ marginTop: 4 }}>{h.text.slice(0, 380)}{h.text.length > 380 ? '…' : ''}</div>
              </div>
            ))}
            {hits && hits.length === 0 && <p className="muted small">No relevant passages.</p>}
          </div>
          {doc && <div className="card md"><Markdown>{doc.content}</Markdown></div>}
        </div>
      </div>
    </Page>
  )
}
