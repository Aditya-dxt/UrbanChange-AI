import { useMemo, useState } from 'react'
import { Banner, ProgressSteps } from './Panels'
import Results from './Results'
import { useInvestigation } from '../hooks/useInvestigation'

function Drop({ label, hint, file, onFile }: { label: string; hint: string; file?: File; onFile: (f: File) => void }) {
  const [over, setOver] = useState(false)
  const url = useMemo(() => (file && file.type.startsWith('image/') ? URL.createObjectURL(file) : undefined), [file])
  return <label
    onDragOver={e => { e.preventDefault(); setOver(true) }} onDragLeave={() => setOver(false)}
    onDrop={e => { e.preventDefault(); setOver(false); const f = e.dataTransfer.files[0]; if (f) onFile(f) }}
    className="flex min-h-[220px] cursor-pointer flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed p-4 text-center focus-within:outline focus-within:outline-2"
    style={{ borderColor: over || file ? 'var(--acc)' : 'var(--line)', outlineColor: 'var(--acc)' }}>
    {url ? <img src={url} alt={file!.name} className="max-h-40 rounded" />
      : <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="var(--mu)" strokeWidth="1.6" aria-hidden><path d="M12 16V4m0 0L7 9m5-5l5 5M4 16v3a1 1 0 001 1h14a1 1 0 001-1v-3" /></svg>}
    <div className="display text-lg font-bold">{label}</div>
    <div className="mu break-all text-sm">{file ? file.name : hint}</div>
    {file && <span className="pill">Click to replace</span>}
    <input type="file" className="sr-only" accept="image/*,.tif,.tiff" onChange={e => { const f = e.target.files?.[0]; if (f) onFile(f) }} />
  </label>
}

export default function UploadMode() {
  const [b, setB] = useState<File>(), [a, setA] = useState<File>()
  const { state, upload } = useInvestigation()
  const tiff = (f?: File) => !!f && /\.tiff?$/i.test(f.name)
  return <div className="flex flex-col gap-3">
    <div className="card flex flex-col gap-3">
      <h2 className="display text-lg font-bold">Add your two images</h2>
      <p className="mu text-sm">Use the same place and the same view in both. Drag a file onto a box or click to browse. PNG, JPEG or GeoTIFF.</p>
      <div className="grid gap-3 grid-cols-2">
        <Drop label="Earlier image" hint="The 'before' picture" file={b} onFile={setB} />
        <Drop label="Later image" hint="The 'after' picture" file={a} onFile={setA} />
      </div>
      {(b || a) && !(tiff(b) && tiff(a)) && <Banner>These files may not carry location data, so area and sensitive-zone results are only indicative. Use GeoTIFF files for measured results.</Banner>}
      <div className="flex items-center gap-3">
        <button className="btn" disabled={!b || !a || state.phase === 'loading'} onClick={() => b && a && upload(b, a)}>Find changes</button>
        {(!b || !a) && <span className="mu text-sm">{!b && !a ? 'Add both images to continue.' : `Add the ${!b ? 'earlier' : 'later'} image to continue.`}</span>}
      </div>
    </div>
    {state.phase === 'loading' && <div className="card"><ProgressSteps step={state.step} /></div>}
    {state.phase === 'error' && <Banner danger>Couldn&rsquo;t analyse the images: {state.error}. Check the files and try again.</Banner>}
    {state.data && <Results inv={state.data} />}
  </div>
}
