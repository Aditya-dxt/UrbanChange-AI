export function Skeleton({ className = '' }: { className?: string }) {
  return (
    <div
      className={`animate-pulse rounded-lg bg-slate-800/60 ${className}`}
      style={{ background: 'color-mix(in srgb, var(--line) 40%, transparent)' }}
    />
  )
}

export function SkeletonCard() {
  return (
    <div className="card flex flex-col gap-3">
      <Skeleton className="h-6 w-1/3" />
      <Skeleton className="h-10 w-2/3" />
      <Skeleton className="h-4 w-full" />
      <Skeleton className="h-4 w-4/5" />
    </div>
  )
}
