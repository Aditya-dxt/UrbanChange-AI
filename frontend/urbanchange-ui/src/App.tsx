import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { TopBar } from './components/layout/TopBar'
import { NavRail } from './components/layout/NavRail'
import { FooterBanner } from './components/layout/FooterBanner'

// Pages
import InvestigatePage from './pages/InvestigatePage'
import ResultsPage from './pages/ResultsPage'
import FingerprintPage from './pages/FingerprintPage'
import SensitiveZonesPage from './pages/SensitiveZonesPage'
import TimelinePage from './pages/TimelinePage'
import EvidenceGraphPage from './pages/EvidenceGraphPage'
import AssistantPage from './pages/AssistantPage'
import UploadPage from './pages/UploadPage'
import HistoryPage from './pages/HistoryPage'

export default function App() {
  return (
    <BrowserRouter>
      <div className="flex h-screen w-screen flex-col overflow-hidden bg-slate-950 text-slate-100 antialiased selection:bg-sky-500 selection:text-white">
        {/* TOP BAR */}
        <TopBar />

        {/* WORKSPACE MIDDLE: LEFT NAV + MAIN CONTENT */}
        <div className="flex flex-1 min-h-0 w-full overflow-hidden">
          {/* Collapsible Left Rail (turns into bottom bar on mobile) */}
          <NavRail />

          {/* DEDICATED SECTION VIEWPORT */}
          <main className="flex-1 flex flex-col min-h-0 min-w-0 overflow-hidden relative pb-14 md:pb-0">
            <Routes>
              <Route path="/" element={<Navigate to="/investigate" replace />} />
              <Route path="/investigate" element={<InvestigatePage />} />
              <Route path="/results" element={<ResultsPage />} />
              <Route path="/fingerprint" element={<FingerprintPage />} />
              <Route path="/sensitive-zones" element={<SensitiveZonesPage />} />
              <Route path="/timeline" element={<TimelinePage />} />
              <Route path="/evidence-graph" element={<EvidenceGraphPage />} />
              <Route path="/assistant" element={<AssistantPage />} />
              <Route path="/upload" element={<UploadPage />} />
              <Route path="/history" element={<HistoryPage />} />
              <Route path="*" element={<Navigate to="/investigate" replace />} />
            </Routes>
          </main>
        </div>

        {/* STATUTORY COMPLIANCE PERSISTENT FOOTER */}
        <FooterBanner />
      </div>
    </BrowserRouter>
  )
}
