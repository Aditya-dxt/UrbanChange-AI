import { forwardRef, useEffect, useImperativeHandle, useRef, useState } from 'react'
import L from 'leaflet'
import type { BBox, Investigation } from '../types'

export type Base = 'street' | 'sat' | 'hybrid'
export interface MapHandle {
  flyTo(lat: number, lon: number): void
  centerBox(): BBox
}
export interface Layers {
  sensitive: boolean
  change: boolean
  bbox: boolean
}
interface Props {
  bbox: BBox | null
  onBbox: (b: BBox) => void
  data?: Investigation
  layers: Layers
  drawing: boolean
  base: Base
}

const SAT = 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}'
const OSM = 'https://tile.openstreetmap.org/{z}/{x}/{y}.png'
const LABELS = 'https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}'

export default forwardRef<MapHandle, Props>(function MapView(
  { bbox, onBbox, data, layers, drawing, base },
  ref
) {
  const el = useRef<HTMLDivElement>(null)
  const map = useRef<L.Map>()
  const g = useRef<Record<keyof Layers, L.LayerGroup>>()
  const labels = useRef<L.TileLayer>()
  const tiles = useRef<{ a: L.TileLayer; b: L.TileLayer }>()
  const imgOverlays = useRef<{ a?: L.ImageOverlay; b?: L.ImageOverlay }>({})

  useImperativeHandle(ref, () => ({
    flyTo: (la, lo) => {
      map.current?.setView([la, lo], 16)
    },
    centerBox: () => {
      const b = map.current!.getBounds().pad(-0.3)
      return [b.getWest(), b.getSouth(), b.getEast(), b.getNorth()] as BBox
    },
  }), [])

  const [split, setSplit] = useState(0.5)
  const splitRef = useRef(0.5)
  splitRef.current = split
  const drawRef = useRef(drawing)
  drawRef.current = drawing
  const cb = useRef(onBbox)
  cb.current = onBbox

  const clip = () => {
    const m = map.current
    const t = tiles.current
    if (!m || !t) return
    const sz = m.getSize()
    const nw = m.containerPointToLayerPoint([0, 0])
    const se = m.containerPointToLayerPoint(sz)
    const x = m.containerPointToLayerPoint([sz.x * splitRef.current, 0]).x
    ;(t.a.getContainer() as HTMLElement).style.clip = `rect(${nw.y}px,${x}px,${se.y}px,${nw.x}px)`
    ;(t.b.getContainer() as HTMLElement).style.clip = `rect(${nw.y}px,${se.x}px,${se.y}px,${x}px)`

    if (imgOverlays.current.a?.getElement()) {
      ;(imgOverlays.current.a.getElement() as HTMLElement).style.clip = `rect(${nw.y}px,${x}px,${se.y}px,${nw.x}px)`
    }
    if (imgOverlays.current.b?.getElement()) {
      ;(imgOverlays.current.b.getElement() as HTMLElement).style.clip = `rect(${nw.y}px,${se.x}px,${se.y}px,${x}px)`
    }
  }

  useEffect(() => {
    const m = L.map(el.current!, {
      center: [26.45, 80.35],
      zoom: 14,
      boxZoom: false,
      zoomControl: false,
    })
    L.control.zoom({ position: 'bottomright' }).addTo(m)
    const opt = { attribution: 'Imagery © Esri', maxZoom: 19 }
    tiles.current = { a: L.tileLayer(SAT, opt).addTo(m), b: L.tileLayer(SAT, opt).addTo(m) }
    const cA = tiles.current.a.getContainer()
    if (cA) {
      cA.style.filter = 'sepia(0.25) contrast(0.92) brightness(0.95)'
    }

    m.createPane('labels')
    const lp = m.getPane('labels')!
    lp.style.zIndex = '350'
    lp.style.pointerEvents = 'none'
    labels.current = L.tileLayer(LABELS, { pane: 'labels', maxZoom: 19 })
    m.attributionControl.addAttribution('© OpenStreetMap contributors')

    g.current = {
      sensitive: L.layerGroup().addTo(m),
      change: L.layerGroup().addTo(m),
      bbox: L.layerGroup().addTo(m),
    }

    let start: L.LatLng | null = null
    let rect: L.Rectangle | null = null

    m.on('mousedown', (e: L.LeafletMouseEvent) => {
      if (!drawRef.current) return
      m.dragging.disable()
      start = e.latlng
    })
    m.on('mousemove', (e: L.LeafletMouseEvent) => {
      if (!start) return
      rect?.remove()
      rect = L.rectangle(L.latLngBounds(start, e.latlng), {
        color: '#22a7f0',
        weight: 2,
        dashArray: '6 4',
      }).addTo(m)
    })
    m.on('mouseup', (e: L.LeafletMouseEvent) => {
      if (!start) return
      const b = L.latLngBounds(start, e.latlng)
      start = null
      rect?.remove()
      rect = null
      m.dragging.enable()
      if (b.getEast() - b.getWest() > 1e-5) {
        cb.current([b.getWest(), b.getSouth(), b.getEast(), b.getNorth()])
      }
    })

    map.current = m
    m.on('move zoom resize', clip)
    clip()
    return () => {
      m.remove()
    }
  }, [])

  useEffect(clip, [split])

  // Update vectors and fit bounds on investigation load
  useEffect(() => {
    if (!g.current || !map.current) return
    g.current.sensitive.clearLayers()
    g.current.change.clearLayers()

    // 1. Sensitive zones layer
    if (data?.gis?.sensitive_geojson) {
      try {
        L.geoJSON(data.gis.sensitive_geojson as any, {
          style: {
            color: '#22d3ee',
            weight: 2,
            dashArray: '6 4',
            fillColor: '#22d3ee',
            fillOpacity: 0.18,
          },
        })
          .bindPopup('<b>Sensitive Zone Context Layer</b><br>Authoritative planning & buffer zone.')
          .addTo(g.current.sensitive)
      } catch (e) {
        console.warn('Could not parse sensitive geojson', e)
      }
    }

    // 2. Change regions layer
    if (data?.detection) {
      const regions = data.detection.change_regions
      if (regions && regions.length > 0) {
        regions.forEach(reg => {
          if (reg.geometry) {
            try {
              L.geoJSON(reg.geometry as any, {
                style: {
                  color: '#dc2626',
                  weight: 3.5,
                  dashArray: '6 3',
                  fillColor: '#ea580c',
                  fillOpacity: 0.55,
                },
              })
                .bindPopup(
                  `<b>Potential ${reg.change_type || data?.detection?.class || 'Change'}</b><br>` +
                  `Area: ${reg.area_m2 ? Math.round(reg.area_m2).toLocaleString() + ' m²' : 'Identified'} · ` +
                  `Confidence: ${Math.round((reg.confidence || data?.detection?.confidence || 0.9) * 100)}%`
                )
                .addTo(g.current!.change)
            } catch (err) {
              console.warn('Could not parse region geometry', err)
            }
          }
        })
      } else if (data.detection.polygon) {
        try {
          L.geoJSON(data.detection.polygon as any, {
            style: {
              color: '#dc2626',
              weight: 3.5,
              dashArray: '6 3',
              fillColor: '#ea580c',
              fillOpacity: 0.55,
            },
          })
            .bindPopup(
              `<b>Potential ${data.detection.class}</b><br>` +
              `Area: ${data.detection.area_m2.toLocaleString()} m² · ` +
              `Confidence: ${Math.round(data.detection.confidence * 100)}%`
            )
            .addTo(g.current.change)
        } catch (err) {
          console.warn('Could not parse detection polygon', err)
        }
      }
    }

    // Ensure layers are attached to map
    if (layers.change && !map.current.hasLayer(g.current.change)) {
      map.current.addLayer(g.current.change)
    }
    if (layers.sensitive && !map.current.hasLayer(g.current.sensitive)) {
      map.current.addLayer(g.current.sensitive)
    }

    // Fit map bounds
    if (data?.bbox) {
      map.current.fitBounds(
        [[data.bbox[1], data.bbox[0]], [data.bbox[3], data.bbox[2]]],
        { maxZoom: 17, padding: [20, 20] }
      )
    }
  }, [data])

  // Base map & overlays
  useEffect(() => {
    if (!tiles.current || !map.current) return
    const u = base === 'street' ? OSM : SAT
    tiles.current.a.setUrl(u)
    tiles.current.b.setUrl(u)

    if (base === 'hybrid') {
      map.current.addLayer(labels.current!)
    } else {
      map.current.removeLayer(labels.current!)
    }
  }, [data, base])

  // Layer toggle visibility
  useEffect(() => {
    if (!map.current || !g.current) return
    ;(Object.keys(layers) as (keyof Layers)[]).forEach(k => {
      if (layers[k]) {
        map.current!.addLayer(g.current![k])
      } else {
        map.current!.removeLayer(g.current![k])
      }
    })
  }, [layers])

  // Drawn AOI box
  useEffect(() => {
    if (!g.current) return
    g.current.bbox.clearLayers()
    if (bbox) {
      L.rectangle([[bbox[1], bbox[0]], [bbox[3], bbox[2]]], {
        color: '#22a7f0',
        weight: 2,
        dashArray: '6 4',
        fillOpacity: 0.08,
      }).addTo(g.current.bbox)
    }
  }, [bbox])

  const drag = (e: React.PointerEvent<HTMLDivElement>) => {
    if (e.buttons !== 1) return
    const r = el.current!.getBoundingClientRect()
    setSplit(Math.min(0.97, Math.max(0.03, (e.clientX - r.left) / r.width)))
  }

  return (
    <div className="relative h-full w-full">
      <div
        ref={el}
        className="h-full w-full"
        style={{ cursor: drawing ? 'crosshair' : undefined }}
      />
      <div
        className="absolute inset-y-0 z-[1000] w-0.5 bg-sky-400"
        style={{ left: `${split * 100}%` }}
      >
        <div
          role="slider"
          aria-label="Compare T1 Historical and T2 Current"
          aria-valuenow={Math.round(split * 100)}
          tabIndex={0}
          onPointerDown={e => e.currentTarget.setPointerCapture(e.pointerId)}
          onPointerMove={drag}
          onKeyDown={e => {
            if (e.key === 'ArrowLeft') setSplit(s => Math.max(0.03, s - 0.03))
            if (e.key === 'ArrowRight') setSplit(s => Math.min(0.97, s + 0.03))
          }}
          className="absolute left-1/2 top-1/2 flex h-9 w-9 -translate-x-1/2 -translate-y-1/2 cursor-ew-resize touch-none items-center justify-center rounded-full border-2 border-sky-400 bg-slate-900 text-sky-300 shadow-lg"
        >
          ‹›
        </div>
        <span className="glass mono absolute right-2 top-16 whitespace-nowrap px-2 py-0.5 text-xs text-slate-200">
          T1 Historical
        </span>
        <span className="glass mono absolute left-2 top-16 whitespace-nowrap px-2 py-0.5 text-xs text-sky-300">
          T2 Current
        </span>
      </div>
    </div>
  )
})
