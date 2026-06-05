"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import {
  fetchAPI,
  formatScore,
  getScoreColor,
  getScoreBg,
  getSourceColor,
} from "@/lib/api";
import {
  ArrowLeft,
  TrendingUp,
  TrendingDown,
  Minus,
  ExternalLink,
} from "lucide-react";

interface Opportunity {
  id: number;
  entity_name: string;
  composite_score: number;
  trend_direction: string;
  signal_count?: number;
  sector?: string;
  region?: string;
  last_updated?: string;
  score_breakdown?: {
    signal_recency?: number;
    signal_volume?: number;
    sentiment?: number;
    entity_strength?: number;
    growth_velocity?: number;
  };
}

interface Signal {
  id: number;
  signal_type: string;
  title: string;
  body_text: string;
  source_name: string;
  collected_at: string;
  sentiment_score?: number;
}

interface RelatedEntity {
  entity_name: string;
  relationship_type: string;
  weight: number;
}

export default function OpportunityDetailPage() {
  const params = useParams();
  const id = params?.id as string;
  const [opportunity, setOpportunity] = useState<Opportunity | null>(null);
  const [signals, setSignals] = useState<Signal[]>([]);
  const [related, setRelated] = useState<RelatedEntity[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!id) return;
    async function load() {
      try {
        const [opp, sig] = await Promise.all([
          fetchAPI<Opportunity>(`/api/opportunities/${id}`),
          fetchAPI<{ signals: Signal[] }>(
            `/api/signals?entity_name=&limit=20`
          ),
        ]);
        setOpportunity(opp);
        setSignals(sig.signals || []);

        // Fetch related entities for the graph context
        if (opp?.entity_name) {
          const graph = await fetchAPI<{
            edges: RelatedEntity[];
          }>(
            `/api/entities/${encodeURIComponent(opp.entity_name)}/connections?depth=1&limit=10`
          );
          setRelated(graph.edges || []);
        }
      } catch {
        // graceful degradation
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [id]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-6 h-6 border-2 border-accent-blue border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (!opportunity) {
    return (
      <div className="flex flex-col items-center justify-center h-64 gap-3">
        <p className="text-zinc-500 text-sm">Opportunity not found</p>
        <Link
          href="/opportunities"
          className="text-xs text-accent-blue hover:underline"
        >
          ← Back to list
        </Link>
      </div>
    );
  }

  const breakdown = opportunity.score_breakdown;
  const breakdownEntries = breakdown
    ? Object.entries(breakdown).filter(([, v]) => v !== undefined && v !== 0)
    : [];

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Back link */}
      <Link
        href="/opportunities"
        className="inline-flex items-center gap-1.5 text-xs text-zinc-500 hover:text-zinc-300 transition-colors"
      >
        <ArrowLeft className="w-3 h-3" />
        Back to Opportunities
      </Link>

      {/* Header Card */}
      <div className="bg-surface-card border border-zinc-800 rounded-lg p-6">
        <div className="flex items-start gap-5">
          {/* Score Ring */}
          <div
            className={`flex items-center justify-center w-20 h-20 rounded-xl border-2 shrink-0 ${getScoreBg(
              opportunity.composite_score
            )}`}
          >
            <span
              className={`text-3xl font-bold font-mono ${getScoreColor(
                opportunity.composite_score
              )}`}
            >
              {formatScore(opportunity.composite_score)}
            </span>
          </div>

          <div className="flex-1">
            <h1 className="text-xl font-semibold text-zinc-100">
              {opportunity.entity_name}
            </h1>
            <div className="flex items-center gap-3 mt-1.5">
              {opportunity.sector && (
                <span className="text-xs text-zinc-500 font-mono px-2 py-0.5 bg-zinc-800 rounded-md">
                  {opportunity.sector}
                </span>
              )}
              {opportunity.region && (
                <span className="text-xs text-zinc-600 font-mono">
                  {opportunity.region}
                </span>
              )}
              <span className="text-xs text-zinc-700">·</span>
              <span className="text-xs text-zinc-600 font-mono">
                {opportunity.signal_count || 0} signals
              </span>
            </div>
            <div className="flex items-center gap-2 mt-2">
              {opportunity.trend_direction === "up" && (
                <span className="flex items-center gap-1 text-xs text-accent-green">
                  <TrendingUp className="w-3 h-3" />
                  Trending Up
                </span>
              )}
              {opportunity.trend_direction === "down" && (
                <span className="flex items-center gap-1 text-xs text-accent-red">
                  <TrendingDown className="w-3 h-3" />
                  Trending Down
                </span>
              )}
              {opportunity.trend_direction === "stable" && (
                <span className="flex items-center gap-1 text-xs text-zinc-500">
                  <Minus className="w-3 h-3" />
                  Stable
                </span>
              )}
              {opportunity.last_updated && (
                <span className="text-[10px] text-zinc-700 font-mono ml-auto">
                  Updated {opportunity.last_updated.split("T")[0]}
                </span>
              )}
            </div>
          </div>
        </div>
      </div>

      <div className="grid lg:grid-cols-3 gap-6">
        {/* Score Breakdown */}
        <div className="lg:col-span-2">
          {breakdownEntries.length > 0 && (
            <div className="bg-surface-card border border-zinc-800 rounded-lg p-5">
              <h2 className="text-sm font-medium text-zinc-400 mb-4">
                Score Breakdown
              </h2>
              <div className="space-y-3">
                {breakdownEntries.map(([key, value]) => {
                  const label = key
                    .replace(/_/g, " ")
                    .replace(/\b\w/g, (c) => c.toUpperCase());
                  return (
                    <div key={key}>
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-xs text-zinc-500">{label}</span>
                        <span className="text-xs font-mono text-zinc-300">
                          {(value as number).toFixed(1)}
                        </span>
                      </div>
                      <div className="h-1.5 bg-zinc-800 rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full transition-all ${
                            (value as number) >= 70
                              ? "bg-accent-green"
                              : (value as number) >= 40
                              ? "bg-accent-blue"
                              : "bg-accent-amber"
                          }`}
                          style={{ width: `${Math.min(100, (value as number))}%` }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Signal Timeline */}
          <div className="mt-5">
            <h2 className="text-sm font-medium text-zinc-400 mb-3">
              Signal Timeline
            </h2>
            <div className="space-y-2">
              {signals.length > 0 ? (
                signals.map((signal) => (
                  <div
                    key={signal.id}
                    className="bg-surface-card border border-zinc-800 rounded-lg p-3"
                  >
                    <div className="flex items-center justify-between mb-1.5">
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
                    <p className="text-xs text-zinc-300">{signal.title}</p>
                    {signal.body_text && (
                      <p className="text-[11px] text-zinc-500 mt-1 line-clamp-2">
                        {signal.body_text.slice(0, 200)}
                      </p>
                    )}
                  </div>
                ))
              ) : (
                <div className="text-center py-12 text-zinc-600 text-sm">
                  No signals linked to this entity yet.
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Sidebar: Related Entities */}
        <div>
          <div className="bg-surface-card border border-zinc-800 rounded-lg p-5">
            <h2 className="text-sm font-medium text-zinc-400 mb-3">
              Related Entities
            </h2>
            {related.length > 0 ? (
              <div className="space-y-2">
                {related.map((r, i) => (
                  <Link
                    key={i}
                    href={`/graph?q=${encodeURIComponent(r.entity_name)}`}
                    className="flex items-center justify-between py-2 px-2 rounded-md hover:bg-zinc-800/50 transition-colors group"
                  >
                    <div>
                      <p className="text-xs text-zinc-300 group-hover:text-accent-blue transition-colors truncate">
                        {r.entity_name}
                      </p>
                      <p className="text-[10px] text-zinc-600">
                        {r.relationship_type}
                      </p>
                    </div>
                    <ExternalLink className="w-3 h-3 text-zinc-700 group-hover:text-accent-blue transition-colors shrink-0" />
                  </Link>
                ))}
              </div>
            ) : (
              <p className="text-xs text-zinc-600 text-center py-6">
                No connections found.
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
