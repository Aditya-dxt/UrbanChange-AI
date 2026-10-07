import { useState } from 'react'
import type { Investigation } from '../types'
import Assistant from './Assistant'
import { Banner, BeforeAfter, Disclaimer, EvidencePanel, FingerprintCard, GisPanel, ResultCards, Timeline } from './Panels'

// Renders every state: complete, partial (temporal null), empty (detection null), low confidence.
export default function Results({ inv }: { inv: Investigation }) {
  const [mask, setMask] = useState(true)
  const [idx, setIdx] = useState(inv.temporal ? inv.temporal.length - 1 : 0)
  const d = inv.detection
  const afterUrl = inv.temporal ? inv.temporal[idx].image_url : inv.observations.t2.image_url
  return <div className="flex flex-col gap-3">
    <Disclaimer />
    {inv.status === 'partial' && <Banner>Partial result: temporal reconstruction is unavailable for this area.</Banner>}
    <BeforeAfter inv={inv} maskOn={mask} onMask={setMask} afterUrl={afterUrl} />
    {!d ? <div className="card"><span className="pill">No significant change detected</span><p className="text-sm opacity-70">No polygons exceeded the model threshold for this area and period.</p></div> : <>
      {d.confidence < 0.6 && <Banner danger>Low confidence ({Math.round(d.confidence * 100)}%). Unverified; manual review required before drawing conclusions.</Banner>}
      <ResultCards d={d} />
    </>}
    {inv.gis && <GisPanel gis={inv.gis} />}
    {inv.temporal && <Timeline events={inv.temporal} idx={idx} onIdx={setIdx} />}
    <div className="grid gap-3 ">
      {inv.fingerprint && <FingerprintCard f={inv.fingerprint} />}
      {d && <EvidencePanel evidence={inv.evidence} text={inv.explanation} graph={inv.evidence_graph} />}
    </div>
    {d && <Assistant investigationId={inv.id} />}
  </div>
}
