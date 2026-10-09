import { ShieldCheck } from 'lucide-react'

export function FooterBanner() {
  return (
    <footer
      className="hidden md:flex h-8 items-center justify-between border-t px-4 text-[11px] text-slate-400 select-none shrink-0"
      style={{ borderColor: 'var(--line)', background: 'var(--panel2)' }}
    >
      <div className="flex items-center gap-2">
        <ShieldCheck className="h-3.5 w-3.5 text-amber-400" />
        <span className="font-semibold text-slate-300">Statutory Notice:</span>
        <span>Automated analysis. Requires human verification. Not a legal determination.</span>
      </div>

      <div className="flex items-center gap-4 text-slate-500 font-mono">
        <span>CRS: EPSG:4326 / UTM Dynamic</span>
        <span>Resolution: 10m Ground Sample</span>
        <span>Version: 0.1.0</span>
      </div>
    </footer>
  )
}
