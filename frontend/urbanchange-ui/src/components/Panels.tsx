import type {
  Evidence,
  EvidenceGraph,
  Fingerprint,
  Gis,
  Investigation,
  TemporalEvent,
} from '../types'
import { PROGRESS_STEPS } from '../types'

export const Banner = ({
  children,
  danger,
}: {
  children: React.ReactNode
  danger?: boolean
}) => (
  <div
    className={`rounded-xl border p-3 text-sm leading-relaxed ${
      danger
        ? 'border-red-500/40 bg-red-950/30 text-red-200'
        : 'border-amber-500/40 bg-amber-950/20 text-amber-200'
    }`}
  >
    {children}
  </div>
)

export const Disclaimer = () => (
  <Banner>
    <div className="font-semibold text-amber-400">
      ⚠️ Statutory Notice: Requires Human Verification
    </div>
    <div className="mt-1 text-xs text-slate-300">
      Automated evidence generated from satellite spectral analysis and GIS context.
      Satellite imagery and planning overlays alone do not constitute legal authorization or illegality.
    </div>
  </Banner>
)

export function ProgressSteps({ step }: { step: number }) {
  return (
    <div className="flex flex-col gap-2">
      <div className="text-xs font-semibold tracking-wider text-sky-400 uppercase">
        Pipeline Execution Status
      </div>
      <ol className="flex flex-col gap-1.5 pl-2 text-sm">
        {PROGRESS_STEPS.map((s, i) => (
          <li
            key={s}
            className={`flex items-center gap-2 transition-colors ${
              i < step
                ? 'text-emerald-400 font-medium'
                : i === step
                ? 'text-sky-400 font-semibold animate-pulse'
                : 'text-slate-500'
            }`}
          >
            <span
              className={`flex h-5 w-5 items-center justify-center rounded-full text-xs ${
                i < step
                  ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40'
                  : i === step
                  ? 'bg-sky-500/20 text-sky-300 border border-sky-500/40'
                  : 'bg-slate-800 text-slate-500 border border-slate-700'
              }`}
            >
              {i < step ? '✓' : i + 1}
            </span>
            {s}
          </li>
        ))}
      </ol>
    </div>
  )
}

export function ResultCards({
  d,
}: {
  d: NonNullable<Investigation['detection']>
}) {
  const pct = Math.round(d.confidence * 100)
  return (
    <section className="card finding flex flex-col gap-3">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <div className="text-xs font-semibold text-slate-400 uppercase tracking-wide">
            Potential {d.class}
          </div>
          <div className="display text-4xl font-bold tabular-nums text-slate-100">
            {d.area_m2.toLocaleString()}{' '}
            <span className="text-lg font-medium text-slate-400">m² changed</span>
          </div>
        </div>
        <span className={`pill prio-${d.priority} uppercase tracking-wider text-xs font-bold`}>
          {d.priority} priority
        </span>
      </div>
      <div>
        <div className="flex justify-between text-xs text-slate-400 mb-1">
          <span>Model confidence</span>
          <b className="text-slate-200">{pct}%</b>
        </div>
        <div className="h-2 w-full rounded-full bg-slate-800 overflow-hidden">
          <div
            className={`h-full rounded-full ${
              pct < 60 ? 'bg-amber-500' : 'bg-emerald-400'
            }`}
            style={{ width: `${pct}%` }}
          />
        </div>
      </div>
    </section>
  )
}

export function BeforeAfter({
  inv,
  maskOn,
  onMask,
  afterUrl,
}: {
  inv: Investigation
  maskOn: boolean
  onMask: (v: boolean) => void
  afterUrl: string
}) {
  const { t1, t2 } = inv.observations
  return (
    <div className="card flex flex-col gap-2">
      <div className="text-sm font-semibold text-slate-200">
        Temporal Scene Pair
      </div>
      <div className="grid gap-3 grid-cols-2">
        <figure className="flex flex-col gap-1">
          <div className="overflow-hidden rounded-lg border border-slate-700/60 bg-slate-900 aspect-video flex items-center justify-center">
            <img
              src={t1.image_url}
              alt="Historical Scene T1"
              className="h-full w-full object-cover"
              onError={e => {
                ;(e.currentTarget as HTMLElement).style.display = 'none'
              }}
            />
          </div>
          <figcaption className="text-[11px] text-slate-400">
            <b>T1:</b> {t1.date} · cloud {t1.cloud}% · {t1.quality}
          </figcaption>
        </figure>
        <figure className="relative flex flex-col gap-1">
          <div className="relative overflow-hidden rounded-lg border border-slate-700/60 bg-slate-900 aspect-video flex items-center justify-center">
            <img
              src={afterUrl}
              alt="Current Scene T2"
              className="h-full w-full object-cover"
              onError={e => {
                ;(e.currentTarget as HTMLElement).style.display = 'none'
              }}
            />
            {maskOn && inv.detection?.mask_url && (
              <img
                src={inv.detection.mask_url}
                alt="Change Detection Mask"
                className="absolute inset-0 h-full w-full object-cover opacity-80 mix-blend-screen"
                onError={e => {
                  ;(e.currentTarget as HTMLElement).style.display = 'none'
                }}
              />
            )}
          </div>
          <figcaption className="text-[11px] text-slate-400">
            <b>T2:</b> {t2.date} · cloud {t2.cloud}% · {t2.quality}
          </figcaption>
        </figure>
      </div>
      {inv.detection?.mask_url && (
        <label className="mt-1 inline-flex items-center gap-2 text-xs text-slate-300 cursor-pointer">
          <input
            type="checkbox"
            checked={maskOn}
            onChange={e => onMask(e.target.checked)}
            className="rounded border-slate-700 bg-slate-800 text-sky-500 focus:ring-0"
          />
          Overlay AI segmentation mask
        </label>
      )}
    </div>
  )
}

