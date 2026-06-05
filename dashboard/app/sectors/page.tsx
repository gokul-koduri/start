"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { fetchAPI, formatNumber, formatScore, getScoreColor } from "@/lib/api";
import { Flame, Snowflake, Zap } from "lucide-react";

interface SectorData {
  sector: string;
  count: number;
  avg_score: number;
  top_company?: string;
  trend?: string;
}

interface Opportunity {
  id: number;
  entity_name: string;
  composite_score: number;
  trend_direction: string;
  signal_count?: number;
}

export default function SectorsPage() {
  const [sectors, setSectors] = useState<SectorData[]>([]);
  const [selectedSector, setSelectedSector] = useState<string | null>(null);
  const [opportunities, setOpportunities] = useState<Opportunity[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const allOpp = await fetchAPI<{ opportunities: Opportunity[] }>(
          "/api/opportunities?limit=200"
        );
        const opps = allOpp.opportunities || [];

        // Group by sector
        const sectorMap = new Map<string, { count: number; totalScore: number; top: Opportunity }>();

        opps.forEach((o) => {
          const sector = o.sector || "Unknown";
          const existing = sectorMap.get(sector) || {
            count: 0,
            totalScore: 0,
            top: o,
          };
          existing.count++;
          existing.totalScore += o.composite_score || 0;
          if ((o.composite_score || 0) > (existing.top.composite_score || 0)) {
            existing.top = o;
          }
          sectorMap.set(sector, existing);
        });

        const sectorData: SectorData[] = Array.from(sectorMap.entries())
          .map(([sector, data]) => ({
            sector,
            count: data.count,
            avg_score: data.count > 0 ? data.totalScore / data.count : 0,
            top_company: data.top?.entity_name,
            trend:
              data.count > 5 ? "hot" : data.count > 2 ? "warm" : "emerging",
          }))
          .sort((a, b) => b.avg_score - a.avg_score);

        setSectors(sectorData);
      } catch {
        // graceful degradation
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  // Filter opportunities when a sector is selected
  useEffect(() => {
    if (!selectedSector) {
      setOpportunities([]);
      return;
    }
    async function load() {
      try {
        const data = await fetchAPI<{ opportunities: Opportunity[] }>(
          `/api/opportunities?limit=50`
        );
        setOpportunities(
          (data.opportunities || []).filter(
            (o) => (o.sector || "Unknown") === selectedSector
          )
        );
      } catch {
        // graceful degradation
      }
    }
    load();
  }, [selectedSector]);

  const maxCount = Math.max(...sectors.map((s) => s.count), 1);

  function getHeatColor(avgScore: number): string {
    if (avgScore >= 75) return "bg-red-500/15 border-red-500/25 text-red-400";
    if (avgScore >= 55) return "bg-amber-500/12 border-amber-500/20 text-amber-400";
    if (avgScore >= 35) return "bg-blue-500/10 border-blue-500/20 text-blue-400";
    return "bg-zinc-800 border-zinc-700 text-zinc-500";
  }

  function getTrendIcon(trend?: string) {
    if (trend === "hot") return <Flame className="w-3 h-3" />;
    if (trend === "warm") return <Zap className="w-3 h-3" />;
    return <Snowflake className="w-3 h-3" />;
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-6 h-6 border-2 border-accent-blue border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-lg font-semibold">Sectors</h1>
        <p className="text-xs text-zinc-500 mt-0.5">
          {sectors.length} sectors analyzed &middot; heat by composite score
        </p>
      </div>

      {/* Sector Treemap */}
      <div>
        <h2 className="text-sm font-medium text-zinc-400 mb-3">
          Sector Heat Map
        </h2>
        {sectors.length > 0 ? (
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3">
            {sectors.map((sector) => (
              <button
                key={sector.sector}
                onClick={() =>
                  setSelectedSector(
                    selectedSector === sector.sector ? null : sector.sector
                  )
                }
                className={`rounded-lg border p-4 text-left transition-all hover:scale-[1.02] ${
                  selectedSector === sector.sector
                    ? "ring-2 ring-accent-blue ring-offset-1 ring-offset-surface-secondary"
                    : ""
                } ${getHeatColor(sector.avg_score)}`}
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="text-[10px] uppercase tracking-wider opacity-60">
                    {sector.trend}
                  </span>
                  {getTrendIcon(sector.trend)}
                </div>
                <p className="text-sm font-medium truncate">{sector.sector}</p>
                <p className="text-lg font-bold font-mono mt-1">
                  {formatScore(sector.avg_score)}
                </p>
                <p className="text-[10px] opacity-60 mt-1">
                  {sector.count} {sector.count === 1 ? "company" : "companies"}
                </p>
              </button>
            ))}
          </div>
        ) : (
          <div className="text-center py-20 text-zinc-600 text-sm">
            No sector data available. Score some opportunities first.
          </div>
        )}
      </div>

      {/* Score Distribution Bar */}
      <div className="bg-surface-card border border-zinc-800 rounded-lg p-5">
        <h2 className="text-sm font-medium text-zinc-400 mb-4">
          Score Distribution
        </h2>
        <div className="space-y-2">
          {sectors.slice(0, 8).map((sector) => (
            <div key={sector.sector} className="flex items-center gap-3">
              <span className="text-xs text-zinc-500 w-24 truncate font-mono">
                {sector.sector}
              </span>
              <div className="flex-1 h-3 bg-zinc-800 rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all ${
                    sector.avg_score >= 75
                      ? "bg-red-500/60"
                      : sector.avg_score >= 55
                      ? "bg-amber-500/60"
                      : "bg-blue-500/40"
                  }`}
                  style={{
                    width: `${(sector.avg_score / 100) * 100}%`,
                  }}
                />
              </div>
              <span
                className={`text-xs font-mono w-10 text-right ${getScoreColor(
                  sector.avg_score
                )}`}
              >
                {formatScore(sector.avg_score)}
              </span>
              <span className="text-[10px] text-zinc-600 w-16 text-right font-mono">
                {sector.count} opp
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Selected Sector Drill-Down */}
      {selectedSector && (
        <div>
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-medium text-zinc-400">
              Companies in{" "}
              <span className="text-accent-blue">{selectedSector}</span>
            </h2>
            <button
              onClick={() => setSelectedSector(null)}
              className="text-[10px] text-zinc-600 hover:text-zinc-400 transition-colors"
            >
              Clear selection
            </button>
          </div>
          <div className="space-y-2">
            {opportunities.length > 0 ? (
              opportunities.map((o) => (
                <Link
                  key={o.id}
                  href={`/opportunities/${o.id}`}
                  className="flex items-center gap-4 py-3 px-4 rounded-lg bg-surface-card border border-zinc-800 card-hover group"
                >
                  <span
                    className={`text-lg font-bold font-mono ${getScoreColor(
                      o.composite_score
                    )}`}
                  >
                    {formatScore(o.composite_score)}
                  </span>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-zinc-200 group-hover:text-accent-blue transition-colors truncate">
                      {o.entity_name}
                    </p>
                    <p className="text-xs text-zinc-600">
                      {o.signal_count || 0} signals
                    </p>
                  </div>
                  <div className="flex items-center gap-1 text-xs text-zinc-500">
                    {o.trend_direction === "up" && (
                      <span className="text-accent-green">▲</span>
                    )}
                    {o.trend_direction === "down" && (
                      <span className="text-accent-red">▼</span>
                    )}
                    {o.trend_direction === "stable" && (
                      <span className="text-zinc-500">→</span>
                    )}
                  </div>
                </Link>
              ))
            ) : (
              <div className="text-center py-12 text-zinc-600 text-sm">
                No companies found in this sector.
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
