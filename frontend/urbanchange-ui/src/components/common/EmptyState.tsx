import React from 'react'

interface EmptyStateProps {
  title: string
  description: string
  icon?: React.ReactNode
  action?: React.ReactNode
  actionLabel?: string
  onAction?: () => void
}

export function EmptyState({
  title,
  description,
  icon,
  action,
  actionLabel,
  onAction,
}: EmptyStateProps) {
  return (
    <div className="card flex flex-col items-center justify-center p-8 text-center sm:p-12">
      {icon && (
        <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl border border-slate-700/60 bg-slate-800/50 text-slate-300">
          {icon}
        </div>
      )}
      <h3 className="display text-lg font-bold text-slate-100">{title}</h3>
      <p className="mt-1.5 max-w-md text-sm text-slate-400 leading-relaxed">{description}</p>
      {action ? (
        <div className="mt-6">{action}</div>
      ) : actionLabel && onAction ? (
        <div className="mt-6">
          <button onClick={onAction} className="btn text-xs py-2 px-4 font-semibold">
            {actionLabel}
          </button>
        </div>
      ) : null}
    </div>
  )
}
