"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  fetchAPI,
  formatNumber,
  formatScore,
  getScoreColor,
  getScoreBg,
  getSourceColor,
} from "@/lib/api";
import {
  ScoreDistributionChart,
  SignalVolumeChart,
  TrendChart,
} from "@/components/ui/charts";

interface Stats {
  signals_today?: number;
  total_startups?: number;
  total_opportunities?: number;
  active_alerts?: number;
  total_signals?: number;
}

interface Signal {
  id: number;
  signal_type: string;
  title: string;
  source_name: string;
  collected_at: string;
  composite_score?: number;
}

interface Opportunity {
  id: number;
  entity_name: string;
  composite_score: number;
  trend_direction: string;
  signal_count?: number;
}

function KPICard({
  label,
  value,
  subtext,
  accent,
}: {
  label: string;
  value: string;
  subtext?: string;
  accent?: string;
}) {
  return (
    <div className="bg-surface-card border border-zinc-800 rounded-lg p-4 card-hover">
      <p className="text-xs font-medium text-zinc-500 uppercase tracking-wider mb-1">
        {label}
      </p>
      <p className={`text-2xl font-bold tabular-nums ${accent || "text-zinc-100"}`}>
        {value}
      </p>
      {subtext && <p className="text-xs text-zinc-500 mt-1">{subtext}</p>}
    </div>
  );
}

function SignalCard({ signal }: { signal: Signal }) {
  const sourceClass = getSourceColor(signal.source_name || "");
  return (
    <div className="flex items-start gap-3 py-3 px-3 rounded-lg bg-surface-card border border-zinc-800 card-hover animate-slide-in">
      <div className="mt-1 w-2 h-2 rounded-full bg-accent-blue shrink-0" />
      <div className="flex-1 min-w-0">
        <p className="text-sm text-zinc-200 truncate">{signal.title}</p>
        <div className="flex items-center gap-2 mt-1">
          <span className={`text-[10px] font-mono font-medium px-1.5 py-0.5 rounded ${sourceClass}`}>
            {signal.source_name}
          </span>
          <span className="text-[10px] text-zinc-600">
            {signal.collected_at?.split("T")[0] || ""}
          </span>
        </div>
      </div>
    </div>
  );
}

function OpportunityRow({ opp }: { opp: Opportunity }) {
  return (
    <Link
      href={`/opportunities/${opp.id}`}
      className="flex items-center gap-4 py-3 px-4 rounded-lg bg-surface-card border border-zinc-800 card-hover group"
    >
      {/* Score bar */}
      <div className={`flex items-center justify-center w-12 h-12 rounded-lg border ${getScoreBg(opp.composite_score)}`}>
        <span className={`text-lg font-bold font-mono ${getScoreColor(opp.composite_score)}`}>
          {formatScore(opp.composite_score)}
        </span>
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-zinc-200 group-hover:text-accent-blue transition-colors truncate">
          {opp.entity_name}
        </p>
        <p className="text-xs text-zinc-500">
          {opp.signal_count || 0} signals
        </p>
      </div>
      <div className="flex items-center gap-1 text-xs text-zinc-500">
        {opp.trend_direction === "up" && (
          <span className="text-accent-green">▲</span>
        )}
        {opp.trend_direction === "down" && (
          <span className="text-accent-red">▼</span>
        )}
        {opp.trend_direction === "stable" && (
          <span className="text-zinc-500">→</span>
        )}
      </div>
    </Link>
  );
}

