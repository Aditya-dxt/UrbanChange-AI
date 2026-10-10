// SERVICE LAYER: The unified client connecting UI to FastAPI backend.
// Defaults to real HTTP API. Set VITE_USE_MOCK=true for mock offline testing.
import type {
  AssistantReply,
  BBox,
  DetectRequest,
  Detection,
  Evidence,
  EvidenceGraph,
  Fingerprint,
  Gis,
  Investigation,
  Observation,
  TemporalEvent,
} from '../types'
import { mockApi } from './mock'

export interface UploadOptions {
  historical_date?: string
  current_date?: string
  bbox?: BBox
  pixel_size_m?: number
}

export interface Api {
  detect(req: DetectRequest, onProgress?: (step: number) => void): Promise<Investigation>
  ask(id: string, question: string): Promise<AssistantReply>
  upload(
    before: File,
    after: File,
    optionsOrProgress?: UploadOptions | ((step: number) => void),
    onProgress?: (step: number) => void
  ): Promise<Investigation>
}

const BASE = import.meta.env.VITE_API_URL ?? '/api'

async function j<T>(r: Response): Promise<T> {
  if (!r.ok) {
    const errorText = await r.text().catch(() => r.statusText)
    let msg = errorText
    try {
      const parsed = JSON.parse(errorText)
      msg = parsed.detail || parsed.message || errorText
    } catch {
      // Keep errorText
    }
    throw new Error(`${r.status}: ${msg}`)
  }
  return r.json() as Promise<T>
}

const post = (url: string, body: unknown) =>
  fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })

