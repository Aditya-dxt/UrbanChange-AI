import React from 'react'

interface CardProps extends Omit<React.HTMLAttributes<HTMLDivElement>, 'title'> {
  title?: React.ReactNode
  action?: React.ReactNode
  subtitle?: React.ReactNode
  variant?: 'default' | 'finding' | 'glass'
}

export function Card({
  title,
  action,
  subtitle,
  children,
  variant = 'default',
  className = '',
  ...props
}: CardProps) {
  const variantClass =
    variant === 'finding'
      ? 'card finding'
      : variant === 'glass'
      ? 'glass'
      : 'card'

  return (
    <div className={`${variantClass} ${className}`} {...props}>
      {(title || action || subtitle) && (
        <div className="mb-3 flex items-start justify-between border-b pb-2.5" style={{ borderColor: 'var(--line)' }}>
          <div>
            {title && <h3 className="display text-base font-bold text-slate-100">{title}</h3>}
            {subtitle && <p className="text-xs text-slate-400 mt-0.5">{subtitle}</p>}
          </div>
          {action && <div className="ml-4 shrink-0">{action}</div>}
        </div>
      )}
      {children}
    </div>
  )
}