export function GisPanel({ gis }: { gis: Gis }) {
  return (
    <div className="card flex flex-col gap-3">
      <div className="flex items-center justify-between border-b border-slate-800 pb-2">
        <span className="font-semibold text-slate-200">GIS Sensitive Zones & Context</span>
        <span className="text-xs text-sky-400 font-mono">EPSG:4326</span>
      </div>

      {gis.sensitive.length === 0 ? (
        <div className="rounded-lg border border-slate-800 bg-slate-900/50 p-3 text-xs text-slate-400">
          No intersecting sensitive zoning layers configured for this boundary.
        </div>
      ) : (
        <div className="flex flex-col gap-2">
          {gis.sensitive.map((z, idx) => (
            <div
              key={idx}
              className="flex items-center justify-between rounded-lg border border-cyan-500/30 bg-cyan-950/20 p-2.5 text-xs text-cyan-200"
            >
              <div>
                <b className="text-cyan-300 font-medium">{z.layer}</b>
                <div className="text-[10px] text-cyan-400/80">Source: {z.source}</div>
              </div>
              <span className="rounded bg-cyan-900/60 px-2 py-1 font-mono font-bold text-cyan-300">
                {z.overlap_percent}% overlap
              </span>
            </div>
          ))}
        </div>
      )}

      <div className="flex justify-between border-t border-slate-800 pt-2 text-xs text-slate-400">
        <span>Baseline Land Cover</span>
        <b className="text-slate-200">{gis.landcover}</b>
      </div>

      <div className="text-[11px] text-slate-500 leading-normal">
        Notice: Spatial overlap indicates geometry intersection with configured planning buffers,
        not proof of title or violation.
      </div>
    </div>
  )
}

export function Timeline({
  events,
  idx,
  onIdx,
}: {
  events: TemporalEvent[]
  idx: number
  onIdx: (i: number) => void
}) {
  const current = events[idx] || events[0]
  return (
    <div className="card flex flex-col gap-3">
      <div className="flex items-center justify-between border-b border-slate-800 pb-2">
        <span className="font-semibold text-slate-200">Temporal Reconstruction</span>
        <span className="text-xs text-slate-400 font-mono">
          {events.length} observations
        </span>
      </div>

      <input
        type="range"
        className="w-full cursor-pointer accent-sky-400"
        min={0}
        max={Math.max(0, events.length - 1)}
        value={idx}
        onChange={e => onIdx(+e.target.value)}
      />

      <div className="flex h-16 items-end gap-1.5 rounded-lg bg-slate-900/60 p-2 border border-slate-800">
        {events.map((t, i) => (
          <div
            key={i}
            onClick={() => onIdx(i)}
            className={`flex-1 rounded cursor-pointer transition-all ${
              i === idx
                ? 'bg-sky-400 ring-2 ring-sky-300 shadow-md shadow-sky-500/20'
                : 'bg-slate-700 hover:bg-slate-600'
            }`}
            style={{ height: `${Math.max(16, t.magnitude * 100)}%` }}
            title={`${t.date}: ${t.state}`}
          />
        ))}
      </div>

      {current && (
        <div className="rounded-lg border border-slate-800 bg-slate-900/40 p-2.5 text-xs">
          <div className="flex justify-between text-slate-300 font-medium">
            <span className="font-mono text-sky-400">{current.date}</span>
            <span>{current.state}</span>
          </div>
          {current.description && (
            <div className="mt-1 text-slate-400 text-[11px]">
              {current.description}
            </div>
          )}
        </div>
      )}

      <div className="text-[11px] text-slate-500">
        Inferred timeline derived from multi-temporal satellite scene intervals.
      </div>
    </div>
  )
}

