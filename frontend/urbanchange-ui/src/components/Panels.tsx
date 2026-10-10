import React, { useState, useMemo } from 'react'
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

// Colour per class matching the visual design
const CLASS_COLORS: Record<string, string> = {
  construction: '#f97316',    // Bright Orange
  deforestation: '#22c55e',   // Emerald Green
  vegetation_loss: '#22c55e', // Emerald Green
  excavation: '#ef4444',      // Vibrant Red
  infrastructure: '#06b6d4',  // Cyan Blue
  water_change: '#3b82f6',    // Royal Blue
  other: '#facc15',           // Amber
  no_change: '#94a3b8',       // Slate
}

function getColor(label?: string, idx: number = 0) {
  if (!label) {
    return idx % 2 === 0 ? '#ef4444' : '#06b6d4'
  }
  const key = label.toLowerCase()
  return CLASS_COLORS[key] ?? (idx % 2 === 0 ? '#ef4444' : '#06b6d4')
}

// Extract axis-aligned bounding box from a GeoJSON Polygon in normalised [0,1] space
function extractPolygonBbox(coords: number[][][]): { x: number; y: number; w: number; h: number } | null {
  const ring = coords[0]
  if (!ring || ring.length < 3) return null
  const xs = ring.map(p => p[0])
  const ys = ring.map(p => p[1])
  const minX = Math.max(0, Math.min(...xs))
  const maxX = Math.min(1, Math.max(...xs))
  const minY = Math.max(0, Math.min(...ys))
  const maxY = Math.min(1, Math.max(...ys))
  return {
    x: minX,
    y: minY,
    w: Math.max(0.02, maxX - minX),
    h: Math.max(0.02, maxY - minY),
  }
}

interface RegionBoxItem {
  box: { x: number; y: number; w: number; h: number }
  label: string
  color: string
  confidence?: number
}

/**
 * Reusable full-scene viewer panel:
 * Displays the complete image without zooming or cropping (natural aspect ratio),
 * with prominent SVG bounding-box overlays outlining detected change regions.
 */
