"use client";

import Link from "next/link";
import {
  usePathname,
} from "next/navigation";

import {
  navigationItems,
} from "./navigation";

export function MobileNavigation() {
  const pathname =
    usePathname();

  return (
    <nav
      aria-label="Mobile navigation"
      className="sticky top-16 z-10 overflow-x-auto border-b border-slate-200 bg-white/95 px-3 py-2 backdrop-blur sm:top-20 sm:px-4 lg:hidden [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
    >
      <div className="flex min-w-max snap-x snap-mandatory gap-2">
        {navigationItems.map(
          (item) => {
            const Icon =
              item.icon;

            const isActive =
              item.exact
                ? pathname ===
                  item.href
                : pathname ===
                    item.href ||
                  pathname.startsWith(
                    `${item.href}/`,
                  );

            return (
              <Link
                key={item.href}
                href={item.href}
                aria-current={
                  isActive
                    ? "page"
                    : undefined
                }
                className={[
                  "flex snap-start items-center gap-2 whitespace-nowrap rounded-xl border px-3 py-2 text-xs font-semibold transition-colors sm:text-sm",
                  isActive
                    ? "border-slate-950 bg-slate-950 text-white shadow-sm"
                    : "border-slate-200 bg-white text-slate-600 hover:border-cyan-300 hover:bg-cyan-50 hover:text-cyan-800",
                ].join(" ")}
              >
                <Icon
                  size={16}
                  className="shrink-0"
                />

                <span>
                  {item.label}
                </span>
              </Link>
            );
          },
        )}
      </div>
    </nav>
  );
}
