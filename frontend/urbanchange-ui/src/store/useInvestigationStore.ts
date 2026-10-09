import { create } from 'zustand'
import { api, type UploadOptions } from '../api/client'
import type { Base, Layers } from '../components/MapView'
import type { BBox, DetectRequest, Investigation } from '../types'

const LOCAL_STORAGE_KEY = 'urbanchange_investigations_history'
const THEME_KEY = 'urbanchange_theme'

function loadHistory(): Investigation[] {
  try {
    const raw = localStorage.getItem(LOCAL_STORAGE_KEY)
    return raw ? JSON.parse(raw) : []
  } catch {
    return []
  }
}

function saveHistory(history: Investigation[]) {
  try {
    localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(history.slice(0, 30)))
  } catch {
    // quota exceeded or private mode
  }
}

function loadInitialTheme(): 'dark' | 'light' {
  try {
    const stored = localStorage.getItem(THEME_KEY)
    if (stored === 'light' || stored === 'dark') return stored
  } catch {
    // fallback
  }
  return 'dark'
}

interface State {
  // Active Investigation
  activeInvestigation: Investigation | null
  phase: 'idle' | 'loading' | 'done' | 'error'
  step: number
  error: string | null

  // Map & Controls
  bbox: BBox | null
  drawing: boolean
  histDate: string
  curDate: string
  cloudCover: number
  scenario: string
  baseMap: Base
  layers: Layers

  // Application Shell
  theme: 'dark' | 'light'
  isNavCollapsed: boolean
  isMockML: boolean
  history: Investigation[]

  // Actions
  setBbox: (b: BBox | null) => void
  setDrawing: (v: boolean) => void
  setHistDate: (d: string) => void
  setCurDate: (d: string) => void
  setCloudCover: (c: number) => void
  setScenario: (s: string) => void
  setBaseMap: (b: Base) => void
  setLayers: (l: Partial<Layers>) => void
  toggleNav: () => void
  setTheme: (t: 'dark' | 'light') => void
  toggleTheme: () => void
  resetActive: () => void
  loadInvestigation: (id: string) => void
  deleteHistory: (id: string) => void
  clearHistory: () => void
  executeDetection: () => Promise<Investigation | undefined>
  executeUpload: (before: File, after: File, options?: UploadOptions) => Promise<Investigation | undefined>
  checkSystemStatus: () => Promise<void>
}

const initialDate = new Date().toISOString().slice(0, 10)

export const useInvestigationStore = create<State>((set, get) => ({
  activeInvestigation: null,
  phase: 'idle',
  step: 0,
  error: null,

  bbox: null,
  drawing: false,
  histDate: '2025-01-05',
  curDate: initialDate,
  cloudCover: 20,
  scenario: 'ok',
  baseMap: 'hybrid',
  layers: { sensitive: true, change: true, bbox: true },

  theme: loadInitialTheme(),
  isNavCollapsed: false,
  isMockML: true,
  history: loadHistory(),

  setBbox: b => set({ bbox: b, drawing: false }),
  setDrawing: v => set({ drawing: v }),
  setHistDate: d => set({ histDate: d }),
  setCurDate: d => set({ curDate: d }),
  setCloudCover: c => set({ cloudCover: c }),
  setScenario: s => set({ scenario: s }),
  setBaseMap: b => set({ baseMap: b }),
  setLayers: l => set(state => ({ layers: { ...state.layers, ...l } })),
  toggleNav: () => set(state => ({ isNavCollapsed: !state.isNavCollapsed })),

  setTheme: t => {
    localStorage.setItem(THEME_KEY, t)
    if (t === 'light') {
      document.documentElement.classList.add('light')
    } else {
      document.documentElement.classList.remove('light')
    }
    set({ theme: t })
  },

  toggleTheme: () => {
    const next = get().theme === 'dark' ? 'light' : 'dark'
    get().setTheme(next)
  },

  resetActive: () =>
    set({
      activeInvestigation: null,
      phase: 'idle',
      step: 0,
      error: null,
    }),

  loadInvestigation: id => {
    const found = get().history.find(h => h.id === id)
    if (found) {
      set({
        activeInvestigation: found,
        bbox: found.bbox,
        phase: 'done',
        step: 5,
        error: null,
      })
    }
  },

  deleteHistory: id => {
    const updated = get().history.filter(h => h.id !== id)
    saveHistory(updated)
    set(state => ({
      history: updated,
      activeInvestigation: state.activeInvestigation?.id === id ? null : state.activeInvestigation,
    }))
  },

  clearHistory: () => {
    saveHistory([])
    set({ history: [] })
  },

  executeDetection: async () => {
    const { bbox, histDate, curDate, cloudCover, scenario } = get()
    if (!bbox) return

    set({ phase: 'loading', step: 0, error: null })
    try {
      const req: DetectRequest = {
        bbox,
        historical_date: histDate.slice(0, 7),
        current_date: curDate,
        max_cloud: cloudCover,
        scenario,
      }
      const data = await api.detect(req, step => set({ step }))

      // Update history
      const existingHistory = get().history.filter(h => h.id !== data.id)
      const newHistory = [data, ...existingHistory]
      saveHistory(newHistory)

      set({
        activeInvestigation: data,
        phase: 'done',
        step: 5,
        history: newHistory,
      })
      return data
    } catch (err: any) {
      set({
        phase: 'error',
        step: 0,
        error: err.message || 'Investigation pipeline failed',
      })
    }
  },

  executeUpload: async (before: File, after: File, options?: UploadOptions) => {
    set({ phase: 'loading', step: 0, error: null })
    try {
      const data = await api.upload(before, after, options, step => set({ step }))

      // Update history
      const existingHistory = get().history.filter(h => h.id !== data.id)
      const newHistory = [data, ...existingHistory]
      saveHistory(newHistory)

      set({
        activeInvestigation: data,
        bbox: data.bbox,
        phase: 'done',
        step: 5,
        history: newHistory,
      })
      return data
    } catch (err: any) {
      set({
        phase: 'error',
        step: 0,
        error: err.message || 'Image upload analysis failed',
      })
    }
  },

  checkSystemStatus: async () => {
    try {
      const res = await fetch('/health/ready')
      if (res.ok) {
        const body = await res.json()
        const isMock = body?.modules?.ml?.mode === 'mock' || body?.modules?.ml?.mode === undefined
        set({ isMockML: isMock })
        return
      }
    } catch {
      // default mock
    }
    set({ isMockML: true })
  },
}))
