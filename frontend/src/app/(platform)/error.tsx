"use client";

import {
  AlertTriangle,
  Home,
  RefreshCw,
} from "lucide-react";
import Link from "next/link";
import {
  useEffect,
} from "react";

type PlatformErrorProps = {
  error: Error & {
    digest?: string;
  };
  reset: () => void;
};

export default function PlatformError({
  error,
  reset,
}: PlatformErrorProps) {
  useEffect(() => {
    console.error(
      "Platform route error:",
      error,
    );
  }, [
    error,
  ]);

  return (
    <section className="mx-auto max-w-2xl rounded-2xl border border-rose-200 bg-white p-8 text-center shadow-sm sm:p-12">
      <span className="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl bg-rose-50 text-rose-600">
        <AlertTriangle
          size={30}
        />
      </span>

      <p className="mt-6 text-xs font-semibold uppercase tracking-[0.18em] text-rose-600">
        Platform error
      </p>

      <h1 className="mt-2 text-2xl font-bold tracking-tight text-slate-950">
        This page could not be loaded
      </h1>

      <p className="mx-auto mt-3 max-w-lg text-sm leading-6 text-slate-500">
        The request may have failed because the backend is unavailable,
        the network connection was interrupted, or an unexpected
        application error occurred.
      </p>

      {error.message ? (
        <div className="mt-6 rounded-xl border border-rose-100 bg-rose-50 px-4 py-3 text-left">
          <p className="text-xs font-semibold uppercase tracking-wide text-rose-700">
            Error information
          </p>

          <p className="mt-2 break-words text-sm text-rose-700">
            {error.message}
          </p>

          {error.digest ? (
            <p className="mt-2 font-mono text-xs text-rose-500">
              Reference: {error.digest}
            </p>
          ) : null}
        </div>
      ) : null}

      <div className="mt-7 flex flex-col justify-center gap-3 sm:flex-row">
        <button
          type="button"
          onClick={reset}
          className="inline-flex h-11 items-center justify-center gap-2 rounded-xl bg-cyan-500 px-5 text-sm font-semibold text-slate-950 hover:bg-cyan-400"
        >
          <RefreshCw
            size={17}
          />
          Try again
        </button>

        <Link
          href="/dashboard"
          className="inline-flex h-11 items-center justify-center gap-2 rounded-xl border border-slate-200 bg-white px-5 text-sm font-semibold text-slate-700 hover:bg-slate-50"
        >
          <Home
            size={17}
          />
          Return to dashboard
        </Link>
      </div>
    </section>
  );
}
