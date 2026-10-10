// All coordinates are GeoJSON order: [longitude, latitude]. BBox = [west, south, east, north].
export type BBox = [number, number, number, number]
export type Status = 'queued' | 'running' | 'partial' | 'complete' | 'failed'

export interface Observation {
  scene_id: string
  date: string
  cloud: number
  quality: string
  image_url: string
  preview_url?: string
  tile_url?: string
  bounds?: BBox
  sensor?: string
}

export interface Detection {
  polygon: GeoJSON.Polygon | GeoJSON.MultiPolygon | GeoJSON.Geometry
  area_m2: number
  confidence: number
  class: string
  class_score: number
  priority: 'low' | 'medium' | 'high'
  model_version: string
  mask_url: string
  bounds?: BBox
  change_regions?: Array<{
    geometry: GeoJSON.Polygon | GeoJSON.Geometry
    area_m2?: number
    change_type?: string
    confidence?: number
    label?: string
    box?: { x: number; y: number; w: number; h: number }
  }>
}

export interface SensitiveHit {
  layer: string
  source: string
  overlap_percent: number
  distance_m: number
}

export interface Gis {
  sensitive: SensitiveHit[]
  sensitive_geojson: GeoJSON.FeatureCollection | GeoJSON.Geometry
  landcover: string
  georeferenced: boolean
  changed_area_m2?: number
}

export interface TemporalEvent {
  date: string
  state: string
  magnitude: number
  image_url: string
  description?: string
}

export interface Fingerprint {
  id: string
  type: string
  area_m2: number
  confidence: number
  temporal_behavior: string
  sensitive_overlap_percent: number
  compactness: number
  rectangularity: number
  landcover: string
}

export interface Evidence {
  id: string
  type: string
  text: string
}

export interface EvidenceGraphNode {
  id: string
  label: string
  type: 'observation' | 'detection' | 'gis' | 'fingerprint' | 'verification'
  details?: string
}

export interface EvidenceGraphEdge {
  source: string
  target: string
  relation: string
}

export interface EvidenceGraph {
  nodes: EvidenceGraphNode[]
  edges: EvidenceGraphEdge[]
}

export interface Investigation {
  id: string
  status: Status
  stage?: string
  progress_step?: number
  error?: string
  bbox: BBox
  observations: { t1: Observation; t2: Observation }
  detection: Detection | null            // null => no change found
  gis: Gis | null
  temporal: TemporalEvent[] | null       // null => unavailable (partial result)
  fingerprint: Fingerprint | null
  evidence: Evidence[]
  evidence_graph?: EvidenceGraph | null
  explanation: string
  requires_human_verification?: boolean
  created_at?: string
}

export interface DetectRequest {
  bbox: BBox
  historical_date: string
  current_date?: string
  max_cloud?: number
  scenario?: string
}

export interface AssistantReply {
  answer: string
  evidence_ids: string[]
  status?: string
}

export const PROGRESS_STEPS = [
  'Querying satellite catalog',
  'Quality filtering scenes',
  'Clipping & aligning raster grid',
  'Running AI change detection',
  'Building GIS context & evidence graph',
]
