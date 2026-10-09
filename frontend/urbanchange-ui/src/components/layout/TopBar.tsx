import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Activity,
  AlertTriangle,
  CheckCircle,
  Clock,
  Menu,
  Moon,
  Plus,
  Settings as SettingsIcon,
  Sun,
} from 'lucide-react'
import { Badge } from '../common/Badge'
import { Modal } from '../common/Modal'
import { useInvestigationStore } from '../../store/useInvestigationStore'

export function TopBar() {
  const navigate = useNavigate()
  const {
    activeInvestigation,
    phase,
    theme,
    toggleTheme,
    toggleNav,
    resetActive,
    isMockML,
    checkSystemStatus,
    scenario,
    setScenario,
  } = useInvestigationStore()

  const [isSettingsOpen, setIsSettingsOpen] = useState(false)

  useEffect(() => {
    checkSystemStatus()
  }, [checkSystemStatus])

  function handleNew() {
    resetActive()
    navigate('/investigate')
  }

  // Determine investigation status badge
  let statusBadge = (
    <Badge variant="default" size="sm">
      <Clock className="h-3 w-3" /> Ready
    </Badge>
  )

  if (phase === 'loading') {
    statusBadge = (
      <Badge variant="info" size="sm" className="animate-pulse">
        <Activity className="h-3 w-3 animate-spin" /> Processing Pipeline…
      </Badge>
    )
  } else if (phase === 'error') {
    statusBadge = (
      <Badge variant="danger" size="sm">
        <AlertTriangle className="h-3 w-3" /> Error
      </Badge>
    )
  } else if (activeInvestigation) {
    statusBadge = (
      <Badge variant="warning" size="sm">
        <CheckCircle className="h-3 w-3 text-amber-400" /> Human Verification Required
      </Badge>
    )
  }

  return (
    <>
      <header
        className="sticky top-0 z-[1100] flex h-16 w-full items-center justify-between border-b px-4 transition-colors"
        style={{ borderColor: 'var(--line)', background: 'var(--panel)' }}
      >
        {/* Left: Hamburger & Brand */}
        <div className="flex items-center gap-3">
          <button
            onClick={toggleNav}
            className="btn-ghost p-2 text-slate-300 hover:text-white"
            aria-label="Toggle Navigation Rail"
          >
            <Menu className="h-5 w-5" />
          </button>

          <div
            onClick={() => navigate('/investigate')}
            className="flex cursor-pointer items-center gap-2.5 select-none"
          >
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-sky-400 to-blue-600 shadow-md shadow-sky-500/20">
              <svg width="22" height="22" viewBox="0 0 32 32" aria-hidden>
                <rect x="7" y="7" width="18" height="18" fill="none" stroke="#04121f" strokeWidth="2.5" />
                <rect x="13" y="13" width="7" height="7" fill="#04121f" />
              </svg>
            </div>
            <div>
              <div className="display text-base font-extrabold tracking-tight text-slate-100 flex items-center gap-2">
                URBANCHANGE AI
              </div>
              <div className="label text-[10px] text-slate-400 hidden sm:block">
                Explainable Satellite Intelligence
              </div>
            </div>
          </div>
        </div>

        {/* Center: Current Investigation Status */}
        <div className="hidden md:flex items-center gap-3">
          {activeInvestigation ? (
            <div className="flex items-center gap-2 rounded-lg border border-slate-700/60 bg-slate-900/60 px-3 py-1.5 text-xs">
              <span className="text-slate-400">Active Investigation:</span>
              <span className="font-mono font-bold text-sky-400">
                {activeInvestigation.fingerprint?.id || activeInvestigation.id.slice(0, 8)}
              </span>
              {statusBadge}
            </div>
          ) : (
            <div className="flex items-center gap-2 text-xs text-slate-400">
              <span>No Active Target</span>
              {statusBadge}
            </div>
          )}

          {isMockML && (
            <Badge variant="warning" size="sm" className="bg-amber-950/40 text-amber-300">
              Demo / Mock ML Active
            </Badge>
          )}
        </div>

        {/* Right: Actions */}
        <div className="flex items-center gap-2">
          <button
            onClick={handleNew}
            className="btn text-xs font-semibold py-2 px-3 sm:px-4"
            title="Start fresh investigation"
          >
            <Plus className="h-4 w-4" />
            <span className="hidden sm:inline">New Investigation</span>
          </button>

          <button
            onClick={toggleTheme}
            className="btn-ghost p-2 text-slate-300 hover:text-white"
            title={`Switch to ${theme === 'dark' ? 'Light' : 'Dark'} mode`}
            aria-label="Toggle theme"
          >
            {theme === 'dark' ? <Sun className="h-4 w-4 text-amber-400" /> : <Moon className="h-4 w-4 text-sky-400" />}
          </button>

          <button
            onClick={() => setIsSettingsOpen(true)}
            className="btn-ghost p-2 text-slate-300 hover:text-white"
            title="System Settings & Mock Scenarios"
            aria-label="Settings"
          >
            <SettingsIcon className="h-4 w-4" />
          </button>
        </div>
      </header>

      {/* Settings Modal */}
      <Modal
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
        title="Settings & Diagnostics"
      >
        <div className="flex flex-col gap-4 text-sm text-slate-300">
          <div>
            <label className="label mb-1 block">Execution Mode</label>
            <div className="rounded-lg border border-slate-700 bg-slate-900/60 p-3 text-xs leading-relaxed">
              <div className="font-semibold text-slate-200">
                {isMockML ? 'Mock ML Adapter Active' : 'Live ML Microservice Connected'}
              </div>
              <div className="text-slate-400 mt-1">
                Satellite, GIS, and Intelligence engines connect to live microservices when deployed under Docker Compose.
              </div>
            </div>
          </div>

          <div>
            <label className="label mb-1 block">Mock Scenario Preset</label>
            <select
              value={scenario}
              onChange={e => setScenario(e.target.value)}
              className="w-full text-xs"
            >
              <option value="ok">Success (High Confidence Construction)</option>
              <option value="none">No Significant Change</option>
              <option value="low">Low Confidence Detection</option>
              <option value="partial">Partial Coverage / Cloud Caveat</option>
            </select>
          </div>

          <div className="border-t border-slate-800 pt-3 text-xs text-slate-400">
            <div>API Base: <code className="text-sky-400">/api</code></div>
            <div>Statutory Notice: All detections are advisory decision-support findings.</div>
          </div>
        </div>
      </Modal>
    </>
  )
}
