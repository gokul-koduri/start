"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { fetchAPI, getSourceColor } from "@/lib/api";
import { Filter } from "lucide-react";

interface Signal {
  id: number;
  signal_type: string;
  title: string;
  body_text: string;
  source_name: string;
  collected_at: string;
  entity_name: string;
  composite_score?: number;
}

export default function SignalsPage() {
  const [signals, setSignals] = useState<Signal[]>([]);
  const [filter, setFilter] = useState<string>("all");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const data = await fetchAPI<{ signals: Signal[] }>("/api/signals?limit=50");
        setSignals(data.signals || []);
      } catch {
        // graceful degradation
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  const filtered =
    filter === "all" ? signals : signals.filter((s) => s.source_name?.toLowerCase() === filter);

  const sources = [...new Set(signals.map((s) => s.source_name).filter(Boolean))];

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-6 h-6 border-2 border-accent-blue border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-semibold">Real-Time Signal Feed</h1>
        <div className="flex items-center gap-2">
          <Filter className="w-4 h-4 text-zinc-500" />
          <select
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            className="bg-surface-card border border-zinc-800 rounded-lg px-3 py-1.5 text-sm text-zinc-300 outline-none"
          >
            <option value="all">All Sources</option>
            {sources.map((s) => (
              <option key={s} value={s.toLowerCase()}>
                {s}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="space-y-2">
        {filtered.length > 0 ? (
          filtered.map((signal) => (
            <div
              key={signal.id}
              className="bg-surface-card border border-zinc-800 rounded-lg p-4 card-hover"
            >
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <span
                    className={`text-[10px] font-mono font-medium px-1.5 py-0.5 rounded ${getSourceColor(
                      signal.source_name || ""
                    )}`}
                  >
                    {signal.source_name}
                  </span>
                  <span className="text-[10px] text-zinc-600 font-mono">
                    {signal.signal_type}
                  </span>
                </div>
                <span className="text-[10px] text-zinc-600 font-mono">
                  {signal.collected_at?.split("T")[0]}
                </span>
              </div>
              <h3 className="text-sm font-medium text-zinc-200 mb-1">
                {signal.title}
              </h3>
              {signal.body_text && (
                <p className="text-xs text-zinc-500 line-clamp-2">
                  {signal.body_text.slice(0, 200)}
                </p>
              )}
              {signal.entity_name && (
                <Link
                  href={`/graph?q=${encodeURIComponent(signal.entity_name)}`}
                  className="text-xs text-accent-blue hover:underline mt-2 inline-block"
                >
                  View in Knowledge Graph →
                </Link>
              )}
            </div>
          ))
        ) : (
          <div className="text-center py-20 text-zinc-600 text-sm">
            No signals available. Start collecting data first.
          </div>
        )}
      </div>
    </div>
  );
}
