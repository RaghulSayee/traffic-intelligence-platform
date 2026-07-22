import {
  BarChart3,
  LayoutDashboard,
  ListChecks,
  ShieldAlert,
  Upload,
  Video,
  type LucideIcon,
  Camera,
} from "lucide-react";

export type NavigationItem = {
  label: string;
  href: string;
  icon: LucideIcon;
  exact?: boolean;
};

export const navigationItems: NavigationItem[] = [
  {
    label: "Dashboard",
    href: "/dashboard",
    icon: LayoutDashboard,
    exact: true,
  },
  {
    label: "Upload Video",
    href: "/videos/upload",
    icon: Upload,
    exact: true,
  },
  {
    label: "Videos",
    href: "/videos",
    icon: Video,
    exact: true,
  },
  {
    label: "Processing Jobs",
    href: "/jobs",
    icon: ListChecks,
    exact: true,
  },

  {
    label: "Cameras",
    href: "/cameras",
    icon: Camera,
  },
  {
    label: "Violations",
    href: "/violations",
    icon: ShieldAlert,
    exact: true,
  },
  {
    label: "Analytics",
    href: "/analytics",
    icon: BarChart3,
    exact: true,
  },
];
