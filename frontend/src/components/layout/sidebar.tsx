"use client";

import { Activity } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { BackendStatus } from "./backend-status";
import { navigationItems } from "./navigation";

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="fixed inset-y-0 left-0 z-30 hidden w-72 flex-col border-r border-slate-800 bg-slate-950 text-white lg:flex">
      <div className="flex h-20 items-center border-b border-slate-800 px-6">
        <Link
          href="/dashboard"
          className="flex items-center gap-3"
        >
          <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-cyan-500 text-slate-950">
            <Activity
              size={24}
              strokeWidth={2.4}
            />
          </span>

          <span>
            <span className="block text-sm font-semibold tracking-wide text-white">
              Traffic Intelligence
            </span>

            <span className="block text-xs text-slate-400">
              Violation Monitoring
            </span>
          </span>
        </Link>
      </div>

      <nav className="flex-1 space-y-1 px-4 py-6">
        <p className="mb-3 px-3 text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
          Workspace
        </p>

        {navigationItems.map((item) => {
          const Icon = item.icon;

          const isActive = item.exact
            ? pathname === item.href
            : pathname === item.href ||
              pathname.startsWith(
                `${item.href}/`,
              );

          return (
            <Link
              key={item.href}
              href={item.href}
              className={[
                "flex items-center gap-3 rounded-xl px-3 py-3 text-sm font-medium transition-colors",
                isActive
                  ? "bg-cyan-500 text-slate-950"
                  : "text-slate-300 hover:bg-slate-900 hover:text-white",
              ].join(" ")}
            >
              <Icon size={19} />
              <span>{item.label}</span>
            </Link>
          );
        })}
      </nav>

      <div className="border-t border-slate-800 p-4">
        <BackendStatus />
      </div>
    </aside>
  );
}
