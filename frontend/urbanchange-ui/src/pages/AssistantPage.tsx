import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  AlertTriangle,
  Bot,
  Compass,
  CornerDownLeft,
  FileCheck2,
  HelpCircle,
  RotateCcw,
  Send,
  Sparkles,
  User,
} from 'lucide-react'
import { api } from '../api/client'
import { Badge } from '../components/common/Badge'
import { Card } from '../components/common/Card'
import { useInvestigationStore } from '../store/useInvestigationStore'

interface ChatMessage {
  id: string
  role: 'user' | 'ai'
  text: string
  evidence_ids?: string[]
  timestamp: string
}

const SUGGESTED_QUESTIONS = [
  'What physical changes were detected in this area?',
  'When did the surface excavation or construction begin?',
  'Does this footprint intersect any sensitive zoning buffers?',
  'Why was this classified with high priority?',
  'What is the total measured change in square meters?',
]

export default function AssistantPage() {
  const navigate = useNavigate()
  const { activeInvestigation } = useInvestigationStore()

  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'init',
      role: 'ai',
      text: activeInvestigation
        ? `I am your UrbanChange AI Investigation Assistant. I have indexed the multi-temporal Sentinel-2 imagery, change segmentation mask, and GIS zoning overlays for Investigation #${activeInvestigation.id}. What would you like to examine?`
        : 'Welcome to the UrbanChange AI Investigation Assistant. Run an investigation from the Investigate map, or ask general questions about satellite change detection methodology.',
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    },
  ])

  const [inputQuestion, setInputQuestion] = useState('')
  const [isBusy, setIsBusy] = useState(false)

  async function handleSend(queryText: string) {
    const q = queryText.trim()
    if (!q || isBusy) return

    const userMsg: ChatMessage = {
      id: `u-${Date.now()}`,
      role: 'user',
      text: q,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    }

    setMessages(prev => [...prev, userMsg])
    setInputQuestion('')
    setIsBusy(true)

    try {
      if (activeInvestigation) {
        const response = await api.ask(activeInvestigation.id, q)
        const aiMsg: ChatMessage = {
          id: `ai-${Date.now()}`,
          role: 'ai',
          text: response.answer,
          evidence_ids: response.evidence_ids,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        }
        setMessages(prev => [...prev, aiMsg])
      } else {
        // Fallback for general inquiry when no active investigation
        setTimeout(() => {
          setMessages(prev => [
            ...prev,
            {
              id: `ai-${Date.now()}`,
              role: 'ai',
              text:
                'To ground specific answers in physical satellite evidence, please create an investigation on the Investigate page by selecting an AOI.',
              timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
            },
          ])
          setIsBusy(false)
        }, 600)
        return
      }
    } catch (err: any) {
      setMessages(prev => [
        ...prev,
        {
          id: `err-${Date.now()}`,
          role: 'ai',
          text: `Assistant response unavailable: ${err.message || 'Pipeline communication error'}`,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        },
      ])
    } finally {
      setIsBusy(false)
    }
  }

  function handleClear() {
    setMessages([
      {
        id: 'init',
        role: 'ai',
        text: 'Investigation chat history cleared. How else can I assist your verification?',
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      },
    ])
  }

  return (
    <div className="flex h-full flex-col p-4 sm:p-6 lg:p-8 overflow-hidden">
      {/* HEADER */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-4 shrink-0">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-mono text-sky-400 font-semibold uppercase tracking-wider">
              Investigation Assistant
            </span>
            {activeInvestigation ? (
              <Badge variant="info" size="sm" className="font-mono">
                Context: #{activeInvestigation.id}
              </Badge>
            ) : (
              <Badge variant="default" size="sm">
                General Mode
              </Badge>
            )}
          </div>
          <h1 className="text-xl sm:text-2xl font-extrabold text-slate-100 tracking-tight flex items-center gap-2">
            <Bot className="h-6 w-6 text-sky-400" />
            AI Evidence Inquirer
          </h1>
        </div>

        <div className="flex items-center gap-2">
          {activeInvestigation && (
            <button
              onClick={() => navigate('/results')}
              className="btn-ghost text-xs border border-slate-700/80"
            >
              View Results
            </button>
          )}
          <button
            onClick={handleClear}
            className="btn-ghost text-xs text-slate-400 hover:text-slate-200 border border-slate-700/80 flex items-center gap-1.5"
            title="Clear chat messages"
          >
            <RotateCcw className="h-3.5 w-3.5" /> Clear History
          </button>
        </div>
      </div>

      {/* STATUTORY DISCLAIMER NOTE */}
      <div className="mt-3 shrink-0 rounded-lg border border-amber-500/30 bg-amber-950/20 px-3 py-2 text-xs text-amber-200/90 flex items-center gap-2">
        <AlertTriangle className="h-4 w-4 text-amber-400 shrink-0" />
        <span>
          Assistant responses are grounded in calculated evidence graph nodes. Requires human verification before statutory action.
        </span>
      </div>

      {/* MESSAGE STREAM (SCROLLABLE AREA) */}
      <div className="my-4 flex-1 overflow-y-auto space-y-4 pr-2">
        {messages.map(msg => (
          <div
            key={msg.id}
            className={`flex flex-col ${
              msg.role === 'user' ? 'items-end' : 'items-start'
            }`}
          >
            <div
              className={`max-w-[85%] sm:max-w-[75%] rounded-2xl p-4 shadow-sm text-xs sm:text-sm leading-relaxed ${
                msg.role === 'user'
                  ? 'bg-sky-600 text-white rounded-br-none'
                  : 'bg-slate-900 border border-slate-800 text-slate-200 rounded-bl-none'
              }`}
            >
              <div className="flex items-center justify-between gap-4 mb-1 text-[11px] opacity-75">
                <span className="font-semibold flex items-center gap-1">
                  {msg.role === 'user' ? (
                    <>
                      <User className="h-3 w-3" /> Investigator
                    </>
                  ) : (
                    <>
                      <Sparkles className="h-3 w-3 text-sky-400" /> Grounded Assistant
                    </>
                  )}
                </span>
                <span>{msg.timestamp}</span>
              </div>

              <div className="whitespace-pre-wrap">{msg.text}</div>

              {/* Evidence Citations if present */}
              {msg.evidence_ids && msg.evidence_ids.length > 0 && (
                <div className="mt-3 pt-2 border-t border-slate-800 text-[11px] flex flex-wrap items-center gap-1.5">
                  <span className="text-slate-400 font-semibold">Grounded Citations:</span>
                  {msg.evidence_ids.map(eid => (
                    <span
                      key={eid}
                      className="rounded bg-sky-950 px-2 py-0.5 font-mono text-sky-400 border border-sky-800/60 font-semibold"
                    >
                      {eid}
                    </span>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}

        {isBusy && (
          <div className="flex items-center gap-2 rounded-xl bg-slate-900/60 border border-slate-800 p-3 max-w-xs text-xs text-slate-400">
            <Bot className="h-4 w-4 animate-spin text-sky-400" />
            <span>Consulting evidence graph & reasoning…</span>
          </div>
        )}
      </div>

      {/* SUGGESTED PROMPTS */}
      <div className="shrink-0 mb-3 flex flex-wrap items-center gap-1.5 overflow-x-auto">
        <span className="text-[11px] font-semibold text-slate-400 mr-1">Suggested:</span>
        {SUGGESTED_QUESTIONS.map((s, idx) => (
          <button
            key={idx}
            onClick={() => handleSend(s)}
            className="rounded-lg border border-slate-800 bg-slate-900/80 px-2.5 py-1 text-[11px] text-slate-300 hover:border-sky-500/40 hover:text-sky-300 transition-colors"
          >
            {s}
          </button>
        ))}
      </div>

      {/* CHAT INPUT FORM */}
      <form
        onSubmit={e => {
          e.preventDefault()
          handleSend(inputQuestion)
        }}
        className="shrink-0 flex items-center gap-2 rounded-2xl border border-slate-700/80 bg-slate-900/90 p-2 shadow-xl"
      >
        <input
          type="text"
          value={inputQuestion}
          onChange={e => setInputQuestion(e.target.value)}
          placeholder="Ask a question about this change footprint or planning conflict…"
          className="w-full bg-transparent px-3 text-xs sm:text-sm text-slate-100 placeholder-slate-400 focus:outline-none"
          disabled={isBusy}
        />
        <button
          type="submit"
          disabled={!inputQuestion.trim() || isBusy}
          className="btn flex items-center gap-1.5 py-2 px-4 text-xs font-semibold"
        >
          <span>Ask</span>
          <Send className="h-3.5 w-3.5" />
        </button>
      </form>
    </div>
  )
}