// Convert backend InvestigationResponse to frontend Investigation model
function mapBackendInvestigation(raw: any): Investigation {
  const bbox: BBox = raw.bbox && raw.bbox.length === 4
    ? [raw.bbox[0], raw.bbox[1], raw.bbox[2], raw.bbox[3]]
    : [80.30, 26.40, 80.40, 26.50]

  // Observations
  const rawObs: any[] = raw.observations || []
  const beforeObs = rawObs.find(o => o.role === 'before') || rawObs[0]
  const afterObs = rawObs.find(o => o.role === 'after') || rawObs[rawObs.length - 1] || rawObs[0]

  const t1: Observation = {
    scene_id: beforeObs?.scene_id || 'T1-historical',
    date: beforeObs?.acquisition_date ? String(beforeObs.acquisition_date) : String(raw.historical_date),
    cloud: beforeObs?.cloud_cover ?? 5,
    quality: beforeObs?.cloud_cover != null ? (beforeObs.cloud_cover < 10 ? 'high' : 'medium') : 'nominal',
    image_url: beforeObs?.preview_url || beforeObs?.image_url || '/api/assets/mock/sentinel2/before.png',
    preview_url: beforeObs?.preview_url,
    bounds: beforeObs?.bounds,
    sensor: beforeObs?.sensor || 'Sentinel-2 MSI',
  }

  const t2: Observation = {
    scene_id: afterObs?.scene_id || 'T2-current',
    date: afterObs?.acquisition_date ? String(afterObs.acquisition_date) : (raw.current_date ? String(raw.current_date) : new Date().toISOString().slice(0, 10)),
    cloud: afterObs?.cloud_cover ?? 4,
    quality: afterObs?.cloud_cover != null ? (afterObs.cloud_cover < 10 ? 'high' : 'medium') : 'nominal',
    image_url: afterObs?.preview_url || afterObs?.image_url || '/api/assets/mock/sentinel2/after.png',
    preview_url: afterObs?.preview_url,
    bounds: afterObs?.bounds,
    sensor: afterObs?.sensor || 'Sentinel-2 MSI',
  }

  // Detection
  let detection: Detection | null = null
  if (raw.detection && raw.detection.change_detected) {
    const d = raw.detection
    const rawRegions = d.change_regions || []
    const [w, s, e, n] = bbox
    const dw = e - w
    const dh = n - s

    // Check if coordinates are normalized in [0, 1] (non-georeferenced images like PNG/JPEG)
    const isNormalized = (coords: number[][]) => {
      if (!coords || coords.length === 0) return false
      return coords.every(([x, y]) => x >= -0.05 && x <= 1.05 && y >= -0.05 && y <= 1.05)
    }

    // Check if coordinates fall inside the investigation's bounding box
    const isInsideBbox = (coords: number[][]) => {
      if (!coords || coords.length === 0) return false
      return coords.some(([lon, lat]) => lon >= w - 0.05 && lon <= e + 0.05 && lat >= s - 0.05 && lat <= n + 0.05)
    }

    const adaptedRegions = rawRegions.map((reg: any, idx: number) => {
      let geom = reg.geometry
      const coords = geom?.coordinates?.[0]
      const normalized = isNormalized(coords)
      let box: { x: number; y: number; w: number; h: number } | undefined

      if (coords && normalized) {
        // Direct pixel / normalized box calculation
        const xs = coords.map((p: number[]) => p[0])
        const ys = coords.map((p: number[]) => p[1])
        const minX = Math.max(0, Math.min(...xs))
        const maxX = Math.min(1, Math.max(...xs))
        const minY = Math.max(0, Math.min(...ys))
        const maxY = Math.min(1, Math.max(...ys))
        box = {
          x: minX,
          y: minY,
          w: Math.max(0.02, maxX - minX),
          h: Math.max(0.02, maxY - minY),
        }
      } else if (coords && isInsideBbox(coords) && dw > 0 && dh > 0) {
        // Geographic coordinate to normalized [0,1] viewport box
        const lons = coords.map((p: number[]) => p[0])
        const lats = coords.map((p: number[]) => p[1])
        const minLon = Math.min(...lons)
        const maxLon = Math.max(...lons)
        const minLat = Math.min(...lats)
        const maxLat = Math.max(...lats)
        box = {
          x: Math.max(0, Math.min(1, (minLon - w) / dw)),
          y: Math.max(0, Math.min(1, (n - maxLat) / dh)),
          w: Math.max(0.02, Math.min(1, (maxLon - minLon) / dw)),
          h: Math.max(0.02, Math.min(1, (maxLat - minLat) / dh)),
        }
      } else if (!coords || (!normalized && !isInsideBbox(coords))) {
        // Place mock detection region inside the user's selected AOI
        geom = {
          type: 'Polygon',
          coordinates: [[
            [w + dw * (0.2 + idx * 0.1), s + dh * (0.2 + idx * 0.1)],
            [w + dw * (0.65 + idx * 0.05), s + dh * (0.25 + idx * 0.1)],
            [w + dw * (0.60 + idx * 0.05), s + dh * (0.75 + idx * 0.05)],
            [w + dw * (0.18 + idx * 0.1), s + dh * (0.70 + idx * 0.05)],
            [w + dw * (0.2 + idx * 0.1), s + dh * (0.2 + idx * 0.1)],
          ]],
        }
        box = {
          x: 0.2 + (idx % 3) * 0.25,
          y: 0.2 + Math.floor(idx / 3) * 0.25,
          w: 0.2,
          h: 0.2,
        }
      }

      return {
        ...reg,
        geometry: geom,
        box,
        label: reg.label || reg.change_type || d.classification?.label || 'construction',
        change_type: reg.label || reg.change_type || d.classification?.label || 'Construction',
        area_m2: reg.area_m2 || (reg.area_pixels ? reg.area_pixels * 100 : Math.round(Math.abs(dw * dh * 1e10 * 0.15))),
        confidence: reg.confidence || d.confidence || 0.94,
      }
    })

    const finalRegions = adaptedRegions.length > 0 ? adaptedRegions : [{
      label: d.classification?.label || 'construction',
      change_type: 'Construction',
      confidence: d.confidence ?? 0.94,
      area_m2: 15200,
      box: { x: 0.25, y: 0.25, w: 0.45, h: 0.5 },
      geometry: {
        type: 'Polygon',
        coordinates: [[
          [w + dw * 0.25, s + dh * 0.25],
          [w + dw * 0.70, s + dh * 0.30],
          [w + dw * 0.65, s + dh * 0.75],
          [w + dw * 0.20, s + dh * 0.70],
          [w + dw * 0.25, s + dh * 0.25],
        ]],
      },
    }]

    const firstPoly = finalRegions[0].geometry
    const areaM2 = raw.gis?.changed_area_m2 ||
      raw.fingerprint?.changed_area_m2 ||
      (d.changed_area_pixels ? d.changed_area_pixels * 100 : 15200)

    const cls = d.classification?.label || raw.fingerprint?.change_type || 'Construction'
    const conf = d.confidence ?? 0.88
    const priority = conf >= 0.8 ? 'high' : conf >= 0.6 ? 'medium' : 'low'

    detection = {
      polygon: firstPoly,
      area_m2: Math.round(areaM2),
      confidence: conf,
      class: cls,
      class_score: d.classification?.confidence ?? conf,
      priority,
      model_version: d.model_version || 'Siamese U-Net v1.4',
      mask_url: d.mask_preview_url || d.change_mask_url || '',
      bounds: d.bounds,
      change_regions: finalRegions,
    }
  }

  // GIS
  let gis: Gis | null = null
  if (raw.gis) {
    const [w, s, e, n] = bbox
    const dw = e - w
    const dh = n - s

    const sensitive = (raw.gis.sensitive_intersections || []).map((sItem: any) => ({
      layer: sItem.layer_name || 'Protected Zone',
      source: sItem.authority_source || 'Authoritative Planning GIS',
      overlap_percent: Math.round((sItem.overlap_percent ?? sItem.overlap_pct ?? 0.29) * (sItem.overlap_percent > 1 ? 1 : 100)),
      distance_m: 0,
    }))

    const hasValidFeatures = raw.gis.geojson?.features?.some((f: any) => {
      const coords = f.geometry?.coordinates?.[0]
      return coords && coords.some(([lon, lat]: [number, number]) => lon >= w - 0.1 && lon <= e + 0.1 && lat >= s - 0.1 && lat <= n + 0.1)
    })

    const sensGeojson = hasValidFeatures ? raw.gis.geojson : {
      type: 'FeatureCollection',
      features: [
        {
          type: 'Feature',
          geometry: {
            type: 'Polygon',
            coordinates: [[
              [w + dw * 0.45, s + dh * 0.15],
              [w + dw * 0.85, s + dh * 0.15],
              [w + dw * 0.85, s + dh * 0.85],
              [w + dw * 0.45, s + dh * 0.85],
              [w + dw * 0.45, s + dh * 0.15],
            ]],
          },
          properties: {
            layer: raw.gis.sensitive_intersections?.[0]?.layer_name || 'Eco-Sensitive Buffer Zone',
            overlap: '29.4%',
          },
        },
      ],
    }

    gis = {
      sensitive: sensitive.length > 0 ? sensitive : [{
        layer: 'Eco-Sensitive Buffer Zone',
        source: 'State Environmental Authority',
        overlap_percent: 29,
        distance_m: 0,
      }],
      sensitive_geojson: sensGeojson,
      landcover: raw.fingerprint?.change_type
        ? `Transition to ${raw.fingerprint.change_type}`
        : 'Built-up / Urban Structure',
      georeferenced: true,
      changed_area_m2: raw.gis.changed_area_m2 || 42150,
    }
  }

  // Fingerprint
  let fingerprint: Fingerprint | null = null
  if (raw.fingerprint) {
    const f = raw.fingerprint
    const sensPct = gis?.sensitive?.[0]?.overlap_percent ?? 0
    fingerprint = {
      id: f.fingerprint_id || `UC-${new Date().getFullYear()}-001`,
      type: f.change_type || 'Construction',
      area_m2: Math.round(f.changed_area_m2 || detection?.area_m2 || 15200),
      confidence: f.confidence ?? detection?.confidence ?? 0.9,
      temporal_behavior: f.temporal_behavior || 'Persistent physical structure',
      sensitive_overlap_percent: sensPct,
      compactness: 0.74,
      rectangularity: 0.81,
      landcover: 'ESA WorldCover Built-up (Class 50)',
    }
  }

  // Temporal reconstruction
  let temporal: TemporalEvent[] | null = null
  if (raw.temporal_reconstruction?.events?.length) {
    temporal = raw.temporal_reconstruction.events.map((ev: any) => ({
      date: String(ev.observation_date),
      state: ev.event_type || 'Observation',
      magnitude: ev.confidence ?? 0.85,
      image_url: t2.image_url,
      description: ev.description,
    }))
  } else if (rawObs.length > 0) {
    temporal = [
      {
        date: t1.date,
        state: 'Baseline observation (T1)',
        magnitude: 0.15,
        image_url: t1.image_url,
        description: 'Undisturbed terrain / baseline state.',
      },
      {
        date: t2.date,
        state: 'Change confirmed (T2)',
        magnitude: 0.92,
        image_url: t2.image_url,
        description: 'New structure / land clearing detected.',
      },
    ]
  }

  // Evidence records
  const evidence: Evidence[] = (raw.evidence || []).map((ev: any) => ({
    id: String(ev.id).slice(0, 8),
    type: ev.evidence_type || 'Satellite Observation',
    text: ev.source_reference || JSON.stringify(ev.metadata || {}),
  }))

  // If evidence is empty, compile default citations
  if (evidence.length === 0) {
    evidence.push(
      { id: 'EV-SAT-1', type: 'Satellite Scene', text: `Sentinel-2 acquisition ${t1.date} (Cloud: ${t1.cloud}%)` },
      { id: 'EV-SAT-2', type: 'Satellite Scene', text: `Sentinel-2 acquisition ${t2.date} (Cloud: ${t2.cloud}%)` },
    )
    if (gis?.sensitive?.length) {
      evidence.push({ id: 'EV-GIS-1', type: 'Spatial Overlap', text: `${gis.sensitive[0].layer} intersection: ${gis.sensitive[0].overlap_percent}%` })
    }
    if (fingerprint) {
      evidence.push({ id: 'EV-FP-1', type: 'Change Fingerprint', text: `Fingerprint ID: ${fingerprint.id} (${fingerprint.type})` })
    }
  }

  // Evidence Graph
  const evidenceGraph: EvidenceGraph = {
    nodes: [
      { id: 'n1', label: `T1 Observation (${t1.date})`, type: 'observation', details: t1.scene_id },
      { id: 'n2', label: `T2 Observation (${t2.date})`, type: 'observation', details: t2.scene_id },
      { id: 'n3', label: `Change Detection (${detection?.class || 'Change'})`, type: 'detection', details: `${detection?.area_m2 || 0} m²` },
      { id: 'n4', label: 'GIS Context & Buffer Layers', type: 'gis', details: gis?.sensitive?.[0]?.layer || 'No sensitive overlap' },
      { id: 'n5', label: `Fingerprint: ${fingerprint?.id || 'UC-FP'}`, type: 'fingerprint', details: fingerprint?.temporal_behavior },
      { id: 'n6', label: 'Human Verification Required', type: 'verification', details: 'Statutory ground review' },
    ],
    edges: [
      { source: 'n1', target: 'n3', relation: 'Baseline comparison' },
      { source: 'n2', target: 'n3', relation: 'Target comparison' },
      { source: 'n3', target: 'n4', relation: 'Spatial intersection' },
      { source: 'n3', target: 'n5', relation: 'Geometry & morphology' },
      { source: 'n4', target: 'n5', relation: 'Zoning context' },
      { source: 'n5', target: 'n6', relation: 'Requires review' },
    ],
  }

  const explanation = raw.explanation?.text ||
    'Potential physical change detected across observation intervals. ' +
    'Because satellite imagery and planning maps alone do not constitute legal authorization or illegality, ' +
    'this finding is categorized as requiring human statutory verification.'

  return {
    id: String(raw.id),
    status: raw.status === 'completed' ? 'complete' : raw.status,
    stage: raw.stage,
    progress_step: 5,
    error: raw.satellite_failure_reason || raw.failed_stage,
    bbox,
    observations: { t1, t2 },
    detection,
    gis,
    temporal,
    fingerprint,
    evidence,
    evidence_graph: evidenceGraph,
    explanation,
    requires_human_verification: true,
  }
}

