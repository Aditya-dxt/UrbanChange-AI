import { useRef, useState } from 'react'
import MapView, { type Base, type Layers, type MapHandle } from './components/MapView'
import UploadMode from './components/UploadMode'
import Assistant from './components/Assistant'
import { Banner, EvidencePanel, FingerprintCard, GisPanel, ProgressSteps, Timeline } from './components/Panels'
import { useInvestigation } from './hooks/useInvestigation'
import type { BBox } from './types'

type Tab = 'detect' | 'gis' | 'fp' | 'time' | 'ask' | 'upload'
const TABS: [Tab, string][] = [['detect', 'Detect'], ['gis', 'GIS zones'], ['fp', 'Fingerprint'], ['time', 'Timeline'], ['ask', 'Assistant'], ['upload', 'Upload']]
const CLASSES: [string, string][] = [['Construction', '#ef4444'], ['Excavation', '#f59e0b'], ['Vegetation loss', '#34d399'], ['Infrastructure', '#a78bfa'], ['Water change', '#22d3ee']]
const Empty = ({ t }: { t: string }) => <div className="card mu text-sm">{t}</div>
const iso = (d: Date) => d.toISOString().slice(0, 10)

function aoi(b: BBox) {
  const [w, s, e, n] = b, lat = (s + n) / 2
  const km2 = Math.abs((e - w) * 111.32 * Math.cos(lat * Math.PI / 180) * (n - s) * 110.57)
  return { km2, ha: km2 * 100, lat, lon: (w + e) / 2 }
}

