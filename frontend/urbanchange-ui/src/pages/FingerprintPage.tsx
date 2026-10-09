import { useNavigate } from 'react-router-dom'
import {
  AlertTriangle,
  Compass,
  Copy,
  Check,
  FileCheck,
  Fingerprint as FingerprintIcon,
  HelpCircle,
  Layers,
  Sparkles,
} from 'lucide-react'
import { useState } from 'react'
import { Card } from '../components/common/Card'
import { EmptyState } from '../components/common/EmptyState'
import { Badge } from '../components/common/Badge'
import { StatTile } from '../components/common/StatTile'
import { useInvestigationStore } from '../store/useInvestigationStore'

export default function FingerprintPage() {
  const navigate = useNavigate()
  const { activeInvestigation } = useInvestigationStore()
  const [copied, setCopied] = useState(false)

  if (!activeInvestigation || !activeInvestigation.fingerprint) {
    return (
      <div className="flex-1 p-6 flex items-center justify-center">
        <EmptyState
          title="No Change Fingerprint Generated"
          description="A change fingerprint is produced once an area is detected with anomalous physical surface changes."
          actionLabel="Go to Investigate Map"
          onAction={() => navigate('/investigate')}
          icon={<FingerprintIcon className="h-8 w-8 text-sky-400" />}
        />
      </div>
    )
  }

  const f = activeInvestigation.fingerprint
  const d = activeInvestigation.detection
  const pct = Math.round(f.confidence * 100)

  function copyFingerprintId() {
    navigator.clipboard.writeText(f.id)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8 space-y-6">
      {/* HEADER */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-mono text-sky-400 font-semibold uppercase tracking-wider">
              Diagnostic Profiling
            </span>
            <span className="flex items-center gap-1.5 rounded-md bg-sky-950/80 border border-sky-800/50 px-2 py-0.5 text-xs font-mono font-bold text-sky-300">
              {f.id}
              <button
                onClick={copyFingerprintId}
                className="hover:text-white transition-colors"
                title="Copy Fingerprint ID"
              >
                {copied ? <Check className="h-3 w-3 text-emerald-400" /> : <Copy className="h-3 w-3" />}
              </button>
            </span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-100 tracking-tight">
            Change Fingerprint
          </h1>
          <p className="text-xs sm:text-sm text-slate-400 mt-1">
            Standardized multi-dimensional signature synthesizing morphology, persistence, and zoning overlap.
          </p>
        </div>

        <button
          onClick={() => navigate('/results')}
          className="btn-ghost text-xs border border-slate-700/80 self-start sm:self-auto"
        >
          ← Back to Results
        </button>
      </div>

      {/* STATUTORY NOTICE */}
      <div className="rounded-xl border border-amber-500/40 bg-amber-950/20 p-4 text-xs text-amber-200/90 leading-relaxed">
        <b className="font-semibold text-amber-300">
          ⚠️ Advisory: Morphological & Spectral Inference Only
        </b>
        <p className="mt-1 text-slate-300">
          Fingerprint parameters quantify physical geometry and reflectance transitions. They serve as
          computational indicators to guide investigative priority, not statutory certificates of legality.
        </p>
      </div>

      {/* TOP STATS ROW */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatTile
          label="Activity Classification"
          value={f.type}
          subValue="Inferred physical nature"
          variant="default"
        />
        <StatTile
          label="Footprint Extent"
          value={`${f.area_m2.toLocaleString()} m²`}
          subValue={`${(f.area_m2 / 10000).toFixed(2)} ha surface area`}
          variant="default"
        />
        <StatTile
          label="Confidence Level"
          value={`${pct}%`}
          subValue="Cross-model consensus"
          variant={pct >= 60 ? 'success' : 'warning'}
        />
        <StatTile
          label="Zoning Overlap"
          value={`${f.sensitive_overlap_percent}%`}
          subValue={f.sensitive_overlap_percent > 0 ? 'Buffer intersected' : 'Zero buffer overlap'}
          variant={f.sensitive_overlap_percent > 0 ? 'danger' : 'success'}
        />
      </div>

      {/* STRUCTURED ATTRIBUTE TABLE */}
      <Card
        title="Comprehensive Fingerprint Specification"
        subtitle="Full parameter breakdown for cross-scene indexing and auditing"
      >
        <div className="divide-y divide-slate-800 text-xs sm:text-sm">
          <div className="py-3 flex items-center justify-between">
            <span className="text-slate-400 flex items-center gap-1.5">
              Unique Signature ID
            </span>
            <span className="font-mono font-bold text-sky-400">{f.id}</span>
          </div>

          <div className="py-3 flex items-center justify-between">
            <span className="text-slate-400 flex items-center gap-1.5">
              Activity Class
            </span>
            <span className="font-semibold text-slate-200 capitalize">{f.type}</span>
          </div>

          <div className="py-3 flex items-center justify-between">
            <span className="text-slate-400 flex items-center gap-1.5">
              Surface Footprint Area
            </span>
            <span className="font-mono text-slate-200">
              {f.area_m2.toLocaleString()} m² ({(f.area_m2 / 10000).toFixed(3)} ha)
            </span>
          </div>

          <div className="py-3 flex items-center justify-between">
            <span className="text-slate-400 flex items-center gap-1.5">
              Statistical Confidence
            </span>
            <span className="font-mono font-bold text-slate-200">{pct}%</span>
          </div>

          <div className="py-3 flex items-center justify-between">
            <span className="text-slate-400 flex items-center gap-1.5">
              Temporal Behavior
            </span>
            <span className="font-semibold text-slate-200">{f.temporal_behavior}</span>
          </div>

          <div className="py-3 flex items-center justify-between">
            <span className="text-slate-400 flex items-center gap-1.5">
              Sensitive Zone Overlap
            </span>
            <span
              className={`font-mono font-bold ${
                f.sensitive_overlap_percent > 0 ? 'text-rose-400' : 'text-emerald-400'
              }`}
            >
              {f.sensitive_overlap_percent}%
            </span>
          </div>

          <div className="py-3 flex items-center justify-between">
            <div>
              <span className="text-slate-400">Morphological Compactness</span>
              <p className="text-[11px] text-slate-500">
                Isoperimetric quotient (ratio of area to squared perimeter)
              </p>
            </div>
            <span className="font-mono text-slate-200 font-semibold">{f.compactness}</span>
          </div>

          <div className="py-3 flex items-center justify-between">
            <div>
              <span className="text-slate-400">Morphological Rectangularity</span>
              <p className="text-[11px] text-slate-500">
                Extent of alignment with minimum bounding oriented rectangle
              </p>
            </div>
            <span className="font-mono text-slate-200 font-semibold">{f.rectangularity}</span>
          </div>

          <div className="py-3 flex items-center justify-between">
            <span className="text-slate-400 flex items-center gap-1.5">
              Baseline Land Cover (ESA WorldCover)
            </span>
            <span className="font-semibold text-slate-200">{f.landcover}</span>
          </div>

          {d?.model_version && (
            <div className="py-3 flex items-center justify-between">
              <span className="text-slate-400">AI Model Version</span>
              <span className="font-mono text-slate-400">{d.model_version}</span>
            </div>
          )}

          <div className="py-3 flex items-center justify-between">
            <span className="text-slate-400">Coordinate Reference System</span>
            <span className="font-mono text-sky-400">UTM Projected / EPSG:4326</span>
          </div>
        </div>
      </Card>
    </div>
  )
}