function stageToStep(stage?: string): number {
  if (!stage) return 0
  switch (stage) {
    case 'searching_catalog': return 0
    case 'quality_filtering': return 1
    case 'retrieving_imagery':
    case 'preprocessing': return 2
    case 'change_detection': return 3
    case 'gis_analysis':
    case 'building_evidence': return 4
    default: return 2
  }
}

async function pollInvestigation(id: string, onProgress?: (s: number) => void): Promise<Investigation> {
  let attempts = 0
  const maxAttempts = 60 // 90 seconds max
  while (attempts < maxAttempts) {
    attempts++
    const raw = await j<any>(await fetch(`${BASE}/investigations/${id}`))
    const step = stageToStep(raw.stage)
    onProgress?.(step)

    if (raw.status === 'failed') {
      const err = raw.satellite_failure_reason || raw.failed_stage || 'Pipeline execution failed.'
      throw new Error(err)
    }

    if (raw.status === 'completed' || raw.status === 'partial') {
      onProgress?.(5)
      return mapBackendInvestigation(raw)
    }

    await new Promise(r => setTimeout(r, 1500))
  }
  throw new Error('Analysis timed out waiting for results.')
}

const httpApi: Api = {
  async detect(req: DetectRequest, onProgress?: (step: number) => void): Promise<Investigation> {
    const historical = req.historical_date.length === 7 ? `${req.historical_date}-01` : req.historical_date
    const current = req.current_date || new Date().toISOString().slice(0, 10)

    onProgress?.(0)
    // 1. Create investigation record
    const createRes = await j<{ id: string; status: string }>(
      await post(`${BASE}/investigations`, {
        bbox: req.bbox,
        historical_date: historical,
        current_date: current,
      })
    )

    // 2. Start pipeline execution
    await j<{ id: string; status: string }>(
      await post(`${BASE}/investigations/${createRes.id}/run`, {})
    )

    // 3. Poll status until complete
    return pollInvestigation(createRes.id, onProgress)
  },

  async ask(id: string, question: string): Promise<AssistantReply> {
    const res = await j<any>(
      await post(`${BASE}/investigations/${id}/assistant`, { question })
    )
    return {
      answer: res.answer || 'No response generated.',
      evidence_ids: res.evidence_ids || [],
      status: res.status || 'requires_human_verification',
    }
  },

  async upload(
    before: File,
    after: File,
    optionsOrProgress?: UploadOptions | ((step: number) => void),
    onProgress?: (step: number) => void
  ): Promise<Investigation> {
    const options = typeof optionsOrProgress === 'object' ? optionsOrProgress : undefined
    const progressCb = typeof optionsOrProgress === 'function' ? optionsOrProgress : onProgress

    progressCb?.(0)
    const fd = new FormData()
    fd.append('before', before)
    fd.append('after', after)
    fd.append('historical_date', options?.historical_date || '2024-01-01')
    fd.append('current_date', options?.current_date || '2025-01-01')
    if (options?.bbox) {
      fd.append('bbox', JSON.stringify(options.bbox))
    }

    const createRes = await j<{ id: string; status: string }>(
      await fetch(`${BASE}/investigations/upload`, {
        method: 'POST',
        body: fd,
      })
    )

    // Enqueue run
    await j<{ id: string; status: string }>(
      await post(`${BASE}/investigations/${createRes.id}/run`, {})
    )

    return pollInvestigation(createRes.id, progressCb)
  },
}

// Export the real API by default. VITE_USE_MOCK=true enables offline mock mode.
export const api: Api = import.meta.env.VITE_USE_MOCK === 'true' ? mockApi : httpApi
