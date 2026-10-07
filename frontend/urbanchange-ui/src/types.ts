// All coordinates are GeoJSON order: [longitude, latitude]. BBox = [west, south, east, north].
export type BBox = [number, number, number, number]
export type Status = 'queued' | 'running' | 'partial' | 'complete' | 'failed'
export interface Observation { scene_id: string; date: string; cloud: number; quality: string; image_url: string; tile_url?: string }
export interface Detection {
  polygon: GeoJSON.Polygon; area_m2: number; confidence: number; class: string; class_score: number
  priority: 'low' | 'medium' | 'high'; model_version: string; mask_url: string
}
export interface SensitiveHit { layer: string; source: string; overlap_percent: number; distance_m: number }
export interface Gis { sensitive: SensitiveHit[]; sensitive_geojson: GeoJSON.FeatureCollection; landcover: string; georeferenced: boolean }
export interface TemporalEvent { date: string; state: string; magnitude: number; image_url: string }
export interface Fingerprint {
  id: string; type: string; area_m2: number; confidence: number; temporal_behavior: string
  sensitive_overlap_percent: number; compactness: number; rectangularity: number; landcover: string
}
export interface Evidence { id: string; type: string; text: string }
export interface Investigation {
  id: string; status: Status; progress_step?: number; error?: string; bbox: BBox
  observations: { t1: Observation; t2: Observation }
  detection: Detection | null            // null => no change found
  gis: Gis | null
  temporal: TemporalEvent[] | null       // null => unavailable (partial result)
  fingerprint: Fingerprint | null
  evidence: Evidence[]
  explanation: string
}
export interface DetectRequest { bbox: BBox; historical_date: string; current_date?: string; max_cloud?: number; scenario?: string }
export interface AssistantReply { answer: string; evidence_ids: string[] }
export const PROGRESS_STEPS = ['Querying satellite catalog', 'Quality filtering scenes', 'Clipping & aligning', 'Running change detection', 'Building GIS context']
