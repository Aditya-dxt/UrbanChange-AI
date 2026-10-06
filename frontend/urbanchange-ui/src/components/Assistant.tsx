import { useState } from 'react'
import { api } from '../api/client'

interface Msg { role: 'user' | 'ai'; text: string; ids?: string[] }
const SUGGESTED = ['What changed?', 'When did it start?', 'How large is it?', 'Why was it flagged?']

export default function Assistant({ investigationId }: { investigationId: string }) {
  const [msgs, setMsgs] = useState<Msg[]>([]), [q, setQ] = useState(''), [busy, setBusy] = useState(false)
  async function ask(text: string) {
    if (!text.trim() || busy) return
    setMsgs(m => [...m, { role: 'user', text }]); setQ(''); setBusy(true)
    try { const r = await api.ask(investigationId, text); setMsgs(m => [...m, { role: 'ai', text: r.answer, ids: r.evidence_ids }]) }
    catch (e) { setMsgs(m => [...m, { role: 'ai', text: `Assistant unavailable: ${(e as Error).message}` }]) }
    setBusy(false)
  }
  return <div className="card"><div className="mb-1 font-semibold">Investigation assistant</div>
    <div className="mb-2 flex flex-col gap-1">{msgs.map((m, i) => m.role === 'user'
      ? <div key={i} className="text-right"><span className="pill">{m.text}</span></div>
      : <div key={i} className="card text-sm">{m.text}<div className="text-xs opacity-60">evidence: {m.ids?.join(', ') || 'none'}</div></div>)}
      {busy && <div className="text-xs opacity-60">Thinking…</div>}</div>
    <div className="flex gap-2"><input className="flex-1 rounded border bg-transparent px-2" value={q} placeholder="Why was this area flagged?" onChange={e => setQ(e.target.value)} onKeyDown={e => e.key === 'Enter' && ask(q)} />
      <button className="btn" disabled={busy} onClick={() => ask(q)}>Ask</button></div>
    <div className="mt-2 flex flex-wrap gap-1">{SUGGESTED.map(s => <button key={s} className="pill" onClick={() => ask(s)}>{s}</button>)}</div></div>
}
