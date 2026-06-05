"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Radar,
  Activity,
  GitFork,
  Search,
  LayoutGrid,
  TrendingUp,
  Settings,
  Zap,
} from "lucide-react";

const nav = [
  { href: "/radar", label: "Radar", icon: Radar },
  { href: "/signals", label: "Signals", icon: Activity },
  { href: "/graph", label: "Graph", icon: GitFork },
  { href: "/opportunities", label: "Opportunities", icon: TrendingUp },
  { href: "/sectors", label: "Sectors", icon: LayoutGrid },
  { href: "/search", label: "Search", icon: Search },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="hidden md:flex flex-col w-56 border-r border-zinc-800 bg-surface-secondary h-screen sticky top-0">
      <div className="p-5 flex items-center gap-2 border-b border-zinc-800">
        <Zap className="w-5 h-5 text-accent-blue" />
        <span className="font-semibold text-sm tracking-tight">
          Opportunity Intelligence
        </span>
      </div>
      <nav className="flex-1 p-3 space-y-1">
        {nav.map((item) => {
          const isActive =
            pathname === item.href ||
            (item.href !== "/radar" && pathname.startsWith(item.href));
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`
                flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium
                transition-colors duration-150
                ${
                  isActive
                    ? "bg-accent-blue/10 text-accent-blue"
                    : "text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800/50"
                }
              `}
            >
              <item.icon className="w-4 h-4" />
              {item.label}
            </Link>
          );
        })}
      </nav>
      <div className="p-3 border-t border-zinc-800">
        <Link
          href="/radar"
          className="flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800/50 transition-colors"
        >
          <Settings className="w-4 h-4" />
          Settings
        </Link>
      </div>
    </aside>
  );
}
