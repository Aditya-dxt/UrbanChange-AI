import { useCallback, useState } from 'react'
import { api } from '../api/client'
import type { DetectRequest, Investigation } from '../types'

type State = { phase: 'idle' | 'loading' | 'done' | 'error'; step: number; data?: Investigation; error?: string }
export function useInvestigation() {
  const [state, set] = useState<State>({ phase: 'idle', step: 0 })
  const run = useCallback(async (fn: (p: (s: number) => void) => Promise<Investigation>) => {
    set({ phase: 'loading', step: 0 })
    try { const data = await fn(step => set(s => ({ ...s, step }))); set({ phase: 'done', step: 5, data }) }
    catch (e) { set({ phase: 'error', step: 0, error: (e as Error).message }) }
  }, [])
  return {
    state,
    detect: (req: DetectRequest) => run(p => api.detect(req, p)),
    upload: (b: File, a: File) => run(p => api.upload(b, a, p)),
    reset: () => set({ phase: 'idle', step: 0 }),
  }
}
