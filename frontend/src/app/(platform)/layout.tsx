import type {
  ReactNode,
} from "react";

import {
  MobileNavigation,
} from "@/components/layout/mobile-navigation";
import {
  Sidebar,
} from "@/components/layout/sidebar";
import {
  TopBar,
} from "@/components/layout/top-bar";
import {
  requireCurrentUser,
} from "@/lib/auth/server";

type PlatformLayoutProps = {
  children: ReactNode;
};

export default async function PlatformLayout({
  children,
}: PlatformLayoutProps) {
  const user =
    await requireCurrentUser();

  return (
    <div className="min-h-screen overflow-x-hidden bg-slate-50 text-slate-950">
      <Sidebar />

      <div className="min-h-screen min-w-0 lg:pl-72">
        <TopBar user={user} />
        <MobileNavigation />

        <main className="min-w-0 px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
          {children}
        </main>
      </div>
    </div>
  );
}
