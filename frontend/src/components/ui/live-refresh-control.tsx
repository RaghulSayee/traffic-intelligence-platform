"use client";

import {
  Clock3,
  RefreshCw,
} from "lucide-react";

import {
  useLiveRefresh,
} from "@/hooks/use-live-refresh";

type LiveRefreshControlProps = {
  enabled?: boolean;
  intervalMs?: number;
};

export function LiveRefreshControl({
  enabled = true,
  intervalMs = 5000,
}: LiveRefreshControlProps) {
  const {
    refresh,
    isRefreshing,
    lastUpdatedLabel,
    isPageVisible,
  } = useLiveRefresh({
    enabled,
    intervalMs,
  });

  const intervalSeconds =
    Math.round(
      intervalMs / 1000,
    );

  return (
    <div className="flex flex-wrap items-center gap-3">
      <div className="hidden items-center gap-2 text-xs text-slate-500 md:flex">
        <Clock3 size={15} />

        <span>
          {lastUpdatedLabel
            ? `Updated ${lastUpdatedLabel}`
            : "Preparing live updates"}
        </span>

        <span className="text-slate-300">
          •
        </span>

        <span>
          {!enabled
            ? "Auto-refresh off"
            : isPageVisible
              ? `Every ${intervalSeconds}s`
              : "Paused"}
        </span>
      </div>

      <button
        type="button"
        onClick={refresh}
        disabled={isRefreshing}
        className="inline-flex h-11 items-center justify-center gap-2 rounded-xl border border-slate-200 bg-white px-4 text-sm font-semibold text-slate-700 hover:bg-slate-50 disabled:cursor-wait disabled:text-slate-400"
      >
        <RefreshCw
          size={17}
          className={
            isRefreshing
              ? "animate-spin"
              : ""
          }
        />

        Refresh
      </button>
    </div>
  );
}
