import type { Api } from './client'
import type { BBox, Investigation } from '../types'

const wait = (ms: number) => new Promise(r => setTimeout(r, ms))
const svg = (lvl: number, mask = false) => {
  let s = '<rect width="260" height="180" fill="#6f9a5a"/><path d="M0 120H260M90 0V180" stroke="#d6d3c4" stroke-width="6"/>'
  for (let i = 0; i < Math.round(lvl * 8); i++) s += `<rect x="${100 + (i % 4) * 30}" y="${20 + Math.floor(i / 4) * 34}" width="24" height="26" fill="#8b8b8b"/>`
  if (mask) s = '<rect x="96" y="16" width="124" height="74" fill="#ef4444" fill-opacity=".5"/>'
  return 'data:image/svg+xml;utf8,' + encodeURIComponent(`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 260 180">${s}</svg>`)
}
function build(bbox: BBox, scenario = 'ok', georef = true): Investigation {
  const [w, s, e, n] = bbox, cx = (w + e) / 2, cy = (s + n) / 2, dx = (e - w) * 0.18, dy = (n - s) * 0.18
  const ring = [[cx - dx, cy - dy], [cx + dx, cy - dy], [cx + dx, cy + dy], [cx - dx, cy + dy], [cx - dx, cy - dy]]
  const low = scenario === 'low', empty = scenario === 'empty'
  const zone: GeoJSON.Polygon = { type: 'Polygon', coordinates: [[[w, s], [cx, s], [cx, n], [w, n], [w, s]]] }
  const tl: [string, string, number][] = [['2025-01', 'Low built-up signal', 0.05], ['2025-04', 'Ground disturbance', 0.25], ['2025-07', 'Early structural footprint', 0.5], ['2025-10', 'Expanded built-up region', 0.75], ['2026-09', 'Larger persistent structure', 1]]
  return {
    id: 'inv-001', status: scenario === 'partial' ? 'partial' : 'complete', bbox,
    observations: {
      t1: { scene_id: 'S2B_20250112', date: '2025-01-12', cloud: 4, quality: 'good', image_url: svg(0) },
      t2: { scene_id: 'S2A_20260928', date: '2026-09-28', cloud: 7, quality: 'good', image_url: svg(empty ? 0 : 1) },
    },
    detection: empty ? null : { polygon: { type: 'Polygon', coordinates: [ring] }, area_m2: 3842, confidence: low ? 0.48 : 0.94, class: 'construction', class_score: low ? 0.41 : 0.88, priority: low ? 'low' : 'high', model_version: 'siamese-unet-0.3', mask_url: svg(1, true) },
    gis: { sensitive: [{ layer: 'Drainage corridor (sample layer)', source: 'Demo GIS v1', overlap_percent: 64, distance_m: 0 }], sensitive_geojson: { type: 'FeatureCollection', features: [{ type: 'Feature', properties: { name: 'Sample sensitive layer' }, geometry: zone }] }, landcover: 'Built-up / bare ground', georeferenced: georef },
    temporal: scenario === 'partial' || empty ? null : tl.map(([date, state, magnitude]) => ({ date, state, magnitude, image_url: svg(magnitude) })),
    fingerprint: empty ? null : { id: 'UC-2026-A91F', type: 'construction', area_m2: 3842, confidence: low ? 0.48 : 0.94, temporal_behavior: 'progressive', sensitive_overlap_percent: 64, compactness: 0.71, rectangularity: 0.83, landcover: 'Built-up' },
    evidence: empty ? [] : [
      { id: 'E1', type: 'observation', text: 'T1 2025-01-12, T2 2026-09-28; cloud 4% / 7%.' },
      { id: 'E2', type: 'detection', text: 'Change polygon about 3,842 m2.' },
      { id: 'E3', type: 'classification', text: 'Construction scored highest.' },
      { id: 'E4', type: 'gis', text: 'About 64% overlap with a configured sample layer.' }],
    explanation: 'Potential construction activity detected between the selected observations. The change overlaps a configured sensitive layer. Imagery and GIS layers do not establish legal authorization, so this requires human verification.',
  }
}
export const mockApi: Api = {
  async detect(req, onProgress) {
    for (let i = 0; i < 5; i++) { onProgress?.(i); await wait(350) }
    if (req.scenario === 'fail') throw new Error('503 satellite catalog unavailable')
    return build(req.bbox, req.scenario)
  },
  async upload(_b, _a, onProgress) {
    for (let i = 0; i < 5; i++) { onProgress?.(i); await wait(250) }
    return build([80.34, 26.43, 80.35, 26.44], 'ok', false)
  },
  async ask(_id, q) {
    await wait(400); q = q.toLowerCase()
    if (/when|start/.test(q)) return { answer: 'First persistent change appears between the Jan and Apr 2025 observations. This is an inference, not an exact date.', evidence_ids: ['E1'] }
    if (/large|area|size/.test(q)) return { answer: 'About 3,842 m2.', evidence_ids: ['E2'] }
    if (/why|flag/.test(q)) return { answer: 'Flagged as potential construction overlapping a configured sensitive layer. Requires human verification; not a legal determination.', evidence_ids: ['E2', 'E3', 'E4'] }
    return { answer: 'I can only answer from computed evidence: what changed, when, how large, why flagged.', evidence_ids: [] }
  },
}
