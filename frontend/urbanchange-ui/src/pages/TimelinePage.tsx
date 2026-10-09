import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Calendar,
  Clock,
  Compass,
  History,
  Image as ImageIcon,
  Layers,
  Sparkles,
  TrendingUp,
} from 'lucide-react'
import { Card } from '../components/common/Card'
import { EmptyState } from '../components/common/EmptyState'
import { Badge } from '../components/common/Badge'
import { StatTile } from '../components/common/StatTile'
import { useInvestigationStore } from '../store/useInvestigationStore'

export default function TimelinePage() {
  const navigate = useNavigate()
  const { activeInvestigation } = useInvestigationStore()
  const [selectedIdx, setSelectedIdx] = useState(0)

  if (!activeInvestigation) {
    return (
      <div className="flex-1 p-6 flex items-center justify-center">
        <EmptyState
          title="No Temporal Timeline Available"
          description="Temporal reconstruction is generated from multi-temporal Sentinel-2 scene intervals."
          actionLabel="Go to Investigate Map"
          onAction={() => navigate('/investigate')}
          icon={<Calendar className="h-8 w-8 text-amber-400" />}
        />
      </div>
    )
  }

  const { temporal, observations, status } = activeInvestigation

  if (!temporal || temporal.length === 0) {
    return (
      <div className="flex-1 p-6 flex items-center justify-center">
        <EmptyState
          title="Timeline Unavailable for this Investigation"
          description={
            status === 'partial'
              ? 'Multi-epoch observations could not be assembled due to persistent cloud cover or missing intermediate Sentinel-2 passes.'
              : 'Execute an investigation to reconstruct the temporal development trajectory.'
          }
          actionLabel="Return to Investigate Map"
          onAction={() => navigate('/investigate')}
          icon={<Clock className="h-8 w-8 text-amber-400" />}
        />
      </div>
    )
  }

  const currentEvent = temporal[selectedIdx] || temporal[0]

  return (
    <div className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8 space-y-6">
      {/* HEADER */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-mono text-amber-400 font-semibold uppercase tracking-wider">
              Chronological Analysis
            </span>
            <Badge variant="default" size="sm" className="font-mono">
              {temporal.length} Temporal Intervals
            </Badge>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-100 tracking-tight">
            Temporal Reconstruction
          </h1>
          <p className="text-xs sm:text-sm text-slate-400 mt-1">
            Chronological progression reconstructing the onset, excavation, and structural development of physical changes.
          </p>
        </div>

        <button
          onClick={() => navigate('/results')}
          className="btn-ghost text-xs border border-slate-700/80 self-start sm:self-auto"
        >
          ← Back to Results
        </button>
      </div>

      {/* METRIC STATS TILES */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatTile
          label="Total Epochs"
          value={temporal.length.toString()}
          subValue="Intermediate satellite passes"
          variant="default"
        />
        <StatTile
          label="Earliest Observation"
          value={temporal[0]?.date || observations.t1.date}
          subValue="Baseline reference state"
          variant="default"
        />
        <StatTile
          label="Latest Observation"
          value={temporal[temporal.length - 1]?.date || observations.t2.date}
          subValue="Recent terminal state"
          variant="default"
        />
        <StatTile
          label="Selected Epoch"
          value={currentEvent?.date || '—'}
          subValue={currentEvent?.state || 'Observation'}
          variant="info"
        />
      </div>

      {/* INTERACTIVE DATE SCRUBBER CARD */}
      <Card
        title="Interactive Epoch Scrubber"
        subtitle="Slide or click bars below to inspect scene states over time"
      >
        <div className="space-y-4">
          {/* Slider input */}
          <div className="space-y-1">
            <div className="flex justify-between text-xs text-slate-400">
              <span>{temporal[0]?.date}</span>
              <span className="font-bold text-amber-400">{currentEvent?.date}</span>
              <span>{temporal[temporal.length - 1]?.date}</span>
            </div>
            <input
              type="range"
              min={0}
              max={temporal.length - 1}
              value={selectedIdx}
              onChange={e => setSelectedIdx(+e.target.value)}
              className="w-full accent-amber-400 cursor-pointer h-2 bg-slate-800 rounded-lg"
              aria-label="Timeline scrubber"
            />
          </div>

          {/* Magnitude Bar Visualizer */}
          <div className="flex h-24 items-end gap-2 rounded-xl bg-slate-950/80 p-3 border border-slate-800">
            {temporal.map((t, i) => (
              <div
                key={i}
                onClick={() => setSelectedIdx(i)}
                className={`flex-1 rounded-t-md cursor-pointer transition-all flex flex-col justify-end items-center relative group ${
                  i === selectedIdx
                    ? 'bg-amber-400 ring-2 ring-amber-300 shadow-lg shadow-amber-500/20'
                    : 'bg-slate-700 hover:bg-slate-500'
                }`}
                style={{ height: `${Math.max(20, (t.magnitude || 0.2) * 100)}%` }}
              >
                <div className="absolute bottom-full mb-1 hidden group-hover:flex flex-col items-center z-20 pointer-events-none">
                  <div className="rounded bg-slate-900 border border-slate-700 px-2 py-1 text-[10px] text-slate-200 whitespace-nowrap shadow-xl">
                    {t.date}: {t.state}
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* Active Event Card */}
          <div className="rounded-xl border border-amber-500/30 bg-amber-950/20 p-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-amber-500/20 pb-3">
              <div className="flex items-center gap-2">
                <span className="text-base font-bold text-slate-100">{currentEvent.state}</span>
                <Badge variant="warning" size="sm">
                  {currentEvent.date}
                </Badge>
              </div>
              <div className="text-xs text-amber-300/80 font-mono">
                Anomaly Index: {Math.round((currentEvent.magnitude || 0) * 100)}%
              </div>
            </div>

            {currentEvent.description && (
              <p className="mt-3 text-xs sm:text-sm text-slate-300 leading-relaxed">
                {currentEvent.description}
              </p>
            )}

            {currentEvent.image_url && (
              <div className="mt-4 max-w-sm rounded-lg overflow-hidden border border-slate-700 bg-slate-900 aspect-video">
                <img
                  src={currentEvent.image_url}
                  alt={currentEvent.state}
                  className="w-full h-full object-cover"
                  onError={e => {
                    ;(e.currentTarget as HTMLElement).style.display = 'none'
                  }}
                />
              </div>
            )}
          </div>
        </div>
      </Card>

      {/* VERTICAL TIMELINE MILESTONES */}
      <Card
        title="Phase Transition History"
        subtitle="Chronological audit records derived from sequential imagery"
      >
        <div className="relative pl-6 space-y-6 before:absolute before:left-2 before:top-2 before:bottom-2 before:w-0.5 before:bg-slate-800">
          {temporal.map((t, idx) => {
            const isSelected = idx === selectedIdx
            return (
              <div
                key={idx}
                onClick={() => setSelectedIdx(idx)}
                className={`relative cursor-pointer group transition-all rounded-xl p-3 border ${
                  isSelected
                    ? 'border-amber-500/50 bg-amber-950/20'
                    : 'border-slate-800/80 bg-slate-900/40 hover:bg-slate-900'
                }`}
              >
                {/* Bullet */}
                <div
                  className={`absolute -left-[23px] top-4 h-3.5 w-3.5 rounded-full border-2 transition-all ${
                    isSelected
                      ? 'border-amber-400 bg-amber-400 shadow-md shadow-amber-400/50'
                      : 'border-slate-600 bg-slate-900 group-hover:border-slate-400'
                  }`}
                />

                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1">
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-slate-200 text-sm">{t.state}</span>
                    <span className="text-xs font-mono text-sky-400 font-semibold">{t.date}</span>
                  </div>
                  <span className="text-[11px] text-slate-400 font-mono">
                    Relative delta: {Math.round((t.magnitude || 0) * 100)}%
                  </span>
                </div>

                {t.description && (
                  <p className="mt-1 text-xs text-slate-400 leading-relaxed">
                    {t.description}
                  </p>
                )}
              </div>
            )
          })}
        </div>
      </Card>
    </div>
  )
}
