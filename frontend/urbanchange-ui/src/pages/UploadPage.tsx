import { useMemo, useState } from 'react'
import {
  AlertTriangle,
  ArrowRight,
  Calendar,
  CheckCircle2,
  FileCheck,
  FileText,
  FolderOpen,
  Image as ImageIcon,
  Info,
  Maximize2,
  Ruler,
  Sliders,
  Sparkles,
  UploadCloud,
  X,
} from 'lucide-react'
import { ProgressSteps } from '../components/Panels'
import { Card } from '../components/common/Card'
import { Badge } from '../components/common/Badge'
import Results from '../components/Results'
import { useInvestigationStore } from '../store/useInvestigationStore'

interface SamplePreset {
  id: string
  name: string
  type: string
  beforePath: string
  afterPath: string
  resolutionM: number
  histDate: string
  currDate: string
  isTiff: boolean
  description: string
  bbox?: [number, number, number, number]
}

const SAMPLE_PRESETS: SamplePreset[] = [
  {
    id: 'pair_01_construction',
    name: 'Sample 1: New Urban Residential Development',
    type: 'construction',
    beforePath: '/sample_pairs/pair_01_construction/before.png',
    afterPath: '/sample_pairs/pair_01_construction/after.png',
    resolutionM: 0.5,
    histDate: '2023-03-10',
    currDate: '2024-02-15',
    isTiff: false,
    description: 'Rapid residential housing construction detected in suburban expansion zone (LEVIR-CD aerial 0.5m).',
  },
  {
    id: 'pair_02_deforestation',
    name: 'Sample 2: Forest Land Clearing (Vegetation Loss)',
    type: 'vegetation_loss',
    beforePath: '/sample_pairs/pair_02_deforestation/before.png',
    afterPath: '/sample_pairs/pair_02_deforestation/after.png',
    resolutionM: 0.5,
    histDate: '2023-01-20',
    currDate: '2023-11-14',
    isTiff: false,
    description: 'Clearing of dense forest canopy for land alteration and site preparation.',
  },
  {
    id: 'pair_03_road_infra',
    name: 'Sample 3: Linear Transport / Road Infrastructure Corridor',
    type: 'infrastructure',
    beforePath: '/sample_pairs/pair_03_road_infra/before.png',
    afterPath: '/sample_pairs/pair_03_road_infra/after.png',
    resolutionM: 0.5,
    histDate: '2023-05-01',
    currDate: '2024-04-10',
    isTiff: false,
    description: 'New linear paved road/corridor crossing rural terrain with high aspect ratio.',
  },
  {
    id: 'pair_04_no_change',
    name: 'Sample 4: Stable Landscape (Seasonal Variation Only)',
    type: 'no_change',
    beforePath: '/sample_pairs/pair_04_no_change/before.png',
    afterPath: '/sample_pairs/pair_04_no_change/after.png',
    resolutionM: 0.5,
    histDate: '2023-04-15',
    currDate: '2023-10-15',
    isTiff: false,
    description: 'Subtle seasonal illumination and sun-angle shift with zero actual ground changes.',
  },
  {
    id: 'pair_05_sentinel2_geotiff',
    name: 'Sample 5: Sentinel-2 L2A Multispectral GeoTIFF Stack',
    type: 'sentinel2_geotiff',
    beforePath: '/sample_pairs/pair_05_sentinel2_geotiff/before.tif',
    afterPath: '/sample_pairs/pair_05_sentinel2_geotiff/after.tif',
    resolutionM: 10.0,
    histDate: '2023-02-18',
    currDate: '2024-01-25',
    isTiff: true,
    bbox: [80.32, 26.42, 80.36, 26.46],
    description: 'Georeferenced 4-band Sentinel-2 stack [B02, B03, B04, B08] (Kanpur, India) with full GIS zoning overlap.',
  },
]

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
    if (file && (file.type.startsWith('image/') || /\.png$/i.test(file.name) || /\.jpe?g$/i.test(file.name))) {
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
            <div className="relative max-h-40 max-w-full overflow-hidden rounded-xl border border-slate-700 bg-black/40">
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
              {(file.size / (1024 * 1024)).toFixed(2)} MB · {isTiff ? 'GeoTIFF raster' : file.type || 'Image raster'}
            </div>
          </div>

          <div className="flex items-center gap-2 mt-1">
            <Badge variant={isTiff ? 'success' : 'default'} size="sm">
              {isTiff ? 'Georeferenced GeoTIFF' : 'Standard Optical'}
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
          <span className="text-[11px] text-slate-500">Supports GeoTIFF (.tif, .tiff), PNG, JPEG</span>
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
  const { phase, step, error, activeInvestigation, executeUpload } = useInvestigationStore()

  const [beforeFile, setBeforeFile] = useState<File | undefined>()
  const [afterFile, setAfterFile] = useState<File | undefined>()
  const [histDate, setHistDate] = useState('2023-03-10')
  const [currDate, setCurrDate] = useState('2024-02-15')
  const [pixelSizeM, setPixelSizeM] = useState<number>(0.5)
  const [selectedPresetId, setSelectedPresetId] = useState<string>('')
  const [isLoadingPreset, setIsLoadingPreset] = useState(false)
  const [customBbox, setCustomBbox] = useState<[number, number, number, number] | undefined>()

  const isBeforeTiff = beforeFile ? /\.tiff?$/i.test(beforeFile.name) : false
  const isAfterTiff = afterFile ? /\.tiff?$/i.test(afterFile.name) : false
  const bothTiff = isBeforeTiff && isAfterTiff
  const hasFiles = !!beforeFile && !!afterFile

  async function handleSelectPreset(presetId: string) {
    if (!presetId) {
      setSelectedPresetId('')
      return
    }
    const preset = SAMPLE_PRESETS.find(p => p.id === presetId)
    if (!preset) return

    setSelectedPresetId(presetId)
    setIsLoadingPreset(true)

    try {
      // Fetch before image
      const bRes = await fetch(preset.beforePath)
      const bBlob = await bRes.blob()
      const bExt = preset.isTiff ? 'before.tif' : 'before.png'
      const bFile = new File([bBlob], bExt, { type: preset.isTiff ? 'image/tiff' : 'image/png' })

      // Fetch after image
      const aRes = await fetch(preset.afterPath)
      const aBlob = await aRes.blob()
      const aExt = preset.isTiff ? 'after.tif' : 'after.png'
      const aFile = new File([aBlob], aExt, { type: preset.isTiff ? 'image/tiff' : 'image/png' })

      setBeforeFile(bFile)
      setAfterFile(aFile)
      setHistDate(preset.histDate)
      setCurrDate(preset.currDate)
      setPixelSizeM(preset.resolutionM)
      setCustomBbox(preset.bbox)
    } catch (err) {
      console.error('Failed to load sample preset:', err)
    } finally {
      setIsLoadingPreset(false)
    }
  }

  async function handleAnalyze() {
    if (!beforeFile || !afterFile) return
    await executeUpload(beforeFile, afterFile, {
      historical_date: histDate,
      current_date: currDate,
      pixel_size_m: pixelSizeM,
      bbox: customBbox,
    })
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
              SatQuery Siamese U-Net AI
            </Badge>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-100 tracking-tight">
            Upload Before & After Imagery
          </h1>
          <p className="text-xs sm:text-sm text-slate-400 mt-1">
            Upload custom drone, aerial, or satellite rasters to run AI change segmentation and evidence synthesis.
          </p>
        </div>

        {/* SAMPLE PRESET PICKER */}
        <div className="flex items-center gap-2 bg-slate-900 border border-slate-800 rounded-xl p-2">
          <FolderOpen className="h-4 w-4 text-sky-400 shrink-0 ml-1" />
          <select
            value={selectedPresetId}
            onChange={e => handleSelectPreset(e.target.value)}
            disabled={isLoadingPreset || phase === 'loading'}
            aria-label="Load pre-built sample pair"
            className="bg-transparent text-xs text-slate-200 font-medium focus:outline-none cursor-pointer py-1 pr-3"
          >
            <option value="" className="bg-slate-900 text-slate-400">
              {isLoadingPreset ? 'Loading preset images...' : 'Load sample pair preset...'}
            </option>
            {SAMPLE_PRESETS.map(p => (
              <option key={p.id} value={p.id} className="bg-slate-900 text-slate-200">
                {p.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* SELECTED PRESET BANNER */}
      {selectedPresetId && (
        <div className="rounded-xl border border-sky-500/30 bg-sky-950/20 p-3.5 text-xs text-sky-200 flex items-start justify-between gap-3">
          <div className="flex items-start gap-2.5">
            <Info className="h-4 w-4 text-sky-400 shrink-0 mt-0.5" />
            <div>
              <span className="font-semibold text-sky-300">
                {SAMPLE_PRESETS.find(p => p.id === selectedPresetId)?.name}
              </span>
              <p className="text-slate-300 mt-0.5">
                {SAMPLE_PRESETS.find(p => p.id === selectedPresetId)?.description}
              </p>
            </div>
          </div>
          <button
            onClick={() => {
              setSelectedPresetId('')
              setBeforeFile(undefined)
              setAfterFile(undefined)
            }}
            className="text-slate-400 hover:text-slate-200 text-xs shrink-0"
          >
            Clear
          </button>
        </div>
      )}

      {/* GEOREFERENCING ALERT OR STATUS */}
      {hasFiles && (
        <>
          {bothTiff ? (
            <div className="rounded-xl border border-emerald-500/40 bg-emerald-950/20 p-4 text-xs sm:text-sm text-emerald-200 flex items-start gap-3">
              <CheckCircle2 className="h-5 w-5 text-emerald-400 shrink-0 mt-0.5" />
              <div>
                <b className="font-semibold text-emerald-300">
                  Georeferenced Metadata Detected (GeoTIFF)
                </b>
                <p className="mt-1 text-slate-300">
                  Embedded projection tags (EPSG) and affine transform found. Metric ground area (m²)
                  and sensitive zoning buffer overlaps will be accurately computed with statutory precision.
                </p>
              </div>
            </div>
          ) : (
            <div className="rounded-xl border border-amber-500/40 bg-amber-950/20 p-4 text-xs sm:text-sm text-amber-200 flex items-start gap-3">
              <AlertTriangle className="h-5 w-5 text-amber-400 shrink-0 mt-0.5" />
              <div>
                <b className="font-semibold text-amber-300">
                  Non-georeferenced Imagery Mode
                </b>
                <p className="mt-1 text-slate-300">
                  Standard optical images without CRS tags. Change segmentation and evidence synthesis will run smoothly.
                  Metric area is calculated using the configured pixel resolution ({pixelSizeM} m/px). GIS zoning overlap is marked N/A.
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

      {/* METADATA CONFIGURATION */}
      <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-4 sm:p-5 space-y-4">
        <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-slate-400">
          <Sliders className="h-4 w-4 text-sky-400" />
          <span>Image Pair Metadata & Resolution</span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1 flex items-center gap-1.5">
              <Calendar className="h-3.5 w-3.5 text-slate-400" />
              Baseline Date (T1)
            </label>
            <input
              type="date"
              value={histDate}
              onChange={e => setHistDate(e.target.value)}
              className="w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-xs text-slate-200 focus:border-sky-500 focus:outline-none"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1 flex items-center gap-1.5">
              <Calendar className="h-3.5 w-3.5 text-slate-400" />
              Comparison Date (T2)
            </label>
            <input
              type="date"
              value={currDate}
              onChange={e => setCurrDate(e.target.value)}
              className="w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-xs text-slate-200 focus:border-sky-500 focus:outline-none"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1 flex items-center gap-1.5">
              <Ruler className="h-3.5 w-3.5 text-slate-400" />
              Pixel Resolution (m / px)
            </label>
            <input
              type="number"
              step="0.1"
              min="0.1"
              max="100.0"
              disabled={bothTiff}
              value={pixelSizeM}
              onChange={e => setPixelSizeM(parseFloat(e.target.value) || 0.5)}
              className="w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-xs text-slate-200 disabled:opacity-50 focus:border-sky-500 focus:outline-none"
            />
            <span className="text-[10px] text-slate-500 mt-1 block">
              {bothTiff ? 'Derived automatically from GeoTIFF affine transform' : 'Default: 0.5m for aerial/drone, 10m for Sentinel-2'}
            </span>
          </div>
        </div>
      </div>

      {/* PIPELINE PROGRESS IF LOADING */}
      {phase === 'loading' && (
        <Card title="Processing AI Change Detection Pipeline">
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
              : 'Add both before and after images or load a sample preset above to continue.'}
          </div>
        </div>

        <button
          onClick={handleAnalyze}
          disabled={!hasFiles || phase === 'loading'}
          className="btn flex items-center justify-center gap-2 py-2.5 px-6 text-xs font-bold uppercase tracking-wider shadow-lg"
        >
          <Sparkles className="h-4 w-4" />
          {phase === 'loading' ? 'Running Model Inference…' : 'Detect Change'}
        </button>
      </div>

      {/* INLINE RESULTS VIEW IF DONE */}
      {phase === 'done' && activeInvestigation && (
        <div className="space-y-6 pt-6 border-t border-slate-800">
          <div className="flex items-center justify-between">
            <div>
              <span className="text-xs font-mono text-emerald-400 font-semibold uppercase tracking-wider">
                Inference Complete
              </span>
              <h2 className="text-xl font-bold text-slate-100">Detection & Evidence Results</h2>
            </div>
            <Badge variant="success" size="md">
              Analysis Complete
            </Badge>
          </div>

          <Results inv={activeInvestigation} />
        </div>
      )}
    </div>
  )
}