export function FingerprintCard({ f }: { f: Fingerprint }) {
  const rows: [string, string | number][] = [
    ['Activity Type', f.type],
    ['Footprint Area', `${f.area_m2.toLocaleString()} m²`],
    ['Confidence Score', `${Math.round(f.confidence * 100)}%`],
    ['Temporal Persistence', f.temporal_behavior],
    ['Sensitive Buffer Overlap', `${f.sensitive_overlap_percent}%`],
    ['Morphology Compactness', f.compactness],
    ['Morphology Rectangularity', f.rectangularity],
    ['Baseline Land Cover', f.landcover],
  ]

  return (
    <div className="card flex flex-col gap-3">
      <div className="flex items-center justify-between border-b border-slate-800 pb-2">
        <span className="font-semibold text-slate-200">Change Fingerprint</span>
        <span className="rounded bg-sky-950/60 px-2 py-0.5 font-mono text-xs font-bold text-sky-400 border border-sky-800/40">
          {f.id}
        </span>
      </div>
      <div className="grid grid-cols-1 gap-2 text-xs">
        {rows.map(([k, v]) => (
          <div
            key={k}
            className="flex items-center justify-between border-b border-slate-800/50 pb-1.5"
          >
            <span className="text-slate-400">{k}</span>
            <b className="text-slate-200 font-medium">{v}</b>
          </div>
        ))}
      </div>
    </div>
  )
}

export function EvidenceGraphView({ graph }: { graph: EvidenceGraph }) {
  return (
    <div className="card flex flex-col gap-3">
      <div className="flex items-center justify-between border-b border-slate-800 pb-2">
        <span className="font-semibold text-slate-200">Evidence Graph</span>
        <span className="text-xs text-sky-400 font-mono">
          {graph.nodes.length} nodes · {graph.edges.length} edges
        </span>
      </div>

      <div className="flex flex-col gap-2">
        {graph.nodes.map(n => {
          const badgeColor =
            n.type === 'observation'
              ? 'bg-blue-950/60 text-blue-300 border-blue-800/50'
              : n.type === 'detection'
              ? 'bg-amber-950/60 text-amber-300 border-amber-800/50'
              : n.type === 'gis'
              ? 'bg-cyan-950/60 text-cyan-300 border-cyan-800/50'
              : n.type === 'fingerprint'
              ? 'bg-purple-950/60 text-purple-300 border-purple-800/50'
              : 'bg-red-950/60 text-red-300 border-red-800/50'

          return (
            <div
              key={n.id}
              className="flex items-center justify-between rounded-lg border border-slate-800 bg-slate-900/60 p-2.5 text-xs"
            >
              <div className="flex items-center gap-2">
                <span
                  className={`rounded border px-1.5 py-0.5 font-mono text-[10px] uppercase font-bold ${badgeColor}`}
                >
                  {n.type}
                </span>
                <span className="font-medium text-slate-200">{n.label}</span>
              </div>
              {n.details && (
                <span className="text-[11px] text-slate-400 font-mono">
                  {n.details}
                </span>
              )}
            </div>
          )
        })}
      </div>

      <div className="rounded-lg border border-slate-800/80 bg-slate-900/40 p-2">
        <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wide mb-1.5">
          Inference Pathways
        </div>
        <div className="flex flex-col gap-1 text-[11px] text-slate-400">
          {graph.edges.map((e, idx) => (
            <div key={idx} className="flex items-center gap-1.5">
              <span className="text-sky-400 font-mono">{e.source}</span>
              <span className="text-slate-600">──({e.relation})──▶</span>
              <span className="text-sky-400 font-mono">{e.target}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

export function EvidencePanel({
  evidence,
  text,
  graph,
}: {
  evidence: Evidence[]
  text: string
  graph?: EvidenceGraph | null
}) {
  return (
    <div className="flex flex-col gap-3">
      {graph && <EvidenceGraphView graph={graph} />}

      <div className="card flex flex-col gap-2">
        <div className="font-semibold text-slate-200">
          Explanation & Audit Trail
        </div>
        <p className="text-xs leading-relaxed text-slate-300">{text}</p>
        <div className="mt-2 flex flex-col gap-1.5 border-t border-slate-800 pt-2">
          <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wide">
            Referenced Records
          </div>
          {evidence.map(e => (
            <div
              key={e.id}
              className="flex items-start justify-between rounded border border-slate-800 bg-slate-900/50 p-2 text-xs"
            >
              <div className="flex items-center gap-1.5">
                <span className="rounded bg-sky-950 px-1.5 py-0.5 font-mono text-[10px] text-sky-400 border border-sky-800/50">
                  {e.id}
                </span>
                <span className="text-slate-300 font-medium">{e.type}</span>
              </div>
              <span className="max-w-[60%] text-right text-[11px] text-slate-400 truncate">
                {e.text}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
