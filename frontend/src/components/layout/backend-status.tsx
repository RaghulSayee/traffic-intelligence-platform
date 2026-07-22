"use client";

import { useEffect, useState } from "react";

import { createApiUrl } from "@/lib/api/client";

type ConnectionStatus =
  | "checking"
  | "connected"
  | "disconnected";

export function BackendStatus() {
  const [status, setStatus] =
    useState<ConnectionStatus>(
      "checking",
    );

  useEffect(() => {
    let active = true;

    async function checkBackend() {
      try {
        const response = await fetch(
          createApiUrl("/health"),
          {
            cache: "no-store",
            credentials: "include",
          },
        );

        if (active) {
          setStatus(
            response.ok
              ? "connected"
              : "disconnected",
          );
        }
      } catch {
        if (active) {
          setStatus("disconnected");
        }
      }
    }

    void checkBackend();

    const interval = window.setInterval(
      () => {
        void checkBackend();
      },
      30000,
    );

    return () => {
      active = false;
      window.clearInterval(interval);
    };
  }, []);

  const connected =
    status === "connected";

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
      <div className="mb-2 flex items-center gap-2">
        <span
          className={[
            "h-2.5 w-2.5 rounded-full",
            status === "checking"
              ? "bg-amber-400"
              : connected
                ? "bg-emerald-400"
                : "bg-rose-400",
          ].join(" ")}
        />

        <span className="text-sm font-medium text-white">
          {status === "checking"
            ? "Checking backend"
            : connected
              ? "Backend connected"
              : "Backend unavailable"}
        </span>
      </div>

      <p className="text-xs leading-5 text-slate-400">
        {connected
          ? "Traffic analysis API is responding."
          : "Start FastAPI on port 8000."}
      </p>
    </div>
  );
}