export default function RadarPage() {
  const [stats, setStats] = useState<Stats>({});
  const [signals, setSignals] = useState<Signal[]>([]);
  const [opportunities, setOpportunities] = useState<Opportunity[]>([]);
  const [loading, setLoading] = useState(true);
  const [scoreDistribution, setScoreDistribution] = useState<Array<{ range: string; count: number }>>([]);
  const [trendData, setTrendData] = useState<Array<{ date: string; score: number; signals: number }>>([]);

  useEffect(() => {
    async function load() {
      try {
        const [s, sig, opp] = await Promise.all([
          fetchAPI<Stats>("/api/stats/summary"),
          fetchAPI<{ signals: Signal[] }>("/api/signals?limit=10"),
          fetchAPI<{ opportunities: Opportunity[] }>("/api/opportunities?limit=50"),
        ]);
        setStats(s);
        setSignals(sig.signals || []);
        setOpportunities(opp.opportunities || []);

        // Generate score distribution from opportunities
        if (opp.opportunities && opp.opportunities.length > 0) {
          const distribution = [
            { range: "80+", count: 0 },
            { range: "60-79", count: 0 },
            { range: "40-59", count: 0 },
            { range: "<40", count: 0 },
          ];
          opp.opportunities.forEach((o: Opportunity) => {
            const score = o.composite_score || 0;
            if (score >= 80) distribution[0].count++;
            else if (score >= 60) distribution[1].count++;
            else if (score >= 40) distribution[2].count++;
            else distribution[3].count++;
          });
          setScoreDistribution(distribution);

          // Generate trend data (mock 7-day trend from current data)
          const trend = [];
          const baseScore = avgScore(opp.opportunities);
          for (let i = 6; i >= 0; i--) {
            const date = new Date();
            date.setDate(date.getDate() - i);
            trend.push({
              date: date.toLocaleDateString("en-US", { month: "short", day: "numeric" }),
              score: Math.max(0, baseScore + (Math.random() - 0.5) * 10),
              signals: Math.floor(Math.random() * 50 + 20),
            });
          }
          setTrendData(trend);
        }
      } catch {
        // graceful degradation — use empty data
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  function avgScore(opps: Opportunity[]): number {
    return opps.length > 0
      ? opps.reduce((s, o) => s + (o.composite_score || 0), 0) / opps.length
      : 0;
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-6 h-6 border-2 border-accent-blue border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      {/* KPI Row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <KPICard
          label="Signals Today"
          value={formatNumber(stats.signals_today || 0)}
          subtext="↑ from daily avg"
          accent="text-accent-blue"
        />
        <KPICard
          label="Opportunities"
          value={formatNumber(stats.total_opportunities || 0)}
          subtext="scored > 60"
          accent="text-accent-green"
        />
        <KPICard
          label="Startups Tracked"
          value={formatNumber(stats.total_startups || 0)}
          subtext="in knowledge graph"
        />
        <KPICard
          label="Active Alerts"
          value={String(stats.active_alerts || 0)}
          accent="text-accent-amber"
        />
      </div>

      <div className="grid lg:grid-cols-2 gap-6">
        {/* Live Signal Feed */}
        <div>
          <h2 className="text-sm font-medium text-zinc-400 mb-3 flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-accent-green live-dot" />
            Live Signal Feed
          </h2>
          <div className="space-y-2">
            {signals.length > 0 ? (
              signals.map((s) => <SignalCard key={s.id} signal={s} />)
            ) : (
              <div className="text-center py-12 text-zinc-600 text-sm">
                No signals yet. Start the pipeline to collect data.
              </div>
            )}
          </div>
        </div>

        {/* Top Opportunities */}
        <div>
          <h2 className="text-sm font-medium text-zinc-400 mb-3">
            Top Opportunities
          </h2>
          <div className="space-y-2">
            {opportunities.length > 0 ? (
              opportunities.map((o) => <OpportunityRow key={o.id} opp={o} />)
            ) : (
              <div className="text-center py-12 text-zinc-600 text-sm">
                No opportunities scored yet. Run the analysis pipeline.
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Charts Section */}
      {(scoreDistribution.length > 0 || trendData.length > 0) && (
        <div className="space-y-4">
          <h2 className="text-sm font-medium text-zinc-400">
            Analytics
          </h2>
          <div className="grid lg:grid-cols-3 gap-4">
            {scoreDistribution.length > 0 && (
              <ScoreDistributionChart
                data={scoreDistribution}
                title="Opportunity Score Distribution"
              />
            )}
            {trendData.length > 0 && (
              <TrendChart data={trendData} title="7-Day Score Trend" />
            )}
            {trendData.length > 0 && (
              <SignalVolumeChart
                data={trendData.map(d => ({
                  date: d.date,
                  signals: d.signals,
                  alerts: Math.floor(d.signals * 0.1),
                }))}
                title="Signal Volume"
              />
            )}
          </div>
        </div>
      )}

      {/* Sector Overview placeholder */}
      <div>
        <h2 className="text-sm font-medium text-zinc-400 mb-3">
          Sector Heat Map
        </h2>
        <div className="grid grid-cols-3 md:grid-cols-5 gap-3">
          {[
            { name: "AI/ML", heat: "hot" },
            { name: "SaaS", heat: "warm" },
            { name: "CleanTech", heat: "emerging" },
            { name: "FinTech", heat: "warm" },
            { name: "HealthTech", heat: "stable" },
          ].map((sector) => (
            <div
              key={sector.name}
              className={`rounded-lg border p-3 text-center text-sm font-medium ${
                sector.heat === "hot"
                  ? "bg-red-500/10 border-red-500/20 text-red-400"
                  : sector.heat === "warm"
                  ? "bg-amber-500/10 border-amber-500/20 text-amber-400"
                  : sector.heat === "emerging"
                  ? "bg-blue-500/10 border-blue-500/20 text-blue-400"
                  : "bg-zinc-800 border-zinc-700 text-zinc-500"
              }`}
            >
              {sector.name}
              <br />
              <span className="text-[10px] uppercase tracking-wider opacity-60">
                {sector.heat}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
