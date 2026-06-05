"use client";

import { useState, useEffect } from "react";
import { Search, Moon, Sun, Wifi } from "lucide-react";

export function Header() {
  const [live, setLive] = useState(false);

  useEffect(() => {
    // Check if backend is reachable
    const check = async () => {
      try {
        const res = await fetch(
          `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/stats/summary`,
          { signal: AbortSignal.timeout(3000) }
        );
        setLive(res.ok);
      } catch {
        setLive(false);
      }
    };
    check();
    const interval = setInterval(check, 30000);
    return () => clearInterval(interval);
  }, []);

  return (
    <header className="h-14 border-b border-zinc-800 bg-surface-secondary/80 backdrop-blur-sm flex items-center justify-between px-6 sticky top-0 z-10">
      {/* Search */}
      <div className="flex items-center gap-2 bg-surface-card rounded-lg px-3 py-1.5 border border-zinc-800 flex-1 max-w-md">
        <Search className="w-4 h-4 text-zinc-500" />
        <input
          type="text"
          placeholder="Search signals, companies, technologies..."
          className="bg-transparent text-sm text-zinc-200 placeholder-zinc-500 outline-none w-full"
          onKeyDown={(e) => {
            if (e.key === "Enter" && e.currentTarget.value) {
              window.location.href = `/search?q=${encodeURIComponent(e.currentTarget.value)}`;
            }
          }}
        />
      </div>

      {/* Right side */}
      <div className="flex items-center gap-4">
        {/* Live indicator */}
        <div className="flex items-center gap-2 text-xs">
          <span
            className={`w-2 h-2 rounded-full ${live ? "bg-accent-green live-dot" : "bg-zinc-600"}`}
          />
          <span className={live ? "text-zinc-300" : "text-zinc-600"}>
            {live ? "Live" : "Offline"}
          </span>
        </div>

        {/* Connection */}
        {live && (
          <Wifi className="w-4 h-4 text-accent-green" />
        )}
      </div>
    </header>
  );
}
