import { forwardRef, useEffect, useImperativeHandle, useRef, useState } from 'react'
import L from 'leaflet'
import type { BBox, Investigation } from '../types'

export type Base = 'street' | 'sat' | 'hybrid'
export interface MapHandle { flyTo(lat: number, lon: number): void; centerBox(): BBox }
export interface Layers { sensitive: boolean; change: boolean; bbox: boolean }
interface Props { bbox: BBox | null; onBbox: (b: BBox) => void; data?: Investigation; layers: Layers; drawing: boolean; base: Base }
// Esri World Imagery as the stand-in base. In production the backend supplies observations.t1/t2.tile_url.
const SAT = 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}'

const OSM = 'https://tile.openstreetmap.org/{z}/{x}/{y}.png'
const LABELS = 'https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}'

// Leaflet uses [lat, lng]; the rest of the app is GeoJSON [lng, lat]. Conversion stays in this file.
export default forwardRef<MapHandle, Props>(function MapView({ bbox, onBbox, data, layers, drawing, base }, ref) {
  const el = useRef<HTMLDivElement>(null)
  const map = useRef<L.Map>()
  const g = useRef<Record<keyof Layers, L.LayerGroup>>()
  const labels = useRef<L.TileLayer>()
  const tiles = useRef<{ a: L.TileLayer; b: L.TileLayer }>()
  useImperativeHandle(ref, () => ({
    flyTo: (la, lo) => { map.current?.setView([la, lo], 16) },
    centerBox: () => { const b = map.current!.getBounds().pad(-0.3); return [b.getWest(), b.getSouth(), b.getEast(), b.getNorth()] as BBox },
  }), [])
  const [split, setSplit] = useState(0.5)
  const splitRef = useRef(0.5); splitRef.current = split
  const drawRef = useRef(drawing); drawRef.current = drawing
  const cb = useRef(onBbox); cb.current = onBbox

  const clip = () => { // swipe compare: T1 on the left of the handle, T2 on the right
    const m = map.current, t = tiles.current; if (!m || !t) return
    const sz = m.getSize(), nw = m.containerPointToLayerPoint([0, 0]), se = m.containerPointToLayerPoint(sz)
    const x = m.containerPointToLayerPoint([sz.x * splitRef.current, 0]).x
    ;(t.a.getContainer() as HTMLElement).style.clip = `rect(${nw.y}px,${x}px,${se.y}px,${nw.x}px)`
    ;(t.b.getContainer() as HTMLElement).style.clip = `rect(${nw.y}px,${se.x}px,${se.y}px,${x}px)`
  }

  useEffect(() => {
    const m = L.map(el.current!, { center: [26.45, 80.35], zoom: 15, boxZoom: false, zoomControl: false })
    L.control.zoom({ position: 'bottomright' }).addTo(m)
    const opt = { attribution: 'Imagery © Esri', maxZoom: 19 }
    tiles.current = { a: L.tileLayer(SAT, opt).addTo(m), b: L.tileLayer(SAT, opt).addTo(m) }
    m.createPane('labels'); const lp = m.getPane('labels')!; lp.style.zIndex = '350'; lp.style.pointerEvents = 'none'
    labels.current = L.tileLayer(LABELS, { pane: 'labels', maxZoom: 19 }) // place names for hybrid mode
    m.attributionControl.addAttribution('© OpenStreetMap contributors')
    g.current = { sensitive: L.layerGroup(), change: L.layerGroup(), bbox: L.layerGroup() }
    let start: L.LatLng | null = null, rect: L.Rectangle | null = null
    m.on('mousedown', (e: L.LeafletMouseEvent) => { if (!drawRef.current) return; m.dragging.disable(); start = e.latlng })
    m.on('mousemove', (e: L.LeafletMouseEvent) => { if (!start) return; rect?.remove(); rect = L.rectangle(L.latLngBounds(start, e.latlng), { color: '#22a7f0', weight: 2, dashArray: '6 4' }).addTo(m) })
    m.on('mouseup', (e: L.LeafletMouseEvent) => {
      if (!start) return
      const b = L.latLngBounds(start, e.latlng); start = null; rect?.remove(); rect = null; m.dragging.enable()
      if (b.getEast() - b.getWest() > 1e-5) cb.current([b.getWest(), b.getSouth(), b.getEast(), b.getNorth()])
    })
    map.current = m
    m.on('move zoom resize', clip); clip()
    return () => { m.remove() }
  }, [])

  useEffect(clip, [split])
  useEffect(() => {
    g.current!.sensitive.clearLayers(); g.current!.change.clearLayers()
    if (data?.gis) L.geoJSON(data.gis.sensitive_geojson, { style: { color: '#22d3ee', dashArray: '6 4', fillOpacity: 0.12 } }).addTo(g.current!.sensitive)
    if (data?.detection) L.geoJSON(data.detection.polygon, { style: { color: '#ef4444', dashArray: '5 3', fillColor: '#f59e0b', fillOpacity: 0.45 } }).addTo(g.current!.change)
    if (data) map.current!.fitBounds([[data.bbox[1], data.bbox[0]], [data.bbox[3], data.bbox[2]]], { maxZoom: 17 })
  }, [data])
  useEffect(() => { // base map: street (OSM names), satellite, or satellite + place names
    const u = (t?: string) => (base === 'street' ? OSM : t ?? SAT)
    tiles.current!.a.setUrl(u(data?.observations.t1.tile_url)); tiles.current!.b.setUrl(u(data?.observations.t2.tile_url))
    base === 'hybrid' ? map.current!.addLayer(labels.current!) : map.current!.removeLayer(labels.current!)
  }, [data, base])
  useEffect(() => {
    (Object.keys(layers) as (keyof Layers)[]).forEach(k => { layers[k] ? map.current!.addLayer(g.current![k]) : map.current!.removeLayer(g.current![k]) })
  }, [layers])
  useEffect(() => {
    g.current!.bbox.clearLayers()
    if (bbox) L.rectangle([[bbox[1], bbox[0]], [bbox[3], bbox[2]]], { color: '#22a7f0', weight: 2, dashArray: '6 4', fillOpacity: 0.08 }).addTo(g.current!.bbox)
  }, [bbox])

  const drag = (e: React.PointerEvent<HTMLDivElement>) => {
    if (e.buttons !== 1) return
    const r = el.current!.getBoundingClientRect(); setSplit(Math.min(0.97, Math.max(0.03, (e.clientX - r.left) / r.width)))
  }
  return <div className="relative h-full w-full">
    <div ref={el} className="h-full w-full" style={{ cursor: drawing ? 'crosshair' : undefined }} />
    <div className="absolute inset-y-0 z-[1000] w-0.5 bg-sky-400" style={{ left: `${split * 100}%` }}>
      <div role="slider" aria-label="Compare T1 and T2" aria-valuenow={Math.round(split * 100)} tabIndex={0}
        onPointerDown={e => e.currentTarget.setPointerCapture(e.pointerId)} onPointerMove={drag}
        onKeyDown={e => { if (e.key === 'ArrowLeft') setSplit(s => Math.max(0.03, s - 0.03)); if (e.key === 'ArrowRight') setSplit(s => Math.min(0.97, s + 0.03)) }}
        className="absolute left-1/2 top-1/2 flex h-9 w-9 -translate-x-1/2 -translate-y-1/2 cursor-ew-resize touch-none items-center justify-center rounded-full border-2 border-sky-400 bg-slate-900 text-sky-300">‹›</div>
      <span className="glass mono absolute right-2 top-16 whitespace-nowrap px-2 py-0.5 text-xs">T1 Historical</span>
      <span className="glass mono absolute left-2 top-16 whitespace-nowrap px-2 py-0.5 text-xs">T2 Current</span>
    </div>
  </div>
})
