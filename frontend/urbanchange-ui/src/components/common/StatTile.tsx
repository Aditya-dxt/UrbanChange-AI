import React from 'react'

interface StatTileProps {
  label: string
  value: React.ReactNode
  unit?: string
  subtext?: React.ReactNode
  subValue?: React.ReactNode
  icon?: React.ReactNode
  trend?: 'up' | 'down' | 'neutral'
  variant?: 'default' | 'hot' | 'ok' | 'bad' | 'info' | 'success' | 'warning' | 'danger'
}

export function StatTile({
  label,
  value,
  unit,
  subtext,
  subValue,
  icon,
  variant = 'default',
}: StatTileProps) {
  const borderColors: Record<string, string> = {
    default: 'var(--line)',
    hot: 'var(--hot)',
    warning: 'var(--hot)',
    ok: 'var(--ok)',
    success: 'var(--ok)',
    bad: 'var(--bad)',
    danger: 'var(--bad)',
    info: 'var(--acc)',
  }

  const helper = subValue ?? subtext

  return (
    <div
      className="card flex flex-col justify-between p-4 transition-all hover:border-slate-600"
      style={{ borderLeftWidth: '3px', borderLeftColor: borderColors[variant] || 'var(--line)' }}
    >
      <div className="flex items-center justify-between text-xs font-semibold uppercase tracking-wider text-slate-400">
        <span>{label}</span>
        {icon && <span className="text-slate-400">{icon}</span>}
      </div>

      <div className="my-2 flex items-baseline gap-1.5">
        <span className="display text-3xl font-bold tracking-tight tabular-nums text-slate-100">
          {value}
        </span>
        {unit && <span className="text-sm font-medium text-slate-400">{unit}</span>}
      </div>

      {helper && <div className="text-xs text-slate-400">{helper}</div>}
    </div>
  )
}
