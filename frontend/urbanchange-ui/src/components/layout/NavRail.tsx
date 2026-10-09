import { NavLink } from 'react-router-dom'
import {
  Archive,
  Bot,
  Calendar,
  Compass,
  FileCheck2,
  Fingerprint,
  Network,
  ShieldAlert,
  UploadCloud,
} from 'lucide-react'
import { useInvestigationStore } from '../../store/useInvestigationStore'

interface NavItem {
  to: string
  label: string
  icon: React.ReactNode
  requiresData?: boolean
}

const NAV_ITEMS: NavItem[] = [
  { to: '/investigate', label: 'Investigate', icon: <Compass className="h-5 w-5" /> },
  { to: '/results', label: 'Results', icon: <FileCheck2 className="h-5 w-5" />, requiresData: true },
  { to: '/fingerprint', label: 'Fingerprint', icon: <Fingerprint className="h-5 w-5" />, requiresData: true },
  { to: '/sensitive-zones', label: 'Sensitive Zones', icon: <ShieldAlert className="h-5 w-5" />, requiresData: true },
  { to: '/timeline', label: 'Timeline', icon: <Calendar className="h-5 w-5" />, requiresData: true },
  { to: '/evidence-graph', label: 'Evidence Graph', icon: <Network className="h-5 w-5" />, requiresData: true },
  { to: '/assistant', label: 'Assistant', icon: <Bot className="h-5 w-5" /> },
  { to: '/upload', label: 'Upload Mode', icon: <UploadCloud className="h-5 w-5" /> },
  { to: '/history', label: 'History', icon: <Archive className="h-5 w-5" /> },
]

export function NavRail() {
  const { isNavCollapsed, activeInvestigation } = useInvestigationStore()

  return (
    <>
      {/* Desktop / Tablet Left Navigation Rail */}
      <aside
        className={`hidden md:flex flex-col border-r transition-all duration-300 ease-in-out shrink-0 select-none ${
          isNavCollapsed ? 'w-16' : 'w-60'
        }`}
        style={{ borderColor: 'var(--line)', background: 'var(--panel)' }}
      >
        <div className="flex flex-col gap-1.5 p-3 flex-1 overflow-y-auto">
          {NAV_ITEMS.map(item => {
            const hasData = !!activeInvestigation
            return (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  `group relative flex items-center gap-3.5 rounded-xl px-3 py-2.5 text-sm font-medium transition-all ${
                    isActive
                      ? 'bg-sky-500/15 text-sky-400 border border-sky-500/30 font-semibold shadow-sm'
                      : 'text-slate-400 hover:bg-slate-800/60 hover:text-slate-200'
                  }`
                }
              >
                <span className="shrink-0 transition-transform group-hover:scale-110">
                  {item.icon}
                </span>

                {!isNavCollapsed && (
                  <span className="truncate whitespace-nowrap">{item.label}</span>
                )}

                {/* Subtle indicator dot if data is active for this tab */}
                {item.requiresData && hasData && !isNavCollapsed && (
                  <span className="ml-auto h-2 w-2 rounded-full bg-emerald-400 ring-4 ring-emerald-400/20" />
                )}

                {/* Hover Tooltip when collapsed */}
                {isNavCollapsed && (
                  <div className="pointer-events-none absolute left-full ml-3 z-50 hidden rounded-md bg-slate-900 border border-slate-700 px-2.5 py-1 text-xs font-semibold text-slate-100 whitespace-nowrap shadow-xl group-hover:block">
                    {item.label}
                  </div>
                )}
              </NavLink>
            )
          })}
        </div>

        {/* System info footnote */}
        {!isNavCollapsed && (
          <div className="border-t p-3 text-[11px] text-slate-500" style={{ borderColor: 'var(--line)' }}>
            <div>Sentinel-2 MSI Level-2A</div>
            <div>Projection: Projected UTM / WGS84</div>
          </div>
        )}
      </aside>

      {/* Mobile Bottom Navigation Bar */}
      <nav
        className="fixed bottom-0 inset-x-0 z-[1200] flex md:hidden h-14 items-center justify-around border-t px-2 overflow-x-auto"
        style={{ borderColor: 'var(--line)', background: 'var(--panel)' }}
      >
        {NAV_ITEMS.slice(0, 5).map(item => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              `flex flex-col items-center justify-center gap-0.5 px-2 py-1 text-[10px] font-medium transition-colors ${
                isActive ? 'text-sky-400 font-bold' : 'text-slate-400'
              }`
            }
          >
            {item.icon}
            <span className="truncate max-w-[60px]">{item.label}</span>
          </NavLink>
        ))}
      </nav>
    </>
  )
}
