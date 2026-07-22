import {
  LayoutDashboard,
  SearchX,
} from "lucide-react";
import Link from "next/link";

export default function RootNotFound() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-50 px-4 py-12">
      <section className="w-full max-w-xl rounded-2xl border border-slate-200 bg-white p-8 text-center shadow-sm sm:p-12">
        <span className="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl bg-slate-100 text-slate-500">
          <SearchX
            size={30}
          />
        </span>

        <p className="mt-6 text-xs font-semibold uppercase tracking-[0.18em] text-cyan-700">
          Error 404
        </p>

        <h1 className="mt-2 text-2xl font-bold text-slate-950">
          Page not found
        </h1>

        <p className="mt-3 text-sm leading-6 text-slate-500">
          The requested address does not match an available page.
        </p>

        <Link
          href="/dashboard"
          className="mt-7 inline-flex h-11 items-center justify-center gap-2 rounded-xl bg-cyan-500 px-5 text-sm font-semibold text-slate-950 hover:bg-cyan-400"
        >
          <LayoutDashboard
            size={17}
          />
          Open dashboard
        </Link>
      </section>
    </main>
  );
}
