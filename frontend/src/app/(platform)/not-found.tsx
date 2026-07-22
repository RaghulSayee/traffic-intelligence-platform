import {
  ArrowLeft,
  LayoutDashboard,
  SearchX,
} from "lucide-react";
import Link from "next/link";

export default function PlatformNotFound() {
  return (
    <section className="mx-auto max-w-2xl rounded-2xl border border-slate-200 bg-white p-8 text-center shadow-sm sm:p-12">
      <span className="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl bg-slate-100 text-slate-500">
        <SearchX
          size={30}
        />
      </span>

      <p className="mt-6 text-xs font-semibold uppercase tracking-[0.18em] text-cyan-700">
        Error 404
      </p>

      <h1 className="mt-2 text-2xl font-bold tracking-tight text-slate-950">
        Page not found
      </h1>

      <p className="mx-auto mt-3 max-w-md text-sm leading-6 text-slate-500">
        The requested platform page does not exist, may have been
        deleted, or the link may no longer be valid.
      </p>

      <div className="mt-7 flex flex-col justify-center gap-3 sm:flex-row">
        <Link
          href="/dashboard"
          className="inline-flex h-11 items-center justify-center gap-2 rounded-xl bg-cyan-500 px-5 text-sm font-semibold text-slate-950 hover:bg-cyan-400"
        >
          <LayoutDashboard
            size={17}
          />
          Open dashboard
        </Link>

        <Link
          href="/videos"
          className="inline-flex h-11 items-center justify-center gap-2 rounded-xl border border-slate-200 bg-white px-5 text-sm font-semibold text-slate-700 hover:bg-slate-50"
        >
          <ArrowLeft
            size={17}
          />
          Open videos
        </Link>
      </div>
    </section>
  );
}
