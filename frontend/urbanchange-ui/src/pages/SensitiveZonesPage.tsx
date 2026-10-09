import { useNavigate } from 'react-router-dom'
import {
  AlertCircle,
  AlertTriangle,
  Compass,
  FileWarning,
  Globe2,
  Info,
  MapPin,
  Shield,
  ShieldAlert,
  ShieldCheck,
} from 'lucide-react'
import { Card } from '../components/common/Card'
import { EmptyState } from '../components/common/EmptyState'
import { Badge } from '../components/common/Badge'
import { StatTile } from '../components/common/StatTile'
import { useInvestigationStore } from '../store/useInvestigationStore'

export default function SensitiveZonesPage() {
  const navigate = useNavigate()
  const { activeInvestigation } = useInvestigationStore()

  if (!activeInvestigation || !activeInvestigation.gis) {
    return (
      <div className="flex-1 p-6 flex items-center justify-center">
        <EmptyState
          title="No Sensitive Zone Data Available"
          description="Sensitive zone evaluations are computed automatically when an investigation is executed on an area."
          actionLabel="Go to Investigate Map"
          onAction={() => navigate('/investigate')}
          icon={<ShieldAlert className="h-8 w-8 text-cyan-400" />}
        />
      </div>
    )
  }

  const { gis, detection } = activeInvestigation
  const zones = gis.sensitive || []
  const hasOverlap = zones.some(z => z.overlap_percent > 0)
  const maxOverlap = zones.length > 0 ? Math.max(...zones.map(z => z.overlap_percent)) : 0

  return (
    <div className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8 space-y-6">
      {/* HEADER */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-mono text-cyan-400 font-semibold uppercase tracking-wider">
              Zoning & Environmental Integrity
            </span>
            <Badge variant={hasOverlap ? 'danger' : 'success'} size="sm">
              {hasOverlap ? 'Intersection Detected' : 'Clear of Protected Buffers'}
            </Badge>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-100 tracking-tight">
            Sensitive Zones & GIS Context
          </h1>
          <p className="text-xs sm:text-sm text-slate-400 mt-1">
            Spatial geometric intersection between identified change polygons and regional planning constraints.
          </p>
        </div>

        <button
          onClick={() => navigate('/results')}
          className="btn-ghost text-xs border border-slate-700/80 self-start sm:self-auto"
        >
          ← Back to Results
        </button>
      </div>

      {/* STATUTORY DISCLAIMER BANNER */}
      <div className="rounded-xl border border-amber-500/40 bg-amber-950/20 p-4 shadow-sm">
        <div className="flex items-start gap-3">
          <AlertTriangle className="h-5 w-5 text-amber-400 shrink-0 mt-0.5" />
          <div className="text-xs sm:text-sm text-amber-200/90 leading-relaxed">
            <b className="font-semibold text-amber-300">
              Statutory Notice: Requires Human Verification
            </b>
            <p className="mt-1 text-slate-300">
              Spatial overlap indicates geometric intersection with configured cadastral buffers and regional
              environmental layers. It does not establish legal title, statutory breach, or authorized permit status.
            </p>
          </div>
        </div>
      </div>

      {/* SAMPLE LAYER DISCLAIMER */}
      <div className="rounded-xl border border-slate-700/80 bg-slate-900/60 p-4 text-xs text-slate-300 leading-relaxed">
        <div className="flex items-center gap-2 text-cyan-400 font-semibold mb-1">
          <Info className="h-4 w-4" /> Sample Data & Baselining Notice
        </div>
        <p className="text-slate-400">
          Planning layers in this environment are synthesized from regional master planning records,
          OpenStreetMap land-use geometries, and the European Space Agency (ESA) 10m WorldCover catalog.
          Operational legal enforcement requires certified revenue maps from local authorities.
        </p>
      </div>

      {/* STATS TILES */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatTile
          label="Intersected Layers"
          value={zones.length.toString()}
          subValue={hasOverlap ? 'Active zone conflicts' : 'Zero conflicts'}
          variant={hasOverlap ? 'warning' : 'success'}
        />
        <StatTile
          label="Max Buffer Overlap"
          value={`${maxOverlap}%`}
          subValue={maxOverlap > 0 ? 'Peak overlap recorded' : 'Clean buffer'}
          variant={maxOverlap > 0 ? 'danger' : 'default'}
        />
        <StatTile
          label="Baseline Land Cover"
          value={gis.landcover || 'Unspecified'}
          subValue="ESA WorldCover 10m"
          variant="default"
        />
        <StatTile
          label="Coordinate System"
          value="EPSG:4326"
          subValue="Projected WGS84"
          variant="default"
        />
      </div>

      {/* DETAILED OVERLAP TABLE */}
      <Card
        title="Planning Buffer Intersections"
        subtitle="Geospatial polygon intersection breakdown"
      >
        {zones.length === 0 ? (
          <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-6 text-center text-xs text-slate-400">
            <ShieldCheck className="h-8 w-8 text-emerald-400 mx-auto mb-2" />
            No sensitive layers configured or intersected within this bounding box.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs sm:text-sm">
              <thead className="border-b border-slate-800 text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                <tr>
                  <th className="pb-3 pr-4">Protected Layer</th>
                  <th className="pb-3 px-4">Overlap %</th>
                  <th className="pb-3 px-4">Est. Area</th>
                  <th className="pb-3 px-4">Authority Source</th>
                  <th className="pb-3 pl-4 text-right">Verification Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800 text-slate-200">
                {zones.map((zone, idx) => {
                  const estArea = detection
                    ? Math.round((detection.area_m2 * zone.overlap_percent) / 100)
                    : 0

                  return (
                    <tr key={idx} className="hover:bg-slate-900/40 transition-colors">
                      <td className="py-3.5 pr-4 font-semibold text-slate-100">
                        <div className="flex items-center gap-2">
                          <ShieldAlert className="h-4 w-4 text-cyan-400 shrink-0" />
                          <span>{zone.layer}</span>
                        </div>
                      </td>
                      <td className="py-3.5 px-4 font-mono font-bold">
                        <span
                          className={`rounded px-2 py-0.5 ${
                            zone.overlap_percent > 50
                              ? 'bg-rose-950/60 text-rose-300 border border-rose-800/40'
                              : 'bg-amber-950/60 text-amber-300 border border-amber-800/40'
                          }`}
                        >
                          {zone.overlap_percent}%
                        </span>
                      </td>
                      <td className="py-3.5 px-4 font-mono text-slate-300">
                        {estArea > 0 ? `${estArea.toLocaleString()} m²` : '—'}
                      </td>
                      <td className="py-3.5 px-4 text-xs text-slate-400">
                        {zone.source}
                      </td>
                      <td className="py-3.5 pl-4 text-right">
                        <Badge variant="warning" size="sm">
                          Requires Human Verification
                        </Badge>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {/* BASELINE LAND COVER PROFILE */}
      <Card
        title="Ecological Context: Baseline Land Cover"
        subtitle="ESA 10m WorldCover Classification"
      >
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-2 text-xs sm:text-sm">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-xl bg-cyan-950/60 border border-cyan-800/50 flex items-center justify-center text-cyan-300">
              <Globe2 className="h-5 w-5" />
            </div>
            <div>
              <div className="text-slate-400 text-xs">Dominant Land Class (Pre-disturbance)</div>
              <div className="text-base font-bold text-slate-100">{gis.landcover}</div>
            </div>
          </div>
          <div className="text-xs text-slate-400 max-w-sm">
            Baseline classification helps distinguish lawful agricultural harvesting or seasonal bare soil
            from high-impact artificial compaction or permanent structural erection.
          </div>
        </div>
      </Card>
    </div>
  )
}
