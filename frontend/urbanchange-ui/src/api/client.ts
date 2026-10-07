// SERVICE LAYER: the only file the UI imports for data. Set VITE_USE_MOCK=false to hit FastAPI.
import type { AssistantReply, DetectRequest, Investigation } from '../types'
import { mockApi } from './mock'

export interface Api {
  detect(req: DetectRequest, onProgress?: (step: number) => void): Promise<Investigation>
  ask(id: string, question: string): Promise<AssistantReply>
  upload(before: File, after: File, onProgress?: (step: number) => void): Promise<Investigation>
}
const BASE = import.meta.env.VITE_API_URL ?? '/api'
async function j<T>(r: Response): Promise<T> {
  if (!r.ok) throw new Error(`${r.status} ${await r.text().catch(() => r.statusText)}`)
  return r.json() as Promise<T>
}
async function poll(id: string, onProgress?: (s: number) => void): Promise<Investigation> {
  for (;;) {
    const inv = await j<Investigation>(await fetch(`${BASE}/investigations/${id}`))
    onProgress?.(inv.progress_step ?? 0)
    if (inv.status === 'failed') throw new Error(inv.error ?? 'Investigation failed')
    if (inv.status === 'complete' || inv.status === 'partial') return inv
    await new Promise(r => setTimeout(r, 1500))
  }
}
const post = (url: string, body: unknown) => fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
const httpApi: Api = {
  async detect(req, onProgress) {
    const { id } = await j<{ id: string }>(await post(`${BASE}/investigations`, req))
    return poll(id, onProgress)
  },
  ask: async (id, question) => j(await post(`${BASE}/investigations/${id}/assistant`, { question })),
  async upload(before, after, onProgress) {
    const fd = new FormData(); fd.append('before', before); fd.append('after', after)
    const { id } = await j<{ id: string }>(await fetch(`${BASE}/uploads`, { method: 'POST', body: fd }))
    return poll(id, onProgress)
  },
}
export const api: Api = import.meta.env.VITE_USE_MOCK === 'false' ? httpApi : mockApi
