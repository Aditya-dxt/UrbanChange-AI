import type { Evidence, Fingerprint, Gis, Investigation, TemporalEvent } from '../types'
import { PROGRESS_STEPS } from '../types'

export const Banner = ({ children, danger }: { children: React.ReactNode; danger?: boolean }) =>
  <div className={`warn ${danger ? 'danger' : ''}`}>{children}</div>

export const Disclaimer = () =>
  <Banner>Automated evidence, not a legal determination. Potential findings require human verification.</Banner>

export function ProgressSteps({ step }: { step: number }) {
  return <ol className="list-decimal pl-5 text-sm">{PROGRESS_STEPS.map((s, i) =>
    <li key={s} className={i < step ? 'text-emerald-600' : i === step ? 'font-semibold text-blue-600' : 'opacity-50'}>{s}</li>)}</ol>
}

export function ResultCards({ d }: { d: NonNullable<Investigation['detection']> }) {
  const pct = Math.round(d.confidence * 100)
  return <section className="card finding">
    <div className="flex flex-wrap items-end justify-between gap-4">
      <div>
        <div className="mu text-sm">Potential {d.class}</div>
        <div className="display text-5xl font-bold tabular-nums">{d.area_m2.toLocaleString()} <span className="mu text-xl font-medium">m² changed</span></div>
      </div>
      <span className={`pill prio-${d.priority}`}>{d.priority} priority</span>
    </div>
    <div className="mt-4">
      <div className="flex justify-between text-sm"><span className="mu">Model confidence</span><b>{pct}%</b></div>
      <div className="meter"><i style={{ width: `${pct}%`, background: pct < 60 ? 'var(--bad)' : 'var(--acc)' }} /></div>
    </div>
  </section>
}

export function BeforeAfter({ inv, maskOn, onMask, afterUrl }: { inv: Investigation; maskOn: boolean; onMask: (v: boolean) => void; afterUrl: string }) {
  const { t1, t2 } = inv.observations
  return <div className="card">
    <div className="mb-2 font-semibold">Before / after</div>
    <div className="grid gap-3 grid-cols-2">
      <figure><img src={t1.image_url} alt="before" className="w-full rounded" /><figcaption className="text-xs opacity-70">T1 {t1.date} · cloud {t1.cloud}% · {t1.quality}</figcaption></figure>
      <figure className="relative"><img src={afterUrl} alt="after" className="w-full rounded" />
        {maskOn && inv.detection && <img src={inv.detection.mask_url} alt="change mask" className="absolute inset-0 w-full rounded" />}
        <figcaption className="text-xs opacity-70">T2 {t2.date} · cloud {t2.cloud}% · {t2.quality}</figcaption></figure>
    </div>
    <label className="mt-2 inline-flex gap-2 text-sm"><input type="checkbox" checked={maskOn} onChange={e => onMask(e.target.checked)} disabled={!inv.detection} />Show change mask</label>
  </div>
}

export function GisPanel({ gis }: { gis: Gis }) {
  return <div className="card"><div className="mb-1 font-semibold">GIS context</div>
    {!gis.georeferenced && <Banner>No georeferencing: area, distance and zone overlap are not authoritative.</Banner>}
    {gis.sensitive.length === 0 && <div className="text-sm opacity-70">No configured sensitive layers intersect this area.</div>}
    {gis.sensitive.map(z => <div className="kv" key={z.layer}><span>{z.layer}<br /><span className="text-xs opacity-60">source: {z.source}</span></span><b>{z.overlap_percent}% overlap</b></div>)}
    <div className="kv"><span className="opacity-60">Land cover</span><b>{gis.landcover}</b></div>
    <div className="mt-1 text-xs opacity-60">Overlap with a configured layer is not proof of ownership or illegality.</div></div>
}

export function Timeline({ events, idx, onIdx }: { events: TemporalEvent[]; idx: number; onIdx: (i: number) => void }) {
  return <div className="card"><div className="mb-1 font-semibold">Temporal reconstruction</div>
    <input type="range" className="w-full" min={0} max={events.length - 1} value={idx} onChange={e => onIdx(+e.target.value)} />
    <div className="my-1 flex h-16 items-end gap-1">{events.map((t, i) => <div key={t.date} className={`flex-1 rounded ${i === idx ? 'bg-blue-600' : 'bg-blue-300'}`} style={{ height: `${Math.max(8, t.magnitude * 100)}%` }} />)}</div>
    <div><b>{events[idx].date}</b> · {events[idx].state}</div>
    <div className="text-xs opacity-60">Inference from available observations, not an exact construction date.</div></div>
}

export function FingerprintCard({ f }: { f: Fingerprint }) {
  const rows: [string, string | number][] = [['type', f.type], ['area m²', f.area_m2], ['confidence', f.confidence], ['temporal', f.temporal_behavior], ['sensitive overlap', `${f.sensitive_overlap_percent}%`], ['compactness', f.compactness], ['rectangularity', f.rectangularity], ['land cover', f.landcover]]
  return <div className="card"><div className="mb-1 font-semibold">Change fingerprint <span className="pill">{f.id}</span></div>
    {rows.map(([k, v]) => <div className="kv" key={k}><span className="opacity-60">{k}</span><b>{v}</b></div>)}</div>
}

export function EvidencePanel({ evidence, text }: { evidence: Evidence[]; text: string }) {
  return <div className="card"><div className="mb-1 font-semibold">Evidence & explanation</div><p className="text-sm">{text}</p>
    {evidence.map(e => <div className="kv text-sm" key={e.id}><span><span className="pill">{e.id}</span> {e.type}</span><span className="text-right opacity-70">{e.text}</span></div>)}</div>
}
