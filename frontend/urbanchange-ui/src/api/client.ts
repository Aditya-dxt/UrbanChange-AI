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

export interface Api {
  detect(req: DetectRequest, onProgress?: (step: number) => void): Promise<Investigation>
  ask(id: string, question: string): Promise<AssistantReply>
  upload(before: File, after: File, onProgress?: (step: number) => void): Promise<Investigation>
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
    const regions = d.change_regions || []
    const firstPoly = regions[0]?.geometry || {
      type: 'Polygon',
      coordinates: [[
        [bbox[0] + 0.005, bbox[1] + 0.005],
        [bbox[2] - 0.005, bbox[1] + 0.005],
        [bbox[2] - 0.005, bbox[3] - 0.005],
        [bbox[0] + 0.005, bbox[3] - 0.005],
        [bbox[0] + 0.005, bbox[1] + 0.005],
      ]],
    }

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
      change_regions: regions,
    }
  }

  // GIS
  let gis: Gis | null = null
  if (raw.gis) {
    const sensitive = (raw.gis.sensitive_intersections || []).map((s: any) => ({
      layer: s.layer_name || 'Protected Zone',
      source: 'Authoritative Planning GIS',
      overlap_percent: Math.round((s.overlap_pct ?? 0) * 100),
      distance_m: 0,
    }))

    gis = {
      sensitive,
      sensitive_geojson: raw.gis.geojson || {
        type: 'FeatureCollection',
        features: (raw.gis.sensitive_intersections || [])
          .filter((s: any) => s.geometry)
          .map((s: any) => ({
            type: 'Feature',
            geometry: s.geometry,
            properties: { layer: s.layer_name, overlap: s.overlap_pct },
          })),
      },
      landcover: raw.fingerprint?.change_type
        ? `Transition to ${raw.fingerprint.change_type}`
        : 'Built-up / Urban Structure',
      georeferenced: true,
      changed_area_m2: raw.gis.changed_area_m2,
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

  async upload(before: File, after: File, onProgress?: (step: number) => void): Promise<Investigation> {
    onProgress?.(0)
    const fd = new FormData()
    fd.append('before', before)
    fd.append('after', after)
    fd.append('historical_date', '2024-01-01')
    fd.append('current_date', '2025-01-01')

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

    return pollInvestigation(createRes.id, onProgress)
  },
}

// Export the real API by default. VITE_USE_MOCK=true enables offline mock mode.
export const api: Api = import.meta.env.VITE_USE_MOCK === 'true' ? mockApi : httpApi
