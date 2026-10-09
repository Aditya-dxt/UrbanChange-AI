import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  FileCheck,
  FileText,
  Image as ImageIcon,
  Info,
  Sparkles,
  UploadCloud,
  X,
} from 'lucide-react'
import { ProgressSteps } from '../components/Panels'
import { Card } from '../components/common/Card'
import { Badge } from '../components/common/Badge'
import { useInvestigationStore } from '../store/useInvestigationStore'

function DropZone({
  label,
  subtitle,
  file,
  onFile,
  onClear,
}: {
  label: string
  subtitle: string
  file?: File
  onFile: (f: File) => void
  onClear: () => void
}) {
  const [isDragOver, setIsDragOver] = useState(false)

  const previewUrl = useMemo(() => {
    if (file && file.type.startsWith('image/')) {
      return URL.createObjectURL(file)
    }
    return undefined
  }, [file])

  const isTiff = file ? /\.tiff?$/i.test(file.name) : false

  return (
    <div
      onDragOver={e => {
        e.preventDefault()
        setIsDragOver(true)
      }}
      onDragLeave={() => setIsDragOver(false)}
      onDrop={e => {
        e.preventDefault()
        setIsDragOver(false)
        const dropped = e.dataTransfer.files[0]
        if (dropped) onFile(dropped)
      }}
      className={`relative flex min-h-[260px] flex-col items-center justify-center rounded-2xl border-2 border-dashed p-6 text-center transition-all ${
        isDragOver
          ? 'border-sky-400 bg-sky-950/20'
          : file
          ? 'border-emerald-500/50 bg-slate-900/60'
          : 'border-slate-800 bg-slate-900/30 hover:border-slate-700 hover:bg-slate-900/50'
      }`}
    >
      {file ? (
        <div className="flex flex-col items-center gap-3 max-w-full">
          {previewUrl ? (
            <div className="relative max-h-40 max-w-full overflow-hidden rounded-xl border border-slate-700">
              <img src={previewUrl} alt={file.name} className="h-36 object-contain" />
            </div>
          ) : (
            <div className="flex h-24 w-24 items-center justify-center rounded-2xl bg-sky-950/60 border border-sky-800/40 text-sky-400">
              <FileText className="h-10 w-10" />
            </div>
          )}

          <div className="text-center">
            <div className="flex items-center justify-center gap-1.5 text-xs font-bold text-slate-100 truncate max-w-xs">
              <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0" />
              <span className="truncate">{file.name}</span>
            </div>
            <div className="text-[11px] text-slate-400 mt-0.5">
              {(file.size / (1024 * 1024)).toFixed(2)} MB · {isTiff ? 'GeoTIFF raster' : file.type}
            </div>
          </div>

          <div className="flex items-center gap-2 mt-1">
            <Badge variant={isTiff ? 'success' : 'default'} size="sm">
              {isTiff ? 'Georeferenced GeoTIFF' : 'Standard Image'}
            </Badge>
            <button
              onClick={e => {
                e.stopPropagation()
                onClear()
              }}
              className="text-xs text-rose-400 hover:underline"
            >
              Remove
            </button>
          </div>
        </div>
      ) : (
        <label className="flex h-full w-full cursor-pointer flex-col items-center justify-center gap-3">
          <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-slate-800/80 text-slate-400">
            <UploadCloud className="h-7 w-7 text-sky-400" />
          </div>
          <div>
            <div className="text-sm font-bold text-slate-200">{label}</div>
            <div className="text-xs text-slate-400 mt-1">{subtitle}</div>
          </div>
          <span className="rounded-lg bg-slate-800 px-3 py-1 text-xs text-slate-300 font-medium">
            Browse file or drag here
          </span>
          <span className="text-[11px] text-slate-500">Supports GeoTIFF, PNG, JPEG</span>
          <input
            type="file"
            className="sr-only"
            accept="image/*,.tif,.tiff"
            onChange={e => {
              const selected = e.target.files?.[0]
              if (selected) onFile(selected)
            }}
          />
        </label>
      )}
    </div>
  )
}

