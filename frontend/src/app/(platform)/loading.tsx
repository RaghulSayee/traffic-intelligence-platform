import {
  LoaderCircle,
} from "lucide-react";

function StatisticSkeleton() {
  return (
    <article className="animate-pulse rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="h-11 w-11 rounded-xl bg-slate-100" />
      <div className="mt-5 h-4 w-28 rounded bg-slate-100" />
      <div className="mt-3 h-9 w-16 rounded bg-slate-100" />
      <div className="mt-3 h-3 w-36 rounded bg-slate-100" />
    </article>
  );
}

export default function PlatformLoading() {
  return (
    <div
      role="status"
      aria-live="polite"
    >
      <div className="mb-7 flex flex-col justify-between gap-5 sm:flex-row sm:items-end">
        <div className="animate-pulse">
          <div className="h-3 w-28 rounded bg-slate-200" />
          <div className="mt-3 h-9 w-72 max-w-full rounded bg-slate-200" />
          <div className="mt-3 h-4 w-[430px] max-w-full rounded bg-slate-200" />
        </div>

        <div className="flex items-center gap-2 text-sm font-medium text-cyan-700">
          <LoaderCircle
            size={18}
            className="animate-spin"
          />
          Loading platform data
        </div>
      </div>

      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {Array.from({
          length: 4,
        }).map((_, index) => (
          <StatisticSkeleton
            key={index}
          />
        ))}
      </section>

      <section className="mt-6 grid gap-6 xl:grid-cols-[1.35fr_1fr]">
        {Array.from({
          length: 2,
        }).map((_, sectionIndex) => (
          <article
            key={sectionIndex}
            className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm"
          >
            <div className="animate-pulse border-b border-slate-100 px-5 py-5">
              <div className="h-5 w-44 rounded bg-slate-100" />
              <div className="mt-2 h-3 w-64 rounded bg-slate-100" />
            </div>

            <div className="divide-y divide-slate-100">
              {Array.from({
                length: 4,
              }).map((_, rowIndex) => (
                <div
                  key={rowIndex}
                  className="animate-pulse px-5 py-5"
                >
                  <div className="flex items-center justify-between gap-4">
                    <div className="min-w-0 flex-1">
                      <div className="h-4 w-2/3 rounded bg-slate-100" />
                      <div className="mt-2 h-3 w-1/3 rounded bg-slate-100" />
                    </div>

                    <div className="h-7 w-20 rounded-full bg-slate-100" />
                  </div>

                  <div className="mt-4 h-2 rounded-full bg-slate-100" />
                </div>
              ))}
            </div>
          </article>
        ))}
      </section>

      <span className="sr-only">
        Loading traffic-intelligence platform data.
      </span>
    </div>
  );
}
