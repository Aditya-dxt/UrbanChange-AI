import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Archive,
  ArrowRight,
  Compass,
  FileText,
  FolderOpen,
  MapPin,
  Search,
  Trash2,
} from 'lucide-react'
import { Card } from '../components/common/Card'
import { EmptyState } from '../components/common/EmptyState'
import { Badge } from '../components/common/Badge'
import { Modal } from '../components/common/Modal'
import { useInvestigationStore } from '../store/useInvestigationStore'

export default function HistoryPage() {
  const navigate = useNavigate()
  const { history, loadInvestigation, deleteHistory, clearHistory } =
    useInvestigationStore()

  const [searchQuery, setSearchQuery] = useState('')
  const [confirmClearOpen, setConfirmClearOpen] = useState(false)

  const filteredHistory = history.filter(item => {
    const q = searchQuery.toLowerCase()
    const idMatch = item.id.toLowerCase().includes(q)
    const classMatch = item.detection?.class.toLowerCase().includes(q) || false
    const dateMatch =
      item.observations.t1.date.includes(q) || item.observations.t2.date.includes(q)
    return idMatch || classMatch || dateMatch
  })

  function handleOpen(id: string) {
    loadInvestigation(id)
    navigate('/results')
  }

  return (
    <div className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8 space-y-6">
      {/* HEADER */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-mono text-sky-400 font-semibold uppercase tracking-wider">
              Investigation Archives
            </span>
            <Badge variant="default" size="sm" className="font-mono">
              {history.length} Saved Records
            </Badge>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-100 tracking-tight">
            Historical Investigations
          </h1>
          <p className="text-xs sm:text-sm text-slate-400 mt-1">
            Audit history of past change detection runs and spatial findings stored in this browser session.
          </p>
        </div>

        {history.length > 0 && (
          <button
            onClick={() => setConfirmClearOpen(true)}
            className="btn-ghost flex items-center gap-1.5 text-xs text-rose-400 hover:text-rose-300 border border-rose-900/50 hover:bg-rose-950/30 self-start sm:self-auto"
          >
            <Trash2 className="h-3.5 w-3.5" /> Clear History
          </button>
        )}
      </div>

      {history.length === 0 ? (
        <EmptyState
          title="No Investigation History Yet"
          description="Investigations you execute from the map or upload section will automatically be logged here for easy review."
          actionLabel="Go to Investigate Map"
          onAction={() => navigate('/investigate')}
          icon={<Archive className="h-8 w-8 text-sky-400" />}
        />
      ) : (
        <>
          {/* SEARCH FILTER */}
          <div className="flex items-center gap-2 rounded-xl border border-slate-700/80 bg-slate-900/80 px-3 py-2 max-w-md shadow-sm">
            <Search className="h-4 w-4 text-slate-400 shrink-0" />
            <input
              type="text"
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              placeholder="Search by ID, class (e.g. construction), or dates…"
              className="w-full bg-transparent text-xs text-slate-100 placeholder-slate-400 focus:outline-none"
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery('')}
                className="text-xs text-slate-400 hover:text-slate-200"
              >
                ×
              </button>
            )}
          </div>

          {/* HISTORY TABLE / CARDS */}
          <div className="space-y-3">
            {filteredHistory.map(item => {
              const d = item.detection
              const pct = d ? Math.round(d.confidence * 100) : 0

              return (
                <div
                  key={item.id}
                  className="rounded-2xl border border-slate-800 bg-slate-900/50 p-4 transition-all hover:border-slate-700 hover:bg-slate-900 flex flex-col md:flex-row md:items-center justify-between gap-4"
                >
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-sm font-bold text-sky-400">
                        #{item.id}
                      </span>
                      <Badge
                        variant={
                          d?.priority === 'high'
                            ? 'danger'
                            : d
                            ? 'warning'
                            : 'default'
                        }
                        size="sm"
                      >
                        {d ? `${d.priority} priority` : 'No change'}
                      </Badge>
                      <span className="text-[11px] text-slate-500 font-mono">
                        {item.created_at ? new Date(item.created_at).toLocaleDateString() : 'Archived'}
                      </span>
                    </div>

                    <div className="text-xs text-slate-300">
                      Observation range:{' '}
                      <b className="text-slate-200">{item.observations.t1.date}</b> →{' '}
                      <b className="text-slate-200">{item.observations.t2.date}</b>
                    </div>

                    <div className="flex flex-wrap items-center gap-3 text-xs text-slate-400 pt-1">
                      {d && (
                        <>
                          <span>
                            Class: <b className="text-slate-200 capitalize">{d.class}</b>
                          </span>
                          <span>·</span>
                          <span>
                            Area: <b className="text-slate-200">{d.area_m2.toLocaleString()} m²</b>
                          </span>
                          <span>·</span>
                          <span>
                            Confidence: <b className="text-slate-200">{pct}%</b>
                          </span>
                        </>
                      )}
                      {item.gis?.sensitive && item.gis.sensitive.length > 0 && (
                        <>
                          <span>·</span>
                          <span className="text-cyan-400">
                            {item.gis.sensitive.length} GIS buffer conflicts
                          </span>
                        </>
                      )}
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="flex items-center gap-2 shrink-0">
                    <button
                      onClick={() => handleOpen(item.id)}
                      className="btn flex items-center gap-1.5 py-2 px-3 text-xs font-semibold"
                    >
                      <FolderOpen className="h-3.5 w-3.5" />
                      <span>Open Report</span>
                    </button>
                    <button
                      onClick={() => deleteHistory(item.id)}
                      className="p-2 text-slate-500 hover:text-rose-400 transition-colors rounded-lg hover:bg-slate-800"
                      title="Delete this record"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              )
            })}
          </div>
        </>
      )}

      {/* CONFIRM CLEAR MODAL */}
      <Modal
        isOpen={confirmClearOpen}
        onClose={() => setConfirmClearOpen(false)}
        title="Clear All History?"
      >
        <div className="space-y-4">
          <p className="text-xs sm:text-sm text-slate-300 leading-relaxed">
            This will remove all saved investigation records from this browser&apos;s local storage. This action cannot be undone.
          </p>
          <div className="flex justify-end gap-2 pt-2">
            <button
              onClick={() => setConfirmClearOpen(false)}
              className="btn-ghost text-xs"
            >
              Cancel
            </button>
            <button
              onClick={() => {
                clearHistory()
                setConfirmClearOpen(false)
              }}
              className="btn text-xs bg-rose-600 hover:bg-rose-500"
            >
              Confirm Clear All
            </button>
          </div>
        </div>
      </Modal>
    </div>
  )
}