export default function UploadPage() {
  const navigate = useNavigate()
  const { phase, step, error, activeInvestigation, executeUpload } = useInvestigationStore()

  const [beforeFile, setBeforeFile] = useState<File | undefined>()
  const [afterFile, setAfterFile] = useState<File | undefined>()

  const isBeforeTiff = beforeFile ? /\.tiff?$/i.test(beforeFile.name) : false
  const isAfterTiff = afterFile ? /\.tiff?$/i.test(afterFile.name) : false
  const bothTiff = isBeforeTiff && isAfterTiff
  const hasFiles = !!beforeFile && !!afterFile

  async function handleAnalyze() {
    if (!beforeFile || !afterFile) return
    const res = await executeUpload(beforeFile, afterFile)
    if (res) {
      navigate('/results')
    }
  }

  return (
    <div className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8 space-y-6">
      {/* HEADER */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-mono text-sky-400 font-semibold uppercase tracking-wider">
              Manual Pair Analysis
            </span>
            <Badge variant="default" size="sm">
              Custom Rasters
            </Badge>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-100 tracking-tight">
            Upload Before & After Imagery
          </h1>
          <p className="text-xs sm:text-sm text-slate-400 mt-1">
            Upload custom ortho-imagery or drone captures to run change segmentation without catalog lookups.
          </p>
        </div>
      </div>

      {/* GEOREFERENCING ALERT OR STATUS */}
      {hasFiles && (
        <>
          {bothTiff ? (
            <div className="rounded-xl border border-emerald-500/40 bg-emerald-950/20 p-4 text-xs sm:text-sm text-emerald-200 flex items-start gap-3">
              <CheckCircle2 className="h-5 w-5 text-emerald-400 shrink-0 mt-0.5" />
              <div>
                <b className="font-semibold text-emerald-300">
                  Georeferencing Metadata Detected (GeoTIFF)
                </b>
                <p className="mt-1 text-slate-300">
                  Embedded projection tags and transform matrices found. Exact ground metric area in m²
                  and sensitive zoning buffer overlaps will be accurately calculated.
                </p>
              </div>
            </div>
          ) : (
            <div className="rounded-xl border border-amber-500/40 bg-amber-950/20 p-4 text-xs sm:text-sm text-amber-200 flex items-start gap-3">
              <AlertTriangle className="h-5 w-5 text-amber-400 shrink-0 mt-0.5" />
              <div>
                <b className="font-semibold text-amber-300">
                  Non-georeferenced Imagery Warning
                </b>
                <p className="mt-1 text-slate-300">
                  One or both images do not carry embedded spatial coordinate reference tags. Change
                  segmentation will run, but metric spatial measurements (m²) and GIS layer overlays
                  will be indicative only. Use GeoTIFF (.tif) files for statutory precision.
                </p>
              </div>
            </div>
          )}
        </>
      )}

      {/* DROP ZONES GRID */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <DropZone
          label="Historical Image (T1)"
          subtitle="Baseline or pre-disturbance capture"
          file={beforeFile}
          onFile={setBeforeFile}
          onClear={() => setBeforeFile(undefined)}
        />

        <DropZone
          label="Recent Image (T2)"
          subtitle="Recent or post-disturbance capture"
          file={afterFile}
          onFile={setAfterFile}
          onClear={() => setAfterFile(undefined)}
        />
      </div>

      {/* PIPELINE PROGRESS IF LOADING */}
      {phase === 'loading' && (
        <Card title="Processing Upload Pipeline">
          <ProgressSteps step={step} />
        </Card>
      )}

      {/* ERROR IF FAILED */}
      {phase === 'error' && (
        <div className="rounded-xl border border-rose-500/40 bg-rose-950/30 p-4 text-xs sm:text-sm text-rose-300">
          <b>Pipeline Failure:</b> {error}
        </div>
      )}

      {/* ACTION CONTROLS */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
        <div>
          <div className="text-sm font-semibold text-slate-200">Ready to Analyze</div>
          <div className="text-xs text-slate-400">
            {hasFiles
              ? 'Both scenes loaded. Click button to begin alignment and change segmentation.'
              : 'Add both before and after images above to continue.'}
          </div>
        </div>

        <button
          onClick={handleAnalyze}
          disabled={!hasFiles || phase === 'loading'}
          className="btn flex items-center justify-center gap-2 py-2.5 px-6 text-xs font-bold uppercase tracking-wider shadow-lg"
        >
          <Sparkles className="h-4 w-4" />
          {phase === 'loading' ? 'Analyzing Rasters…' : 'Execute Change Detection'}
        </button>
      </div>
    </div>
  )
}
