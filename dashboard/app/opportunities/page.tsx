"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  fetchAPI,
  formatNumber,
  formatScore,
  getScoreColor,
  getScoreBg,
} from "@/lib/api";
import { ArrowUpDown, TrendingUp, TrendingDown, Minus } from "lucide-react";

interface Opportunity {
  id: number;
  entity_name: string;
  composite_score: number;
  trend_direction: string;
  signal_count?: number;
  top_signals?: string[];
  sector?: string;
  region?: string;
  last_updated?: string;
}

type SortKey = "composite_score" | "signal_count" | "entity_name";
type SortDir = "asc" | "desc";

export default function OpportunitiesPage() {
  const [opportunities, setOpportunities] = useState<Opportunity[]>([]);
  const [loading, setLoading] = useState(true);
  const [sortKey, setSortKey] = useState<SortKey>("composite_score");
  const [sortDir, setSortDir] = useState<SortDir>("desc");
  const [scoreFilter, setScoreFilter] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState("");

  useEffect(() => {
    async function load() {
      try {
        const data = await fetchAPI<{ opportunities: Opportunity[] }>(
          "/api/opportunities?limit=100"
        );
        setOpportunities(data.opportunities || []);
      } catch {
        // graceful degradation
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  function toggleSort(key: SortKey) {
    if (sortKey === key) {
      setSortDir((d) => (d === "desc" ? "asc" : "desc"));
    } else {
      setSortKey(key);
      setSortDir("desc");
    }
  }

  const filtered = opportunities
    .filter((o) => {
      if (scoreFilter === "high") return o.composite_score >= 80;
      if (scoreFilter === "medium") return o.composite_score >= 60 && o.composite_score < 80;
      if (scoreFilter === "low") return o.composite_score < 60;
      return true;
    })
    .filter((o) => {
      if (!searchQuery) return true;
      return o.entity_name?.toLowerCase().includes(searchQuery.toLowerCase());
    })
    .sort((a, b) => {
      const aVal = a[sortKey] ?? 0;
      const bVal = b[sortKey] ?? 0;
      if (typeof aVal === "string" && typeof bVal === "string") {
        return sortDir === "asc"
          ? aVal.localeCompare(bVal)
          : bVal.localeCompare(aVal);
      }
      return sortDir === "asc"
        ? (aVal as number) - (bVal as number)
        : (bVal as number) - (aVal as number);
    });

  const avgScore =
    opportunities.length > 0
      ? opportunities.reduce((s, o) => s + (o.composite_score || 0), 0) /
        opportunities.length
      : 0;

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-6 h-6 border-2 border-accent-blue border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold">Opportunities</h1>
          <p className="text-xs text-zinc-500 mt-0.5">
            {opportunities.length} scored entities &middot; avg score{" "}
            <span className={getScoreColor(avgScore)}>
              {formatScore(avgScore)}
            </span>
          </p>
        </div>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3">
        <input
          type="text"
          placeholder="Filter by name..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="bg-surface-card border border-zinc-800 rounded-lg px-3 py-1.5 text-sm text-zinc-200 placeholder-zinc-600 outline-none flex-1 max-w-xs"
        />
        <div className="flex items-center gap-1 bg-surface-card border border-zinc-800 rounded-lg p-1">
          {(
            [
              { key: "all", label: "All" },
              { key: "high", label: "80+" },
              { key: "medium", label: "60-79" },
              { key: "low", label: "<60" },
            ] as const
          ).map((f) => (
            <button
              key={f.key}
              onClick={() => setScoreFilter(f.key)}
              className={`px-2.5 py-1 rounded-md text-xs font-medium transition-colors ${
                scoreFilter === f.key
                  ? "bg-accent-blue/20 text-accent-blue"
                  : "text-zinc-500 hover:text-zinc-300"
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>
      </div>

      {/* Sort Controls */}
      <div className="flex items-center gap-2 text-xs text-zinc-500">
        <span>Sort by:</span>
        {(
          [
            { key: "composite_score", label: "Score" },
            { key: "signal_count", label: "Signals" },
            { key: "entity_name", label: "Name" },
          ] as const
        ).map((s) => (
          <button
            key={s.key}
            onClick={() => toggleSort(s.key)}
            className={`flex items-center gap-1 px-2 py-1 rounded-md transition-colors ${
              sortKey === s.key
                ? "text-zinc-200 bg-zinc-800"
                : "hover:text-zinc-300"
            }`}
          >
            {s.label}
            {sortKey === s.key && (
              <ArrowUpDown className="w-3 h-3" />
            )}
          </button>
        ))}
        <span className="text-zinc-600">
          {sortDir === "desc" ? "↓ high first" : "↑ low first"}
        </span>
      </div>

      {/* Opportunity Grid */}
      <div className="space-y-2">
        {filtered.length > 0 ? (
          filtered.map((opp) => (
            <Link
              key={opp.id}
              href={`/opportunities/${opp.id}`}
              className="flex items-center gap-4 py-3 px-4 rounded-lg bg-surface-card border border-zinc-800 card-hover group"
            >
              {/* Score Ring */}
              <div
                className={`flex items-center justify-center w-12 h-12 rounded-lg border shrink-0 ${getScoreBg(
                  opp.composite_score
                )}`}
              >
                <span
                  className={`text-lg font-bold font-mono ${getScoreColor(
                    opp.composite_score
                  )}`}
                >
                  {formatScore(opp.composite_score)}
                </span>
              </div>

              {/* Info */}
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-zinc-200 group-hover:text-accent-blue transition-colors truncate">
                  {opp.entity_name}
                </p>
                <div className="flex items-center gap-2 mt-0.5">
                  {opp.sector && (
                    <span className="text-[10px] text-zinc-600 font-mono">
                      {opp.sector}
                    </span>
                  )}
                  {opp.region && (
                    <span className="text-[10px] text-zinc-700">·</span>
                  )}
                  {opp.region && (
                    <span className="text-[10px] text-zinc-600 font-mono">
                      {opp.region}
                    </span>
                  )}
                </div>
              </div>

              {/* Signal Count */}
              <div className="text-right shrink-0">
                <p className="text-sm font-mono text-zinc-400">
                  {opp.signal_count || 0}
                </p>
                <p className="text-[10px] text-zinc-600">signals</p>
              </div>

              {/* Trend */}
              <div className="w-6 shrink-0 flex justify-center">
                {opp.trend_direction === "up" && (
                  <TrendingUp className="w-4 h-4 text-accent-green" />
                )}
                {opp.trend_direction === "down" && (
                  <TrendingDown className="w-4 h-4 text-accent-red" />
                )}
                {opp.trend_direction === "stable" && (
                  <Minus className="w-4 h-4 text-zinc-500" />
                )}
              </div>
            </Link>
          ))
        ) : (
          <div className="text-center py-20 text-zinc-600 text-sm">
            {opportunities.length === 0
              ? "No opportunities scored yet. Run the analysis pipeline."
              : "No results match your filters."}
          </div>
        )}
      </div>
    </div>
  );
}
