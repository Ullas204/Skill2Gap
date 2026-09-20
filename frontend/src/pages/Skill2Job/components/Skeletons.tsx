export function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`animate-pulse rounded-lg bg-gray-200 ${className}`} />;
}

export function CardSkeleton({ lines = 3 }: { lines?: number }) {
  return (
    <div className="rounded-2xl border border-gray-200 bg-white p-6 space-y-3">
      <Skeleton className="h-5 w-1/3" />
      {Array.from({ length: lines }).map((_, i) => (
        <Skeleton key={i} className="h-4 w-full" />
      ))}
    </div>
  );
}

export function ReadinessSkeleton() {
  return (
    <div className="rounded-2xl border border-gray-200 bg-white p-6">
      <Skeleton className="h-5 w-40 mb-4" />
      <div className="flex items-center gap-6">
        <Skeleton className="h-[130px] w-[130px] rounded-full" />
        <div className="grid grid-cols-2 gap-4 flex-1">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-16 rounded-xl" />
          ))}
        </div>
      </div>
    </div>
  );
}

export function JobCardSkeleton() {
  return (
    <div className="rounded-2xl border border-gray-200 bg-white p-5 space-y-3">
      <div className="flex justify-between">
        <div className="space-y-2">
          <Skeleton className="h-5 w-40" />
          <Skeleton className="h-3 w-28" />
        </div>
        <Skeleton className="h-8 w-12" />
      </div>
      <Skeleton className="h-2 w-full rounded-full" />
      <div className="flex gap-2">
        <Skeleton className="h-5 w-16 rounded-full" />
        <Skeleton className="h-5 w-16 rounded-full" />
        <Skeleton className="h-5 w-16 rounded-full" />
      </div>
    </div>
  );
}
