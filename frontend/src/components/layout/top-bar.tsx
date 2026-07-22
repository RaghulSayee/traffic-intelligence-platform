"use client";

import {
  LoaderCircle,
  LogOut,
} from "lucide-react";
import {
  usePathname,
  useRouter,
} from "next/navigation";
import {
  useTransition,
} from "react";

import type {
  AuthUser,
} from "@/lib/auth/types";

const pageTitles = [
  {
    path: "/videos/upload",
    title: "Upload Video",
    description:
      "Submit traffic footage for automated analysis.",
  },
  {
    path: "/videos",
    title: "Videos",
    description:
      "Manage uploaded traffic footage.",
  },
  {
    path: "/jobs",
    title: "Processing Jobs",
    description:
      "Track video-analysis progress and results.",
  },
  {
    path: "/cameras",
    title: "Cameras",
    description:
      "Manage traffic cameras and scene configurations.",
  },
  {
    path: "/violations",
    title: "Violations",
    description:
      "Review detected traffic-rule violations.",
  },
  {
    path: "/analytics",
    title: "Analytics",
    description:
      "Explore traffic and violation trends.",
  },
  {
    path: "/dashboard",
    title: "Dashboard",
    description:
      "Monitor your traffic-intelligence platform.",
  },
];

type TopBarProps = {
  user: AuthUser;
};

function getInitials(
  fullName: string,
): string {
  return fullName
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) =>
      part.charAt(0),
    )
    .join("")
    .toUpperCase();
}

export function TopBar({
  user,
}: TopBarProps) {
  const pathname =
    usePathname();

  const router =
    useRouter();

  const [
    isLoggingOut,
    startLogout,
  ] = useTransition();

  const currentPage =
    pageTitles.find(
      (page) =>
        pathname === page.path ||
        pathname.startsWith(
          `${page.path}/`,
        ),
    ) ??
    pageTitles[
      pageTitles.length - 1
    ];

  function handleLogout() {
    startLogout(async () => {
      try {
        await fetch(
          "/api/auth/logout",
          {
            method: "POST",
          },
        );
      } finally {
        router.replace(
          "/login",
        );

        router.refresh();
      }
    });
  }

  return (
    <header className="sticky top-0 z-20 flex h-16 items-center justify-between gap-3 border-b border-slate-200 bg-white/95 px-4 backdrop-blur sm:h-20 sm:px-6 lg:px-8">
      <div className="min-w-0 flex-1">
        <h1 className="truncate text-lg font-bold tracking-tight text-slate-950 sm:text-2xl">
          {currentPage.title}
        </h1>

        <p className="mt-1 hidden truncate text-sm text-slate-500 sm:block">
          {currentPage.description}
        </p>
      </div>

      <div className="flex shrink-0 items-center gap-2 sm:gap-3">
        <div className="hidden text-right md:block">
          <p className="max-w-48 truncate text-sm font-semibold text-slate-800">
            {user.full_name}
          </p>

          <p className="text-xs capitalize text-slate-400">
            {user.role}
          </p>
        </div>

        <div
          aria-label={`Signed in as ${user.full_name}`}
          className="flex h-9 w-9 items-center justify-center rounded-xl bg-slate-950 text-xs font-semibold text-white sm:h-10 sm:w-10 sm:text-sm"
        >
          {getInitials(
            user.full_name,
          )}
        </div>

        <button
          type="button"
          onClick={handleLogout}
          disabled={isLoggingOut}
          aria-label="Sign out"
          title="Sign out"
          className="flex h-9 w-9 items-center justify-center rounded-xl border border-slate-200 bg-white text-slate-600 hover:border-rose-200 hover:bg-rose-50 hover:text-rose-700 disabled:cursor-wait disabled:opacity-50 sm:h-10 sm:w-10"
        >
          {isLoggingOut ? (
            <LoaderCircle
              size={18}
              className="animate-spin"
            />
          ) : (
            <LogOut size={18} />
          )}
        </button>
      </div>
    </header>
  );
}
