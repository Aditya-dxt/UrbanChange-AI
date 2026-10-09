import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  ArrowRight,
  Compass,
  FileText,
  Info,
  Network,
  Share2,
  Sparkles,
  Tag,
  X,
} from 'lucide-react'
import { Card } from '../components/common/Card'
import { EmptyState } from '../components/common/EmptyState'
import { Badge } from '../components/common/Badge'
import { StatTile } from '../components/common/StatTile'
import { useInvestigationStore } from '../store/useInvestigationStore'
import type { EvidenceGraphNode } from '../types'

export default function EvidenceGraphPage() {
  const navigate = useNavigate()
  const { activeInvestigation } = useInvestigationStore()
  const [selectedNode, setSelectedNode] = useState<EvidenceGraphNode | null>(null)
  const [filterType, setFilterType] = useState<string>('all')

  if (!activeInvestigation || !activeInvestigation.evidence_graph) {
    return (
      <div className="flex-1 p-6 flex items-center justify-center">
        <EmptyState
          title="No Evidence Graph Available"
          description="An evidence graph is generated during investigation to provide an explainable audit trail linking raw satellite scenes, model predictions, and spatial context."
          actionLabel="Go to Investigate Map"
          onAction={() => navigate('/investigate')}
          icon={<Network className="h-8 w-8 text-purple-400" />}
        />
      </div>
    )
  }

  const graph = activeInvestigation.evidence_graph
  const evidence = activeInvestigation.evidence || []

  const nodeTypes = ['all', ...Array.from(new Set(graph.nodes.map(n => n.type)))]

  const filteredNodes =
    filterType === 'all'
      ? graph.nodes
      : graph.nodes.filter(n => n.type === filterType)

  return (
    <div className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8 space-y-6">
      {/* HEADER */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-mono text-purple-400 font-semibold uppercase tracking-wider">
              Explainable AI & Provenance
            </span>
            <Badge variant="default" size="sm" className="font-mono">
              {graph.nodes.length} Nodes · {graph.edges.length} Edges
            </Badge>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-100 tracking-tight">
            Evidence Graph
          </h1>
          <p className="text-xs sm:text-sm text-slate-400 mt-1">
            Auditable knowledge graph connecting input observations, model inferences, and GIS planning constraints.
          </p>
        </div>

        <button
          onClick={() => navigate('/results')}
          className="btn-ghost text-xs border border-slate-700/80 self-start sm:self-auto"
        >
          ← Back to Results
        </button>
      </div>

      {/* STATS TILES */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatTile
          label="Total Graph Nodes"
          value={graph.nodes.length.toString()}
          subValue="Entities in provenance tree"
          variant="default"
        />
        <StatTile
          label="Inference Edges"
          value={graph.edges.length.toString()}
          subValue="Causal relations tracked"
          variant="default"
        />
        <StatTile
          label="Referenced Records"
          value={evidence.length.toString()}
          subValue="Citable audit entries"
          variant="default"
        />
        <StatTile
          label="Inspection Focus"
          value={selectedNode ? selectedNode.label : 'None selected'}
          subValue={selectedNode ? `Type: ${selectedNode.type}` : 'Click any node to inspect'}
          variant={selectedNode ? 'info' : 'default'}
        />
      </div>

      {/* FILTER TABS */}
      <div className="flex items-center gap-1.5 overflow-x-auto pb-1">
        <span className="text-xs text-slate-400 font-medium mr-2">Filter Nodes:</span>
        {nodeTypes.map(t => (
          <button
            key={t}
            onClick={() => setFilterType(t)}
            className={`rounded-lg px-3 py-1 text-xs font-medium uppercase tracking-wider transition-colors ${
              filterType === t
                ? 'bg-purple-500/20 text-purple-300 border border-purple-500/40 font-bold'
                : 'bg-slate-900 border border-slate-800 text-slate-400 hover:text-slate-200'
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      {/* GRAPH NODES & INSPECTOR DUAL-VIEW */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2 Cols: Nodes Interactive Grid */}
        <div className="lg:col-span-2 space-y-4">
          <Card
            title="Interactive Graph Entities"
            subtitle="Click any node below to inspect its detailed evidence properties"
          >
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {filteredNodes.map(node => {
                const isSelected = selectedNode?.id === node.id
                let badgeColor = 'bg-slate-800 text-slate-300 border-slate-700'
                if (node.type === 'observation')
                  badgeColor = 'bg-blue-950/70 text-blue-300 border-blue-800/60'
                if (node.type === 'detection')
                  badgeColor = 'bg-amber-950/70 text-amber-300 border-amber-800/60'
                if (node.type === 'gis')
                  badgeColor = 'bg-cyan-950/70 text-cyan-300 border-cyan-800/60'
                if (node.type === 'fingerprint')
                  badgeColor = 'bg-purple-950/70 text-purple-300 border-purple-800/60'

                return (
                  <div
                    key={node.id}
                    onClick={() => setSelectedNode(node)}
                    className={`rounded-xl border p-3 cursor-pointer transition-all flex flex-col justify-between gap-2 ${
                      isSelected
                        ? 'border-purple-500 bg-purple-950/25 ring-2 ring-purple-500/30 shadow-lg shadow-purple-500/10'
                        : 'border-slate-800 bg-slate-900/50 hover:border-slate-700 hover:bg-slate-900'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <span
                        className={`rounded border px-2 py-0.5 text-[10px] font-mono uppercase font-bold ${badgeColor}`}
                      >
                        {node.type}
                      </span>
                      <span className="text-[11px] font-mono text-slate-500">{node.id}</span>
                    </div>

                    <div>
                      <h4 className="font-semibold text-slate-200 text-sm">{node.label}</h4>
                      {node.details && (
                        <p className="text-xs text-slate-400 mt-1 line-clamp-2">
                          {node.details}
                        </p>
                      )}
                    </div>

                    <div className="text-[11px] text-purple-400 font-medium flex items-center gap-1 pt-1 border-t border-slate-800/60">
                      <span>Inspect node details</span>
                      <ArrowRight className="h-3 w-3" />
                    </div>
                  </div>
                )
              })}
            </div>
          </Card>

          {/* Inference Pathways Card */}
          <Card
            title="Inference Pathways & Directed Edges"
            subtitle="Causal relationships tracking derivation and evaluation logic"
          >
            <div className="flex flex-col gap-2 max-h-72 overflow-y-auto pr-1">
              {graph.edges.map((e, idx) => (
                <div
                  key={idx}
                  className="flex flex-wrap items-center gap-2 rounded-lg border border-slate-800/80 bg-slate-950/60 p-2.5 text-xs"
                >
                  <span className="font-mono text-sky-400 font-semibold bg-sky-950/50 border border-sky-800/40 px-2 py-0.5 rounded">
                    {e.source}
                  </span>
                  <div className="flex items-center gap-1 text-slate-500 text-[11px] font-medium">
                    <span>──</span>
                    <span className="rounded bg-slate-800 px-1.5 py-0.5 text-slate-300 font-mono">
                      {e.relation}
                    </span>
                    <span>──▶</span>
                  </div>
                  <span className="font-mono text-purple-400 font-semibold bg-purple-950/50 border border-purple-800/40 px-2 py-0.5 rounded">
                    {e.target}
                  </span>
                </div>
              ))}
            </div>
          </Card>
        </div>

        {/* Right 1 Col: Node Inspector Side Panel */}
        <div className="space-y-4">
          <Card
            title="Node Inspector"
            subtitle={selectedNode ? selectedNode.id : 'Click a node to view attributes'}
          >
            {selectedNode ? (
              <div className="space-y-4">
                <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                  <div>
                    <span className="text-[10px] uppercase font-bold text-slate-400">
                      Entity Type
                    </span>
                    <div className="text-sm font-bold text-slate-100 capitalize">
                      {selectedNode.type}
                    </div>
                  </div>
                  <Badge variant="info" size="sm" className="font-mono">
                    {selectedNode.id}
                  </Badge>
                </div>

                <div>
                  <span className="text-xs font-medium text-slate-400">Label</span>
                  <div className="text-sm font-semibold text-slate-200 mt-0.5">
                    {selectedNode.label}
                  </div>
                </div>

                {selectedNode.details && (
                  <div>
                    <span className="text-xs font-medium text-slate-400">Payload & Details</span>
                    <div className="rounded-lg border border-slate-800 bg-slate-950 p-3 text-xs text-slate-300 font-mono mt-1 whitespace-pre-wrap leading-relaxed">
                      {selectedNode.details}
                    </div>
                  </div>
                )}

                {/* Connected edges for this node */}
                <div>
                  <span className="text-xs font-medium text-slate-400">Connected Inferences</span>
                  <div className="mt-1 space-y-1.5">
                    {graph.edges
                      .filter(
                        e => e.source === selectedNode.id || e.target === selectedNode.id
                      )
                      .map((e, idx) => (
                        <div
                          key={idx}
                          className="rounded border border-slate-800 bg-slate-900/60 p-2 text-[11px] text-slate-300"
                        >
                          <span className="text-slate-400">
                            {e.source === selectedNode.id ? 'Targets:' : 'Derived from:'}
                          </span>{' '}
                          <b className="font-mono text-purple-300">
                            {e.source === selectedNode.id ? e.target : e.source}
                          </b>{' '}
                          via <span className="text-sky-400">({e.relation})</span>
                        </div>
                      ))}
                  </div>
                </div>
              </div>
            ) : (
              <div className="p-8 text-center text-xs text-slate-400">
                <Info className="h-6 w-6 text-slate-500 mx-auto mb-2" />
                Select any node from the interactive grid to review its causal connections and payload data.
              </div>
            )}
          </Card>

          {/* Audit Trail List */}
          <Card
            title="Referenced Evidence Records"
            subtitle="Text citations used in AI explanation generation"
          >
            <div className="space-y-2 max-h-80 overflow-y-auto pr-1">
              {evidence.map(e => (
                <div
                  key={e.id}
                  className="rounded-lg border border-slate-800 bg-slate-900/40 p-2.5 text-xs space-y-1"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono font-bold text-sky-400 bg-sky-950/60 px-1.5 py-0.5 rounded border border-sky-800/40 text-[10px]">
                      {e.id}
                    </span>
                    <span className="text-slate-400 text-[10px] uppercase font-semibold">
                      {e.type}
                    </span>
                  </div>
                  <p className="text-slate-300 text-[11px] leading-relaxed">{e.text}</p>
                </div>
              ))}
            </div>
          </Card>
        </div>
      </div>
    </div>
  )
}