function FullScenePanel({
  src,
  alt,
  badgeText,
  badgeColorClass,
  boxes,
  showBoxes,
  overlayElement,
}: {
  src: string
  alt: string
  badgeText: string
  badgeColorClass: string
  boxes: RegionBoxItem[]
  showBoxes: boolean
  overlayElement?: React.ReactNode
}) {
  return (
    <figure className="relative flex flex-col gap-1.5">
      {/* Outer viewport container – prevents cropping, displays full unzoomed image */}
      <div className="relative overflow-hidden rounded-xl border border-slate-700/80 bg-slate-950 flex items-center justify-center shadow-lg">
        {/* Full Image: 100% width, natural height, zero crop or artificial zoom */}
        <img
          src={src}
          alt={alt}
          className="w-full h-auto max-h-[540px] object-contain block select-none"
          onError={e => {
            ;(e.currentTarget as HTMLElement).style.display = 'none'
          }}
        />

        {/* Optional segmentation mask overlay (e.g. for T2) */}
        {overlayElement}

        {/* Prominent Bounding Boxes SVG Overlay (aligned 1:1 with the image bounds) */}
        {showBoxes && boxes.length > 0 && (
          <svg
            className="absolute inset-0 h-full w-full pointer-events-none"
            viewBox="0 0 1 1"
            preserveAspectRatio="none"
            aria-label="Detected change region bounding boxes"
          >
            {boxes.map((item, i) => {
              const { box, color, label } = item
              // Bold, high-visibility stroke matching reference image 2
              const strokeWidth = '0.012'
              const cornerRadius = '0.010'
              return (
                <g key={i}>
                  {/* Outer glow / drop-shadow stroke */}
                  <rect
                    x={box.x}
                    y={box.y}
                    width={box.w}
                    height={box.h}
                    fill="none"
                    stroke="#000000"
                    strokeWidth="0.018"
                    rx={cornerRadius}
                    opacity="0.6"
                  />
                  {/* Translucent colored highlight fill */}
                  <rect
                    x={box.x}
                    y={box.y}
                    width={box.w}
                    height={box.h}
                    fill={color}
                    fillOpacity="0.22"
                    stroke={color}
                    strokeWidth={strokeWidth}
                    rx={cornerRadius}
                  />
                  {/* Corner brackets accents */}
                  <polyline
                    points={`${box.x + Math.min(0.04, box.w * 0.35)},${box.y} ${box.x},${box.y} ${box.x},${box.y + Math.min(0.04, box.h * 0.35)}`}
                    fill="none"
                    stroke="#ffffff"
                    strokeWidth="0.016"
                    strokeLinecap="round"
                  />
                  <polyline
                    points={`${box.x + box.w - Math.min(0.04, box.w * 0.35)},${box.y + box.h} ${box.x + box.w},${box.y + box.h} ${box.x + box.w},${box.y + box.h - Math.min(0.04, box.h * 0.35)}`}
                    fill="none"
                    stroke="#ffffff"
                    strokeWidth="0.016"
                    strokeLinecap="round"
                  />
                  {/* Label badge tag */}
                  {box.h >= 0.05 && (
                    <g>
                      <rect
                        x={box.x}
                        y={Math.max(0.005, box.y - 0.038)}
                        width={Math.min(box.w, label.length * 0.018 + 0.03)}
                        height="0.034"
                        rx="0.006"
                        fill="#0f172a"
                        fillOpacity="0.9"
                        stroke={color}
                        strokeWidth="0.005"
                      />
                      <text
                        x={box.x + 0.008}
                        y={Math.max(0.027, box.y - 0.015)}
                        fontSize="0.024"
                        fill="#ffffff"
                        fontWeight="bold"
                        fontFamily="sans-serif"
                      >
                        {label.length > 12 ? label.slice(0, 10) + '…' : label}
                      </text>
                    </g>
                  )}
                </g>
              )
            })}
          </svg>
        )}

        {/* Top-Left Scene Identifier Badge (e.g. T1 Baseline, T2 Current) */}
        <div className="absolute top-2.5 left-2.5 z-10">
          <span className={`px-2.5 py-1 rounded-md text-xs font-bold uppercase tracking-wider shadow-md backdrop-blur-sm ${badgeColorClass}`}>
            {badgeText}
          </span>
        </div>
      </div>
    </figure>
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
  const [showBoxes, setShowBoxes] = useState(true)
  const [boxesOnBoth, setBoxesOnBoth] = useState(true)

  // Extract all region boxes
  const regions = inv.detection?.change_regions ?? []
  const boxItems = useMemo<RegionBoxItem[]>(() => {
    const list: RegionBoxItem[] = []
    for (let idx = 0; idx < regions.length; idx++) {
      const r = regions[idx] as any
      let b = r.box
      if (!b) {
        const poly = r.geometry as GeoJSON.Polygon
        if (poly?.coordinates) {
          b = extractPolygonBbox(poly.coordinates)
        }
      }
      if (b) {
        const label = r.label || r.change_type || 'Change'
        list.push({
          box: b,
          label: String(label).replace(/_/g, ' '),
          color: getColor(label, idx),
          confidence: r.confidence,
        })
      }
    }
    return list
  }, [regions])

  const distinctLabels = Array.from(new Set(boxItems.map(b => b.label)))

  return (
    <div className="card flex flex-col gap-3 p-4 sm:p-5">
      {/* Title & Section Header matching Reference Image 2 */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-800 pb-3">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xs font-mono font-bold uppercase tracking-wider text-sky-400">
              Full Scene Analysis
            </span>
            {boxItems.length > 0 && (
              <span className="text-xs font-semibold text-emerald-400">
                ({boxItems.length} changes outlined)
              </span>
            )}
          </div>
          <div className="text-xs text-slate-400 mt-0.5">
            Bi-temporal comparison showing full uncropped visual extent with automated spatial bounding boxes.
          </div>
        </div>

        {/* Legend pills for detected change types */}
        {distinctLabels.length > 0 && (
          <div className="flex items-center gap-1.5 flex-wrap">
            {distinctLabels.map(lbl => {
              const color = getColor(lbl)
              return (
                <span
                  key={lbl}
                  className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-semibold text-white shadow-sm"
                  style={{ backgroundColor: color + 'cc' }}
                >
                  <span className="w-2 h-2 rounded-full bg-white shadow-sm" />
                  {lbl}
                </span>
              )
            })}
          </div>
        )}
      </div>

      {/* Side-by-Side Full Scenes Grid (No Zooming, No Cropping) */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* ── T1 Baseline Scene ── */}
        <div className="flex flex-col gap-1">
          <FullScenePanel
            src={t1.image_url}
            alt="Historical Baseline Scene T1"
            badgeText="T1 Baseline"
            badgeColorClass="bg-slate-900/90 text-slate-100 border border-slate-700"
            boxes={boxItems}
            showBoxes={showBoxes && boxesOnBoth}
          />
          <div className="text-[11px] text-slate-400 flex items-center justify-between px-1">
            <span><b>Date:</b> {t1.date}</span>
            <span>Cloud: {t1.cloud}% · Quality: {t1.quality}</span>
          </div>
        </div>

        {/* ── T2 Current Scene (with Bounding Boxes & AI Segmentation Mask) ── */}
        <div className="flex flex-col gap-1">
          <FullScenePanel
            src={afterUrl}
            alt="Current Scene T2"
            badgeText="T2 Current"
            badgeColorClass="bg-amber-500/90 text-slate-950 font-extrabold border border-amber-300"
            boxes={boxItems}
            showBoxes={showBoxes}
            overlayElement={
              maskOn && inv.detection?.mask_url ? (
                <img
                  src={inv.detection.mask_url}
                  alt="Change Detection Mask"
                  className="absolute inset-0 h-full w-full object-contain opacity-75 mix-blend-screen pointer-events-none"
                  onError={e => {
                    ;(e.currentTarget as HTMLElement).style.display = 'none'
                  }}
                />
              ) : null
            }
          />
          <div className="text-[11px] text-slate-400 flex items-center justify-between px-1">
            <span><b>Date:</b> {t2.date}</span>
            <span>Cloud: {t2.cloud}% · Quality: {t2.quality}</span>
          </div>
        </div>
      </div>

      {/* Interactive Controls Row */}
      <div className="flex items-center justify-between flex-wrap gap-4 pt-2 border-t border-slate-800/80 text-xs text-slate-300">
        <div className="flex items-center gap-5 flex-wrap">
          {/* Toggle Change Bounding Boxes */}
          <label className="inline-flex items-center gap-2 cursor-pointer font-medium hover:text-white">
            <input
              type="checkbox"
              checked={showBoxes}
              onChange={e => setShowBoxes(e.target.checked)}
              className="rounded border-slate-700 bg-slate-800 text-sky-500 focus:ring-0"
            />
            <span>Highlight Change Bounding Boxes</span>
          </label>

          {/* Toggle Bounding Boxes on Both Scenes */}
          {showBoxes && (
            <label className="inline-flex items-center gap-2 cursor-pointer font-medium hover:text-white">
              <input
                type="checkbox"
                checked={boxesOnBoth}
                onChange={e => setBoxesOnBoth(e.target.checked)}
                className="rounded border-slate-700 bg-slate-800 text-sky-500 focus:ring-0"
              />
              <span>Outline on Both Scenes (T1 & T2)</span>
            </label>
          )}

          {/* Toggle AI Segmentation Mask */}
          {inv.detection?.mask_url && (
            <label className="inline-flex items-center gap-2 cursor-pointer font-medium hover:text-white">
              <input
                type="checkbox"
                checked={maskOn}
                onChange={e => onMask(e.target.checked)}
                className="rounded border-slate-700 bg-slate-800 text-sky-500 focus:ring-0"
              />
              <span>Overlay AI Segmentation Mask</span>
            </label>
          )}
        </div>

        {boxItems.length > 0 && (
          <div className="text-[11px] text-slate-400 font-mono">
            {boxItems.length} regions identified
          </div>
        )}
      </div>
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
