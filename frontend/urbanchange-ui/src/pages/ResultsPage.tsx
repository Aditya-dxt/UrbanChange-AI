import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import {
  AlertTriangle,
  ArrowRight,
  Bot,
  Calendar,
  CheckCircle2,
  Compass,
  Eye,
  FileSearch,
  Fingerprint as FingerprintIcon,
  Layers,
  Network,
  ShieldAlert,
} from 'lucide-react'
import { Card } from '../components/common/Card'
import { StatTile } from '../components/common/StatTile'
import { EmptyState } from '../components/common/EmptyState'
import { Badge } from '../components/common/Badge'
import { useInvestigationStore } from '../store/useInvestigationStore'

export default function ResultsPage() {
  const navigate = useNavigate()
  const { activeInvestigation } = useInvestigationStore()
  const [maskOverlay, setMaskOverlay] = useState(true)

  if (!activeInvestigation) {
    return (
      <div className="flex-1 p-6 flex items-center justify-center">
        <EmptyState
          title="No Active Investigation Results"
          description="You haven't run any change detection analysis yet. Select an area on the map or upload image pairs to view results."
          actionLabel="Go to Investigate Map"
          onAction={() => navigate('/investigate')}
          icon={<Compass className="h-8 w-8 text-sky-400" />}
        />
      </div>
    )
  }

  const { detection, observations, status, id, created_at, gis, fingerprint } =
    activeInvestigation
  const pct = detection ? Math.round(detection.confidence * 100) : 0
  const ha = detection ? (detection.area_m2 / 10000).toFixed(2) : '0'

  return (
    <div className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8 space-y-6">
      {/* HEADER SECTION */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-mono text-sky-400 font-semibold uppercase tracking-wider">
              Investigation Report
            </span>
            <Badge variant="default" size="sm" className="font-mono">
              ID: {id}
            </Badge>
            {status === 'partial' && (
              <Badge variant="warning" size="sm">
                Partial (Timeline Unavailable)
              </Badge>
            )}
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-100 tracking-tight">
            Detection Findings & Overview
          </h1>
          <p className="text-xs sm:text-sm text-slate-400 mt-1">
            Bi-temporal Sentinel-2 MSI comparison between{' '}
            <b className="text-slate-200">{observations.t1.date}</b> and{' '}
            <b className="text-slate-200">{observations.t2.date}</b>
          </p>
        </div>

        {/* Quick Actions */}
        <div className="flex items-center gap-2">
          <button
            onClick={() => navigate('/investigate')}
            className="btn-ghost flex items-center gap-1.5 text-xs border border-slate-700/80"
          >
            <Compass className="h-3.5 w-3.5" /> Return to Map
          </button>
          <button
            onClick={() => navigate('/assistant')}
            className="btn flex items-center gap-1.5 text-xs"
          >
            <Bot className="h-3.5 w-3.5" /> Ask Assistant
          </button>
        </div>
      </div>

      {/* STATUTORY DISCLAIMER BANNER */}
      <div className="rounded-xl border border-amber-500/40 bg-amber-950/20 p-4 shadow-sm">
        <div className="flex items-start gap-3">
          <AlertTriangle className="h-5 w-5 text-amber-400 shrink-0 mt-0.5" />
          <div className="text-xs sm:text-sm leading-relaxed text-amber-200/90">
            <b className="font-semibold text-amber-300">
              Statutory Notice: Automated Analysis Requires Human Verification
            </b>
            <p className="mt-1 text-slate-300">
              Findings represent automated spectral anomaly detection and spatial geometry intersection.
              Satellite imagery and planning overlays alone do not constitute legal proof of title,
              encroachment, or regulatory violation.
            </p>
          </div>
        </div>
      </div>

      {/* LOW CONFIDENCE BANNER IF APPLICABLE */}
      {detection && detection.confidence < 0.6 && (
        <div className="rounded-xl border border-rose-500/40 bg-rose-950/25 p-4 shadow-sm">
          <div className="flex items-start gap-3">
            <AlertTriangle className="h-5 w-5 text-rose-400 shrink-0 mt-0.5" />
            <div className="text-xs sm:text-sm text-rose-200">
              <b className="font-semibold text-rose-300">
                Low Confidence Detection ({pct}%)
              </b>
              <p className="mt-1 text-slate-300">
                Model confidence is below the verified threshold (60%). Potential factors include
                ephemeral surface changes, cloud/shadow artifacts, or seasonal variation. Field
                inspection is strongly recommended.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* METRICS GRID */}
      {detection ? (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <StatTile
            label="Changed Area"
            value={`${detection.area_m2.toLocaleString()} m²`}
            subValue={`${ha} hectares affected`}
            variant="default"
          />
          <StatTile
            label="Model Confidence"
            value={`${pct}%`}
            subValue={pct >= 60 ? 'High probability' : 'Low certainty'}
            variant={pct >= 60 ? 'success' : 'warning'}
          />
          <StatTile
            label="Identified Class"
            value={detection.class}
            subValue={`Model: ${detection.model_version}`}
            variant="default"
          />
          <StatTile
            label="Review Priority"
            value={detection.priority.toUpperCase()}
            subValue={
              detection.priority === 'high'
                ? 'Sensitive overlap detected'
                : 'Routine review'
            }
            variant={detection.priority === 'high' ? 'danger' : 'info'}
          />
        </div>
      ) : (
        <Card className="p-6 text-center">
          <CheckCircle2 className="h-10 w-10 text-emerald-400 mx-auto mb-2" />
          <h3 className="text-base font-bold text-slate-100">No Significant Change Detected</h3>
          <p className="text-xs text-slate-400 max-w-md mx-auto mt-1">
            No pixels or regions exceeded the anomaly threshold between the two observation dates.
            Surface characteristics appear stable.
          </p>
        </Card>
      )}

      {/* BEFORE / AFTER COMPARISON VIEWER */}
      <Card
        title="Temporal Scene Pair Comparison"
        subtitle="Spectral reflectance scenes clipped to selected AOI bounds"
        action={
          detection?.mask_url ? (
            <label className="flex items-center gap-2 text-xs text-slate-300 cursor-pointer">
              <input
                type="checkbox"
                checked={maskOverlay}
                onChange={e => setMaskOverlay(e.target.checked)}
                className="rounded border-slate-700 bg-slate-800 text-sky-500"
              />
              <span className="flex items-center gap-1">
                <Eye className="h-3.5 w-3.5 text-sky-400" /> Overlay AI Mask
              </span>
            </label>
          ) : undefined
        }
      >
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* T1 Historical */}
          <div className="flex flex-col gap-2">
            <div className="relative overflow-hidden rounded-xl border border-slate-700/80 bg-slate-950 aspect-video flex items-center justify-center">
              <img
                src={observations.t1.image_url}
                alt={`T1 Scene ${observations.t1.date}`}
                className="h-full w-full object-cover"
                onError={e => {
                  ;(e.currentTarget as HTMLElement).style.display = 'none'
                }}
              />
              <div className="absolute top-2 left-2 rounded-md bg-slate-900/85 border border-slate-700/60 px-2 py-0.5 text-[11px] font-mono text-slate-200">
                T1: Earlier
              </div>
            </div>
            <div className="flex items-center justify-between text-xs text-slate-400 px-1">
              <span>Date: <b className="text-slate-200">{observations.t1.date}</b></span>
              <span>Cloud: <b className="text-slate-200">{observations.t1.cloud}%</b></span>
              <span>Quality: <b className="text-slate-200">{observations.t1.quality}</b></span>
            </div>
          </div>

          {/* T2 Current */}
          <div className="flex flex-col gap-2">
            <div className="relative overflow-hidden rounded-xl border border-slate-700/80 bg-slate-950 aspect-video flex items-center justify-center">
              <img
                src={observations.t2.image_url}
                alt={`T2 Scene ${observations.t2.date}`}
                className="h-full w-full object-cover"
                onError={e => {
                  ;(e.currentTarget as HTMLElement).style.display = 'none'
                }}
              />
              {maskOverlay && detection?.mask_url && (
                <img
                  src={detection.mask_url}
                  alt="Segmentation Mask Overlay"
                  className="absolute inset-0 h-full w-full object-cover opacity-75 mix-blend-screen pointer-events-none"
                  onError={e => {
                    ;(e.currentTarget as HTMLElement).style.display = 'none'
                  }}
                />
              )}
              <div className="absolute top-2 left-2 rounded-md bg-slate-900/85 border border-slate-700/60 px-2 py-0.5 text-[11px] font-mono text-slate-200">
                T2: Recent
              </div>
            </div>
            <div className="flex items-center justify-between text-xs text-slate-400 px-1">
              <span>Date: <b className="text-slate-200">{observations.t2.date}</b></span>
              <span>Cloud: <b className="text-slate-200">{observations.t2.cloud}%</b></span>
              <span>Quality: <b className="text-slate-200">{observations.t2.quality}</b></span>
            </div>
          </div>
        </div>
      </Card>

      {/* AUDIT SUMMARY & EXPLANATION */}
      {activeInvestigation.explanation && (
        <Card title="AI Audit Trail & Findings Summary">
          <p className="text-xs sm:text-sm text-slate-300 leading-relaxed font-sans">
            {activeInvestigation.explanation}
          </p>
        </Card>
      )}

      {/* QUICK DEEP-DIVE NAVIGATION CARDS */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Link
          to="/fingerprint"
          className="group rounded-xl border border-slate-800 bg-slate-900/60 p-4 transition-all hover:border-sky-500/40 hover:bg-slate-900 flex flex-col justify-between"
        >
          <div>
            <div className="flex items-center justify-between text-sky-400 mb-2">
              <FingerprintIcon className="h-5 w-5" />
              <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />
            </div>
            <h4 className="text-sm font-bold text-slate-100">Change Fingerprint</h4>
            <p className="text-xs text-slate-400 mt-1">
              Morphology compactness, rectangularity, persistence, and land cover signature.
            </p>
          </div>
          <div className="mt-4 text-[11px] font-mono text-sky-400 font-semibold">
            {fingerprint ? `ID: ${fingerprint.id}` : 'Inspect signature →'}
          </div>
        </Link>

        <Link
          to="/sensitive-zones"
          className="group rounded-xl border border-slate-800 bg-slate-900/60 p-4 transition-all hover:border-cyan-500/40 hover:bg-slate-900 flex flex-col justify-between"
        >
          <div>
            <div className="flex items-center justify-between text-cyan-400 mb-2">
              <ShieldAlert className="h-5 w-5" />
              <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />
            </div>
            <h4 className="text-sm font-bold text-slate-100">Sensitive Zones</h4>
            <p className="text-xs text-slate-400 mt-1">
              GIS planning buffer overlap percentages, municipal master plans, and ESA WorldCover.
            </p>
          </div>
          <div className="mt-4 text-[11px] font-mono text-cyan-400 font-semibold">
            {gis?.sensitive ? `${gis.sensitive.length} layers intersected →` : 'View zoning →'}
          </div>
        </Link>

        <Link
          to="/timeline"
          className="group rounded-xl border border-slate-800 bg-slate-900/60 p-4 transition-all hover:border-amber-500/40 hover:bg-slate-900 flex flex-col justify-between"
        >
          <div>
            <div className="flex items-center justify-between text-amber-400 mb-2">
              <Calendar className="h-5 w-5" />
              <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />
            </div>
            <h4 className="text-sm font-bold text-slate-100">Temporal Timeline</h4>
            <p className="text-xs text-slate-400 mt-1">
              Multi-scene progression, disturbance onset dates, and development phases.
            </p>
          </div>
          <div className="mt-4 text-[11px] font-mono text-amber-400 font-semibold">
            {activeInvestigation.temporal
              ? `${activeInvestigation.temporal.length} epochs analysed →`
              : 'Reconstruct phases →'}
          </div>
        </Link>

        <Link
          to="/evidence-graph"
          className="group rounded-xl border border-slate-800 bg-slate-900/60 p-4 transition-all hover:border-purple-500/40 hover:bg-slate-900 flex flex-col justify-between"
        >
          <div>
            <div className="flex items-center justify-between text-purple-400 mb-2">
              <Network className="h-5 w-5" />
              <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />
            </div>
            <h4 className="text-sm font-bold text-slate-100">Evidence Graph</h4>
            <p className="text-xs text-slate-400 mt-1">
              Explicit directed graph connecting satellite scenes to inferences and policy checks.
            </p>
          </div>
          <div className="mt-4 text-[11px] font-mono text-purple-400 font-semibold">
            {activeInvestigation.evidence_graph
              ? `${activeInvestigation.evidence_graph.nodes.length} nodes connected →`
              : 'Trace evidence →'}
          </div>
        </Link>
      </div>
    </div>
  )
}
