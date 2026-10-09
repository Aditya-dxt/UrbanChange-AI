import { useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  ArrowRight,
  Calendar,
  Cloud,
  Crosshair,
  Layers as LayersIcon,
  MapPin,
  Play,
  RotateCcw,
  Search,
  Sparkles,
} from 'lucide-react'
import MapView, { type Base, type Layers, type MapHandle } from '../components/MapView'
import { ProgressSteps } from '../components/Panels'
import { Badge } from '../components/common/Badge'
import { useInvestigationStore } from '../store/useInvestigationStore'
import type { BBox } from '../types'

const CLASSES: [string, string][] = [
  ['Construction', '#ef4444'],
  ['Excavation', '#f59e0b'],
  ['Vegetation loss', '#34d399'],
  ['Infrastructure', '#a78bfa'],
  ['Water change', '#22d3ee'],
]

function computeAoi(b: BBox) {
  const [w, s, e, n] = b
  const lat = (s + n) / 2
  const km2 = Math.abs((e - w) * 111.32 * Math.cos((lat * Math.PI) / 180) * (n - s) * 110.57)
  return { km2, ha: km2 * 100, lat, lon: (w + e) / 2 }
}

export default function InvestigatePage() {
  const navigate = useNavigate()
  const mapRef = useRef<MapHandle>(null)

  const {
    activeInvestigation,
    phase,
    step,
    error,
    bbox,
    drawing,
    histDate,
    curDate,
    cloudCover,
    scenario,
    baseMap,
    layers,
    isMockML,
    setBbox,
    setDrawing,
    setHistDate,
    setCurDate,
    setCloudCover,
    setScenario,
    setBaseMap,
    setLayers,
    resetActive,
    executeDetection,
  } = useInvestigationStore()

  const [searchQuery, setSearchQuery] = useState('')
  const [searchMsg, setSearchMsg] = useState('')
  const [isControlsOpen, setIsControlsOpen] = useState(true)

  async function handleSearch(e: React.FormEvent) {
    e.preventDefault()
    if (!searchQuery.trim()) return
    setSearchMsg('Searching…')
    try {
      const res = await fetch(
        `https://nominatim.openstreetmap.org/search?format=json&limit=1&q=${encodeURIComponent(
          searchQuery
        )}`
      )
      const data = await res.json()
      if (data && data[0]) {
        mapRef.current?.flyTo(+data[0].lat, +data[0].lon)
        setSearchMsg('')
      } else {
        setSearchMsg('Place not found. Try a nearby city or landmark.')
      }
    } catch {
      setSearchMsg('Search unavailable. Zoom the map manually.')
    }
  }

  const aoi = bbox ? computeAoi(bbox) : null

  async function onRunDetection() {
    const result = await executeDetection()
    if (result) {
      // Stay on map or optionally show quick jump banner
    }
  }

  return (
    <div className="relative h-full w-full flex-1 overflow-hidden">
      {/* 
        LEAFLET MAP CONTAINER
        MapView is untouched and receives state directly from the store
      */}
      <div className="absolute inset-0 z-0">
        <MapView
          ref={mapRef}
          bbox={bbox}
          onBbox={b => {
            setBbox(b)
            setDrawing(false)
          }}
          data={activeInvestigation || undefined}
          layers={layers}
          drawing={drawing}
          base={baseMap}
        />
      </div>

      {/* TOP-LEFT: Search & AOI Status Bar */}
      <div className="absolute left-3 top-3 z-[1000] flex flex-col gap-2 max-w-[calc(100vw-24px)] sm:max-w-md">
        {/* Nominatim Search */}
        <form
          onSubmit={handleSearch}
          className="flex items-center gap-2 rounded-xl border border-slate-700/80 bg-slate-900/90 px-3 py-2 shadow-2xl backdrop-blur-md"
        >
          <Search className="h-4 w-4 shrink-0 text-slate-400" />
          <input
            type="text"
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            placeholder="Search place, e.g. Kanpur, Lucknow, Noida"
            className="w-full bg-transparent text-xs text-slate-100 placeholder-slate-400 focus:outline-none"
            aria-label="Search place"
          />
          {searchQuery && (
            <button
              type="button"
              onClick={() => {
                setSearchQuery('')
                setSearchMsg('')
              }}
              className="text-xs text-slate-400 hover:text-slate-200"
            >
              ×
            </button>
          )}
        </form>
        {searchMsg && (
          <div className="rounded-lg bg-slate-900/90 border border-slate-800 px-3 py-1 text-[11px] text-amber-400 shadow-md">
            {searchMsg}
          </div>
        )}

        {/* AOI Metrics Pill */}
        <div className="flex items-center gap-2 rounded-xl border border-slate-700/80 bg-slate-900/90 px-3 py-2 text-xs shadow-2xl backdrop-blur-md">
          <MapPin className="h-4 w-4 text-sky-400 shrink-0" />
          {aoi ? (
            <div className="flex flex-wrap items-center gap-1.5 font-mono text-[11px] text-slate-300">
              <span>AOI:</span>
              <b className="text-sky-400">{aoi.km2.toFixed(3)} km²</b>
              <span className="text-slate-500">({aoi.ha.toFixed(1)} ha)</span>
              <span className="text-slate-600 hidden sm:inline">·</span>
              <span className="text-slate-400 hidden sm:inline">
                {aoi.lat.toFixed(4)}°N, {aoi.lon.toFixed(4)}°E
              </span>
            </div>
          ) : (
            <span className="text-slate-400 text-xs">
              Draw an AOI box on the map to define your study area.
            </span>
          )}
        </div>
      </div>

      {/* TOP-RIGHT: Map Tools & Layer Chooser */}
      <div className="absolute right-3 top-3 z-[1000] flex flex-col items-end gap-2">
        {/* Draw & View Actions */}
        <div className="flex items-center gap-1.5 rounded-xl border border-slate-700/80 bg-slate-900/90 p-1.5 shadow-2xl backdrop-blur-md">
          <button
            onClick={() => setDrawing(!drawing)}
            className={`flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-xs font-medium transition-all ${
              drawing
                ? 'bg-sky-500 text-white shadow-md shadow-sky-500/30'
                : 'text-slate-300 hover:bg-slate-800 hover:text-white'
            }`}
            title="Click and drag to draw bounding box"
          >
            <Crosshair className="h-3.5 w-3.5" />
            {drawing ? 'Drawing…' : 'Draw AOI'}
          </button>

          <button
            onClick={() => mapRef.current && setBbox(mapRef.current.centerBox())}
            className="flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-xs font-medium text-slate-300 hover:bg-slate-800 hover:text-white transition-all"
            title="Create AOI from current map viewport"
          >
            Use View
          </button>

          <button
            onClick={() => {
              setBbox(null)
              resetActive()
            }}
            className="flex items-center gap-1 rounded-lg px-2 py-1.5 text-xs font-medium text-slate-400 hover:bg-slate-800 hover:text-rose-400 transition-all"
            title="Clear current AOI and results"
          >
            <RotateCcw className="h-3.5 w-3.5" />
          </button>
        </div>

        {/* Base Map Selector */}
        <div className="flex items-center gap-1 rounded-xl border border-slate-700/80 bg-slate-900/90 p-1 shadow-2xl backdrop-blur-md text-[11px]">
          {(
            [
              ['street', 'Street'],
              ['sat', 'Satellite'],
              ['hybrid', 'Hybrid'],
            ] as [Base, string][]
          ).map(([key, label]) => (
            <button
              key={key}
              onClick={() => setBaseMap(key)}
              className={`rounded-lg px-2.5 py-1 font-medium transition-colors ${
                baseMap === key
                  ? 'bg-sky-500/20 text-sky-300 border border-sky-500/40 font-semibold'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* FLOATING DETECTION CONTROLLER (BOTTOM-RIGHT / DOCKED PANEL) */}
      <div className="absolute right-3 bottom-5 z-[1000] w-84 sm:w-96 max-w-[calc(100vw-24px)] rounded-2xl border border-slate-700/80 bg-slate-950/95 p-4 shadow-2xl backdrop-blur-md flex flex-col gap-3">
        <div className="flex items-center justify-between border-b border-slate-800 pb-2">
          <div className="flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-sky-400" />
            <span className="text-xs font-bold text-slate-200 tracking-wide uppercase">
              Observation Controls
            </span>
          </div>
          <button
            onClick={() => setIsControlsOpen(!isControlsOpen)}
            className="text-xs text-slate-400 hover:text-slate-200"
          >
            {isControlsOpen ? 'Minimize' : 'Expand'}
          </button>
        </div>

        {isControlsOpen && (
          <>
            {/* Observation Dates */}
            <div className="grid grid-cols-2 gap-2 text-xs">
              <label className="flex flex-col gap-1 text-slate-400">
                <span className="flex items-center gap-1 font-medium">
                  <Calendar className="h-3 w-3 text-sky-400" /> Historical (T1)
                </span>
                <input
                  type="date"
                  value={histDate}
                  max={curDate}
                  onChange={e => setHistDate(e.target.value)}
                  className="rounded-lg border border-slate-800 bg-slate-900 px-2 py-1.5 text-xs text-slate-200 focus:border-sky-500 focus:outline-none"
                />
              </label>

              <label className="flex flex-col gap-1 text-slate-400">
                <span className="flex items-center gap-1 font-medium">
                  <Calendar className="h-3 w-3 text-sky-400" /> Current (T2)
                </span>
                <input
                  type="date"
                  value={curDate}
                  min={histDate}
                  onChange={e => setCurDate(e.target.value)}
                  className="rounded-lg border border-slate-800 bg-slate-900 px-2 py-1.5 text-xs text-slate-200 focus:border-sky-500 focus:outline-none"
                />
              </label>
            </div>

            {/* Cloud Cover Slider */}
            <div className="flex flex-col gap-1 text-xs">
              <div className="flex justify-between text-slate-400">
                <span className="flex items-center gap-1">
                  <Cloud className="h-3 w-3 text-sky-400" /> Max Cloud Cover
                </span>
                <b className="font-mono text-sky-300">{cloudCover}%</b>
              </div>
              <input
                type="range"
                min={0}
                max={80}
                value={cloudCover}
                onChange={e => setCloudCover(+e.target.value)}
                className="w-full accent-sky-400 cursor-pointer"
                aria-label="Max Cloud Cover"
              />
            </div>

            {/* Mock Scenario (if mock adapter active) */}
            {isMockML && (
              <div className="flex items-center justify-between text-xs text-slate-400 border-t border-slate-900 pt-2">
                <span>Simulation Scenario</span>
                <select
                  value={scenario}
                  onChange={e => setScenario(e.target.value)}
                  className="rounded-md border border-slate-800 bg-slate-900 px-2 py-1 text-xs text-slate-200"
                >
                  <option value="ok">Success (Detected)</option>
                  <option value="low">Low Confidence (&lt;60%)</option>
                  <option value="partial">Partial (No Timeline)</option>
                  <option value="empty">No Change Detected</option>
                  <option value="fail">Pipeline Error</option>
                </select>
              </div>
            )}

            {/* Pipeline Execution Status Overlay if Loading */}
            {phase === 'loading' && (
              <div className="rounded-xl border border-sky-500/30 bg-sky-950/20 p-3">
                <ProgressSteps step={step} />
              </div>
            )}

            {/* Error Message if Failed */}
            {phase === 'error' && (
              <div className="rounded-xl border border-rose-500/40 bg-rose-950/30 p-2.5 text-xs text-rose-300 leading-relaxed">
                <b>Analysis Failed:</b> {error}
                <button
                  onClick={onRunDetection}
                  className="block mt-1.5 text-sky-400 underline font-semibold"
                >
                  Retry Execution
                </button>
              </div>
            )}

            {/* Action Trigger Button */}
            <button
              onClick={onRunDetection}
              disabled={!bbox || phase === 'loading'}
              className="btn flex items-center justify-center gap-2 py-2.5 text-xs font-bold tracking-wider uppercase transition-all shadow-lg"
            >
              <Play className="h-3.5 w-3.5" />
              {phase === 'loading' ? 'Executing Pipeline…' : 'Execute AI Change Detection'}
            </button>

            {!bbox && (
              <div className="text-center text-[11px] text-slate-500">
                Draw or specify an AOI box on the map to enable detection.
              </div>
            )}

            {/* If Detection Completed: Shortcut to Detailed Pages */}
            {activeInvestigation && phase === 'done' && (
              <div className="flex items-center justify-between rounded-xl border border-emerald-500/30 bg-emerald-950/20 p-2.5 text-xs">
                <div className="flex flex-col">
                  <span className="font-semibold text-emerald-300">Analysis Complete</span>
                  <span className="text-[10px] text-emerald-400/80">
                    {activeInvestigation.detection?.area_m2.toLocaleString()} m² change flagged
                  </span>
                </div>
                <button
                  onClick={() => navigate('/results')}
                  className="flex items-center gap-1 rounded-lg bg-emerald-500/20 px-2.5 py-1 text-xs font-semibold text-emerald-300 hover:bg-emerald-500/30 transition-colors"
                >
                  Results <ArrowRight className="h-3 w-3" />
                </button>
              </div>
            )}
          </>
        )}
      </div>

      {/* BOTTOM-LEFT: Map Legend and Layer Toggles */}
      <div className="absolute left-3 bottom-5 z-[1000] hidden sm:flex flex-col gap-2 rounded-2xl border border-slate-700/80 bg-slate-950/90 p-3 shadow-2xl backdrop-blur-md w-64 text-xs">
        <div className="flex items-center justify-between border-b border-slate-800 pb-1.5">
          <span className="font-semibold text-slate-300 text-[11px] uppercase tracking-wider flex items-center gap-1.5">
            <LayersIcon className="h-3 w-3 text-sky-400" />
            Active Overlays
          </span>
          <span className="text-[10px] text-slate-500 font-mono">EPSG:4326</span>
        </div>

        {/* Layer Switches */}
        <div className="flex flex-col gap-1.5 py-1 text-slate-300">
          <label className="flex items-center gap-2 cursor-pointer hover:text-white transition-colors">
            <input
              type="checkbox"
              checked={layers.sensitive}
              onChange={e => setLayers({ sensitive: e.target.checked })}
              className="rounded border-slate-700 bg-slate-800 text-sky-500"
            />
            Sensitive Planning Zones
          </label>
          <label className="flex items-center gap-2 cursor-pointer hover:text-white transition-colors">
            <input
              type="checkbox"
              checked={layers.change}
              onChange={e => setLayers({ change: e.target.checked })}
              className="rounded border-slate-700 bg-slate-800 text-sky-500"
            />
            AI Change Polygons
          </label>
          <label className="flex items-center gap-2 cursor-pointer hover:text-white transition-colors">
            <input
              type="checkbox"
              checked={layers.bbox}
              onChange={e => setLayers({ bbox: e.target.checked })}
              className="rounded border-slate-700 bg-slate-800 text-sky-500"
            />
            AOI Boundary Box
          </label>
        </div>

        {/* Change Classes Legend */}
        <div className="border-t border-slate-800 pt-2">
          <div className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider mb-1.5">
            Class Signatures
          </div>
          <div className="grid grid-cols-2 gap-x-2 gap-y-1 text-[11px]">
            {CLASSES.map(([name, color]) => (
              <span key={name} className="flex items-center gap-1.5 text-slate-400">
                <i className="inline-block h-2 w-2 rounded-sm" style={{ background: color }} />
                {name}
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* DRAWING GUIDE TOAST */}
      {drawing && (
        <div className="absolute top-16 left-1/2 -translate-x-1/2 z-[1000] rounded-xl border border-sky-400/50 bg-slate-900/95 px-4 py-2 text-xs font-semibold text-sky-300 shadow-2xl backdrop-blur-md animate-bounce">
          Click and drag on the map to define the bounding box
        </div>
      )}

      {/* EMPTY ONBOARDING CALLOUT IF NO AOI */}
      {!bbox && !drawing && (
        <div className="pointer-events-none absolute inset-0 z-[990] flex items-center justify-center p-4">
          <div className="pointer-events-auto max-w-sm rounded-2xl border border-slate-700/80 bg-slate-950/95 p-5 shadow-2xl backdrop-blur-md">
            <div className="flex items-center gap-2 text-sky-400 font-bold text-base mb-1">
              <Sparkles className="h-5 w-5" /> Start an Investigation
            </div>
            <p className="text-xs text-slate-400 leading-relaxed">
              Define a geographic bounding box (AOI) to initiate multi-temporal Sentinel-2 retrieval,
              bi-temporal change segmentation, and GIS zone intersection.
            </p>
            <ol className="mt-3 list-decimal pl-4 text-xs text-slate-300 space-y-1">
              <li>Search a location or navigate the map.</li>
              <li>Click &quot;Draw AOI&quot; or &quot;Use View&quot;.</li>
              <li>Select observation dates and run detection.</li>
            </ol>
            <div className="mt-4 flex gap-2">
              <button onClick={() => setDrawing(true)} className="btn text-xs py-1.5">
                Draw AOI Box
              </button>
              <button
                onClick={() => mapRef.current && setBbox(mapRef.current.centerBox())}
                className="btn-ghost text-xs py-1.5 border border-slate-700"
              >
                Use Current View
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
