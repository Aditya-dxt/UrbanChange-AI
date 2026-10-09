import { useEffect } from 'react'

interface ToastProps {
  message: string
  type?: 'success' | 'info' | 'warning' | 'error'
  onClose: () => void
  duration?: number
}

export function Toast({ message, type = 'info', onClose, duration = 4000 }: ToastProps) {
  useEffect(() => {
    const timer = setTimeout(onClose, duration)
    return () => clearTimeout(timer)
  }, [onClose, duration])

  const colors = {
    success: 'border-emerald-500/50 bg-emerald-950/90 text-emerald-200',
    info: 'border-sky-500/50 bg-sky-950/90 text-sky-200',
    warning: 'border-amber-500/50 bg-amber-950/90 text-amber-200',
    error: 'border-red-500/50 bg-red-950/90 text-red-200',
  }

  return (
    <div
      className={`fixed bottom-12 right-6 z-[3000] flex items-center gap-3 rounded-xl border p-3.5 shadow-2xl backdrop-blur-md text-sm ${colors[type]}`}
    >
      <span>{message}</span>
      <button onClick={onClose} className="opacity-70 hover:opacity-100 font-bold ml-2">
        ✕
      </button>
    </div>
  )
}
