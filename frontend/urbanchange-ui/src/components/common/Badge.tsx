import React from 'react'

export type BadgeVariant = 'default' | 'success' | 'warning' | 'danger' | 'info' | 'purple'

interface BadgeProps {
  children: React.ReactNode
  variant?: BadgeVariant
  className?: string
  size?: 'sm' | 'md'
}

export function Badge({ children, variant = 'default', className = '', size = 'md' }: BadgeProps) {
  const variantStyles: Record<BadgeVariant, string> = {
    default: 'bg-slate-800/80 text-slate-300 border-slate-700',
    success: 'bg-emerald-950/60 text-emerald-400 border-emerald-800/50',
    warning: 'bg-amber-950/60 text-amber-400 border-amber-800/50',
    danger: 'bg-red-950/60 text-red-400 border-red-800/50',
    info: 'bg-sky-950/60 text-sky-400 border-sky-800/50',
    purple: 'bg-purple-950/60 text-purple-400 border-purple-800/50',
  }

  const sizeStyles = size === 'sm' ? 'px-2 py-0.5 text-[10px]' : 'px-2.5 py-1 text-xs'

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border font-mono font-medium tracking-wide transition-colors ${variantStyles[variant]} ${sizeStyles} ${className}`}
    >
      {children}
    </span>
  )
}