export default function App() {
  const [tab, setTab] = useState<Tab>('detect')
  const [bbox, setBbox] = useState<BBox | null>(null)
  const [drawing, setDrawing] = useState(false)
  const [hist, setHist] = useState('2025-01-05')
  const [cur, setCur] = useState(iso(new Date()))
  const [base, setBase] = useState<Base>('hybrid')
  const [cloud, setCloud] = useState(10)
  const [scenario, setScenario] = useState('ok')
  const [tIdx, setTIdx] = useState(0)
  const [layers, setLayers] = useState<Layers>({ sensitive: true, change: true, bbox: true })
  const { state, detect, reset } = useInvestigation()
  const mapRef = useRef<MapHandle>(null)
  const [q, setQ] = useState(''), [searchMsg, setSearchMsg] = useState('')
  async function search(e: React.FormEvent) {
    e.preventDefault(); if (!q.trim()) return
    setSearchMsg('Searching…')
    try {
      const r = await (await fetch(`https://nominatim.openstreetmap.org/search?format=json&limit=1&q=${encodeURIComponent(q)}`)).json()
      if (r[0]) { mapRef.current?.flyTo(+r[0].lat, +r[0].lon); setSearchMsg('') } else setSearchMsg('Place not found. Try a nearby city or landmark.')
    } catch { setSearchMsg('Search unavailable. Zoom the map manually.') }
  }
  const d = state.data, det = d?.detection
  const mock = import.meta.env.VITE_USE_MOCK !== 'false'
  const run = () => bbox && detect({ bbox, historical_date: hist.slice(0, 7), current_date: cur, max_cloud: cloud, scenario })
  const a = bbox ? aoi(bbox) : null

  return <div className="flex min-h-screen flex-col lg:h-screen">
    <header className="flex flex-wrap items-center justify-between gap-2 border-b px-4 py-2" style={{ borderColor: 'var(--line)', background: 'var(--panel)' }}>
      <div className="flex items-center gap-3">
        <svg width="30" height="30" viewBox="0 0 32 32" aria-hidden><rect width="32" height="32" rx="8" fill="#0ea5e9" /><rect x="7" y="7" width="18" height="18" fill="none" stroke="#04121f" strokeWidth="2.5" /><rect x="13" y="13" width="7" height="7" fill="#04121f" /></svg>
        <div><div className="display text-base font-bold tracking-wide">URBANCHANGE AI</div>
          <div className="label">Explainable satellite change detection</div></div>
      </div>
      <div className="flex items-center gap-2">
        {d?.fingerprint && <span className="label rounded-lg border px-3 py-1.5" style={{ borderColor: 'var(--line)' }}>ID: <b className="text-sky-400">{d.fingerprint.id}</b></span>}
      </div>
    </header>

    <main className="flex min-h-0 flex-1 flex-col lg:flex-row">
      <div className="relative h-[60vh] lg:h-auto lg:flex-1">
        <MapView ref={mapRef} bbox={bbox} onBbox={b => { setBbox(b); setDrawing(false) }} data={d} layers={layers} drawing={drawing} base={base} />
        <div className="glass mono absolute left-3 top-3 z-[1000] max-w-[70%] px-3 py-1.5 text-xs">
          {a ? <>AOI area: <b className="text-sky-400">{a.km2.toFixed(3)} km²</b> <span className="mu">({a.ha.toFixed(1)} ha)</span> · {a.lat.toFixed(4)}°N, {a.lon.toFixed(4)}°E</> : 'Draw an AOI box to begin'}
        </div>
        <form onSubmit={search} className="glass absolute left-3 top-14 z-[1000] flex w-64 max-w-[70%] flex-col gap-1 p-1.5">
          <input value={q} onChange={e => setQ(e.target.value)} placeholder="Search a place, e.g. Kanpur" aria-label="Search a place" />
          {searchMsg && <span className="mu px-1 text-xs">{searchMsg}</span>}
        </form>
        {!bbox && !drawing && <div className="pointer-events-none absolute inset-0 z-[1000] flex items-center justify-center p-4"><div className="glass pointer-events-auto max-w-sm p-5">
          <div className="display text-xl font-bold">Start in 3 steps</div>
          <ol className="mu mt-2 list-decimal pl-5 text-sm"><li>Search a place or zoom to your area</li><li>Draw a box around it</li><li>Pick dates and run detection</li></ol>
          <div className="mt-3 flex flex-wrap gap-2"><button className="btn" onClick={() => setDrawing(true)}>Draw AOI box</button>
            <button className="btn-ghost" onClick={() => mapRef.current && setBbox(mapRef.current.centerBox())}>Use current view</button></div></div></div>}
        {drawing && <div className="glass absolute bottom-3 left-1/2 z-[1000] -translate-x-1/2 px-4 py-2 text-sm">Click and drag on the map to draw your box</div>}
        <div className="glass absolute right-3 top-3 z-[1000] flex gap-1 p-1">
          <button className={`btn-ghost text-sm ${drawing ? 'on' : ''}`} onClick={() => setDrawing(v => !v)}>{drawing ? 'Drag on map…' : 'Draw AOI box'}</button>
          <button className="btn-ghost text-sm" onClick={() => mapRef.current && setBbox(mapRef.current.centerBox())}>Use view</button>
          <button className="btn-ghost text-sm" onClick={() => { setBbox(null); reset() }}>Reset</button>
        </div>
        <div className="glass absolute right-3 top-16 z-[1000] flex gap-1 p-1" role="group" aria-label="Base map">
          {([['street', 'Street'], ['sat', 'Satellite'], ['hybrid', 'Satellite + names']] as [Base, string][]).map(([k, n]) =>
            <button key={k} className={`btn-ghost text-xs ${base === k ? 'on' : ''}`} onClick={() => setBase(k)}>{n}</button>)}
        </div>
        <div className="glass absolute bottom-3 left-3 z-[1000] hidden w-60 p-3 text-xs sm:block">
          <div className="label mb-1">Detected change classes</div>
          <div className="grid grid-cols-2 gap-x-2 gap-y-1">{CLASSES.map(([n, c]) => <span key={n} className="flex items-center gap-1.5"><i className="inline-block h-2.5 w-2.5 rounded-sm" style={{ background: c }} />{n}</span>)}</div>
          <div className="label mb-1 mt-3">Layers</div>
          {([['sensitive', 'Sensitive zones'], ['change', 'Change regions'], ['bbox', 'AOI selection']] as [keyof Layers, string][]).map(([k, n]) =>
            <label key={k} className="flex gap-2"><input type="checkbox" checked={layers[k]} onChange={e => setLayers(l => ({ ...l, [k]: e.target.checked }))} />{n}</label>)}
          <div className="mu mono mt-2">Sentinel-2 (10 m) · EPSG:4326</div>
        </div>
      </div>

      <aside className="flex w-full flex-col border-t lg:w-[450px] lg:border-l lg:border-t-0" style={{ borderColor: 'var(--line)', background: 'var(--panel)' }}>
        <nav className="flex overflow-x-auto border-b" style={{ borderColor: 'var(--line)' }} aria-label="Panels">
          {TABS.map(([k, n]) => <button key={k} className={`stab ${tab === k ? 'on' : ''}`} onClick={() => setTab(k)}>{n}</button>)}</nav>
        <div className="flex flex-col gap-3 p-4 lg:flex-1 lg:overflow-y-auto">
          {tab === 'detect' && <>
            <section className="card">
              <div className="flex justify-between"><span className="label">Target bounding box</span>{a && <b className="mono text-xs text-sky-400">{a.km2.toFixed(3)} km²</b>}</div>
              {bbox ? <div className="mono mt-2 grid grid-cols-2 gap-2 text-xs"><span>SW: {bbox[1].toFixed(4)}, {bbox[0].toFixed(4)}</span><span>NE: {bbox[3].toFixed(4)}, {bbox[2].toFixed(4)}</span></div>
                : <p className="mu mt-2 text-sm">Click “Draw AOI box” on the map, then drag over the area you want to check.</p>}
            </section>
            <section className="card flex flex-col gap-3">
              <span className="label">Observation dates</span>
              <div className="grid grid-cols-2 gap-3">
                <label className="label">Historical (T1)<input type="date" value={hist} max={cur} onChange={e => setHist(e.target.value)} className="mt-1" /></label>
                <label className="label">Current (T2)<input type="date" value={cur} min={hist} onChange={e => setCur(e.target.value)} className="mt-1" /></label>
              </div>
              <label className="label flex justify-between">Max cloud cover <b className="text-sky-400">{cloud}%</b></label>
              <input type="range" min={0} max={80} value={cloud} onChange={e => setCloud(+e.target.value)} aria-label="Max cloud cover" />
              {mock && <label className="label">Mock scenario<select value={scenario} onChange={e => setScenario(e.target.value)} className="mt-1">
                {[['ok', 'Success'], ['low', 'Low confidence'], ['partial', 'Partial (no timeline)'], ['empty', 'No change'], ['fail', 'Backend failure']].map(([v, n]) => <option key={v} value={v}>{n}</option>)}</select></label>}
            </section>
            <button className="btn w-full tracking-wide" disabled={!bbox || state.phase === 'loading'} onClick={run}>{state.phase === 'loading' ? 'Analysing…' : 'EXECUTE AI CHANGE DETECTION'}</button>
            {!bbox && <p className="mu -mt-1 text-center text-xs">Draw an area first to enable detection.</p>}
            {state.phase === 'loading' && <div className="card"><ProgressSteps step={state.step} /></div>}
            {state.phase === 'error' && <Banner danger><b>Couldn’t finish the analysis.</b> {state.error}. <button className="underline" onClick={run}>Retry</button></Banner>}
            {d && <>
              <Banner><b className="label" style={{ color: 'var(--hot)' }}>Requires human verification · Not legal proof</b><br />{d.explanation}</Banner>
              {d.status === 'partial' && <Banner>Partial result: the timeline is unavailable for this area.</Banner>}
              {!det ? <Empty t="No significant change detected for this area and period." /> : <>
                {det.confidence < 0.6 && <Banner danger>Low confidence ({Math.round(det.confidence * 100)}%). Treat as unverified and review manually.</Banner>}
                <div className="grid grid-cols-2 gap-3">
                  <div className="card"><div className="label">Total changed footprint</div><div className="display mono mt-1 text-2xl font-bold">{det.area_m2.toLocaleString()} m²</div><div className="mu mono text-xs">{(det.area_m2 / 10000).toFixed(2)} ha</div></div>
                  <div className="card"><div className="label">Model confidence</div><div className="display mono mt-1 text-2xl font-bold" style={{ color: det.confidence < 0.6 ? 'var(--bad)' : 'var(--ok)' }}>{Math.round(det.confidence * 100)}%</div><div className="mu mono text-xs">{det.model_version}</div></div>
                </div>
                <div className="card flex items-center justify-between"><span><span className="label">Class</span><br /><b className="capitalize">{det.class}</b></span><span className={`pill prio-${det.priority}`}>{det.priority} priority</span></div>
              </>}
            </>}
          </>}
          {tab === 'gis' && (d?.gis ? <GisPanel gis={d.gis} /> : <Empty t="Run a detection to see sensitive-zone overlap and land-cover context." />)}
          {tab === 'fp' && (d?.fingerprint ? <><FingerprintCard f={d.fingerprint} /><EvidencePanel evidence={d.evidence} text={d.explanation} /></> : <Empty t="The change fingerprint and evidence appear after a detection that finds change." />)}
          {tab === 'time' && (d?.temporal ? <Timeline events={d.temporal} idx={Math.min(tIdx, d.temporal.length - 1)} onIdx={setTIdx} /> : <Empty t={d ? 'Timeline unavailable: not enough suitable intermediate observations.' : 'Run a detection to reconstruct how the change developed.'} />)}
          {tab === 'ask' && (d && det ? <Assistant investigationId={d.id} /> : <Empty t="The assistant answers from the computed evidence. Run a detection first." />)}
          {tab === 'upload' && <UploadMode />}
        </div>
      </aside>
    </main>
  </div>
}
