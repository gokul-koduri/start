"""Build the Ohio Manufacturing Intelligence page for the Government Dashboard.

This page shows Ohio's EV Battery Manufacturing opportunity intelligence
for economic development decision-makers.

It presents scored opportunities with evidence-based recommendations
for "Which industries should Ohio build?"
"""

'use client';

import { useEffect, useState } from 'react';
import {
  AlertTriangle,
  ArrowUpRight,
  Battery,
  Building2,
  CheckCircle2,
  Cpu,
  Factory,
  Globe,
  Info,
  MapPin,
  TrendingUp,
  Users,
  XCircle,
  Zap,
} from 'lucide-react';

interface Opportunity {
  id: number;
  title: string;
  opportunity_type: string;
  sector: string;
  sub_sector: string;
  demand_score: number;
  supply_gap_score: number;
  feasibility_score: number;
  timing_score: number;
  competition_score: number;
  opportunity_score: number;
  confidence_score: number;
  confidence_label: string;
  decision: string;
  total_addressable_market_billion: number;
  service_addressable_market_billion: number;
  expected_growth_rate_pct: number;
  estimated_capex_min: number;
  estimated_capex_max: number;
  time_to_market_months: number;
  jobs_creation_estimate: number;
  description: string;
  addressable_customer_types: string[];
}

interface DashboardStats {
  total_opportunities: number;
  avg_opportunity_score: number;
  avg_confidence: number;
  total_tam_billion: number;
  total_jobs_estimate: number;
}

// -------------------------------------------------------------------
// Score badges
// -------------------------------------------------------------------
function ScoreBar({
  label,
  value,
  max = 100,
  color = 'bg-accent-blue',
}: {
  label: string;
  value: number;
  max?: number;
  color?: string;
}) {
  const pct = Math.min(100, (value / max) * 100);
  return (
    <div className="flex items-center gap-2 text-sm">
      <span className="w-36 text-zinc-500 flex-shrink-0">{label}</span>
      <div className="flex-1 h-2 bg-zinc-700 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all ${color}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="w-10 text-right font-mono text-zinc-300">{value}</span>
    </div>
  );
}

function DecisionBadge({ decision }: { decision: string }) {
  const map: Record<string, { color: string; bg: string; label: string }> = {
    strong_recommendation: {
      color: 'text-accent-green',
      bg: 'bg-accent-green/10 border-accent-green/20',
      label: 'Strong',
    },
    conditional_recommendation: {
      color: 'text-yellow-400',
      bg: 'bg-yellow-400/10 border-yellow-400/20',
      label: 'Conditional',
    },
    requires_validation: {
      color: 'text-orange-400',
      bg: 'bg-orange-400/10 border-orange-400/20',
      label: 'Validate',
    },
    not_recommended: {
      color: 'text-red-400',
      bg: 'bg-red-400/10 border-red-400/20',
      label: 'Not Recommended',
    },
  };
  const cfg = map[decision] || map.not_recommended;
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium border ${cfg.color} ${cfg.bg}`}>
      {decision === 'strong_recommendation' ? <CheckCircle2 size={12} /> : <Info size={12} />}
      {cfg.label}
    </span>
  );
}

// -------------------------------------------------------------------
// Score circle
// -------------------------------------------------------------------
function OpportunityScoreCircle({ score }: { score: number }) {
  const r = 28;
  const circ = 2 * Math.PI * r;
  const pct = score / 100;
  const dash = pct * circ;
  const color = score >= 75 ? '#16a34a' : score >= 60 ? '#ca8a04' : score >= 45 ? '#ea580c' : '#dc2626';

  return (
    <div className="relative w-16 h-16 flex-shrink-0">
      <svg className="w-16 h-16 -rotate-90" viewBox="0 0 64 64">
        <circle cx="32" cy="32" r={r} fill="none" stroke="#27272a" strokeWidth="6" />
        <circle
          cx="32" cy="32" r={r} fill="none" stroke={color}
          strokeWidth="6" strokeLinecap="round"
          strokeDasharray={`${dash} ${circ - dash}`}
        />
      </svg>
      <span className="absolute inset-0 flex items-center justify-center font-bold text-lg" style={{ color }}>
        {score}
      </span>
    </div>
  );
}

// -------------------------------------------------------------------
// Stat card
// -------------------------------------------------------------------
function StatCard({
  icon: Icon,
  label,
  value,
  sub,
  color = 'blue',
}: {
  icon: React.ElementType;
  label: string;
  value: string;
  sub?: string;
  color?: string;
}) {
  const colorMap: Record<string, string> = {
    blue: 'text-accent-blue bg-accent-blue/10',
    green: 'text-accent-green bg-accent-green/10',
    purple: 'text-purple-400 bg-purple-400/10',
    orange: 'text-orange-400 bg-orange-400/10',
    teal: 'text-teal-400 bg-teal-400/10',
    red: 'text-red-400 bg-red-400/10',
  };
  return (
    <div className="bg-surface-card rounded-xl shadow-sm border border-zinc-800 p-4">
      <div className="flex items-center gap-3 mb-2">
        <div className={`p-2 rounded-lg ${colorMap[color] || colorMap.blue}`}>
          <Icon size={20} />
        </div>
        <span className="text-zinc-500 text-sm font-medium">{label}</span>
      </div>
      <div className="text-2xl font-bold text-zinc-50">{value}</div>
      {sub && <div className="text-xs text-zinc-600 mt-0.5">{sub}</div>}
    </div>
  );
}

// -------------------------------------------------------------------
// CAPEX formatter
// -------------------------------------------------------------------
function formatCapex(min: number, max: number): string {
  if (!min && !max) return '—';
  if (!max) return `$${Math.round(min / 1e6)}M+`;
  if (!min) return `$${Math.round(max / 1e6)}M`;
  return `$${Math.round(min / 1e6)}–${Math.round(max / 1e6)}M`;
}

// -------------------------------------------------------------------
// Main page
// -------------------------------------------------------------------
export default function OhioManufacturingPage() {
  const [opportunities, setOpportunities] = useState<Opportunity[]>([]);
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState<number | null>(null);
  const [selectedDecision, setSelectedDecision] = useState<string>('all');

  useEffect(() => {
    fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v2/government/ohio-manufacturing`)
      .then(r => r.json())
      .then(d => {
        setOpportunities(d.opportunities || []);
        setStats(d.stats || null);
      })
      .catch(() => setOpportunities([]))
      .finally(() => setLoading(false));
  }, []);

  const filtered = selectedDecision === 'all'
    ? opportunities
    : opportunities.filter(o => o.decision === selectedDecision);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-pulse text-zinc-600">Loading Ohio Manufacturing Intelligence...</div>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="border-b border-zinc-800 pb-4">
        <div className="flex items-center gap-2 text-sm text-zinc-500 mb-1">
          <MapPin size={14} />
          Ohio, USA
        </div>
        <h1 className="text-3xl font-bold text-zinc-50">
          Ohio Manufacturing Opportunity Intelligence
        </h1>
        <p className="text-zinc-400 mt-1">
          AI-identified manufacturing opportunities. Which companies should Ohio build?
        </p>
      </div>

      {/* Hero stats */}
      {stats && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard icon={Zap} label="Opportunities Identified" value={String(stats.total_opportunities)} color="blue" />
          <StatCard icon={TrendingUp} label="Avg. Opportunity Score" value={String(stats.avg_opportunity_score)} sub="0-100 scale" color="green" />
          <StatCard icon={Globe} label="Total Addressable Market" value={`$${stats.total_tam_billion}B`} color="purple" />
          <StatCard icon={Users} label="Est. Jobs Creation" value={String(stats.total_jobs_estimate)} sub="direct manufacturing jobs" color="orange" />
        </div>
      )}

      {/* Confidence notice */}
      {!loading && stats && stats.avg_confidence < 0.6 && (
        <div className="flex items-start gap-2 p-3 rounded-lg bg-yellow-400/10 border border-yellow-400/20 text-sm">
          <AlertTriangle className="text-yellow-400 flex-shrink-0 mt-0.5" size={16} />
          <span className="text-yellow-300">
            Average model confidence is {Math.round(stats.avg_confidence * 100)}%. CAPEX estimates
            and feasibility scores require supplier validation before investment decisions.
          </span>
        </div>
      )}

      {/* Filter bar */}
      <div className="flex items-center gap-2 flex-wrap">
        <span className="text-sm font-medium text-zinc-300">Filter:</span>
        {['all', 'strong_recommendation', 'conditional_recommendation', 'requires_validation'].map(d => (
          <button
            key={d}
            onClick={() => setSelectedDecision(d)}
            className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
              selectedDecision === d
                ? 'bg-accent-blue text-white'
                : 'bg-zinc-700 text-zinc-400 hover:bg-zinc-600'
                : 'bg-zinc-800 text-zinc-400 hover:bg-zinc-700'
            }`}
          >
            {d === 'all' ? 'All' : d === 'strong_recommendation' ? 'Strong' : d === 'conditional_recommendation' ? 'Conditional' : 'Validate'}
          </button>
        ))}
      </div>

      {/* Opportunity cards */}
      {filtered.length === 0 ? (
        <div className="text-center py-16 text-zinc-600">
          <Battery size={48} className="mx-auto mb-3 opacity-40" />
          <p>No opportunities match your filter.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {filtered.map(opp => {
            const isOpen = expanded === opp.id;
            return (
              <div key={opp.id} className="bg-white border border-zinc-800 rounded-xl shadow-sm overflow-hidden">
                {/* Card header */}
                <div
                  className="flex items-start gap-4 p-4 cursor-pointer hover:bg-zinc-900 transition-colors"
                  onClick={() => setExpanded(isOpen ? null : opp.id)}
                >
                  <OpportunityScoreCircle score={opp.opportunity_score} />

                  <div className="flex-1 min-w-0">
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <h3 className="font-semibold text-zinc-50 leading-tight">{opp.title}</h3>
                        <div className="flex items-center gap-2 mt-1 flex-wrap">
                          <span className="inline-flex items-center gap-1 text-xs text-zinc-500">
                            <Cpu size={12} /> {opp.sub_sector || opp.sector}
                          </span>
                          <span className="inline-flex items-center gap-1 text-xs text-zinc-500">
                            <Battery size={12} /> {opp.opportunity_type}
                          </span>
                        </div>
                      </div>
                      <div className="flex items-center gap-2 flex-shrink-0">
                        <DecisionBadge decision={opp.decision} />
                        <span className="text-xs text-zinc-600">
                          Confidence: {Math.round(opp.confidence_score * 100)}%
                        </span>
                      </div>
                    </div>

                    {/* Quick score bars */}
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-1.5 mt-3">
                      <ScoreBar label="Market Demand" value={opp.demand_score} color="bg-accent-green" />
                      <ScoreBar label="Supply Gap" value={opp.supply_gap_score} color="bg-accent-blue" />
                      <ScoreBar label="Feasibility" value={opp.feasibility_score} color="bg-purple-400" />
                      <ScoreBar label="Timing" value={opp.timing_score} color="bg-teal-400" />
                    </div>
                  </div>
                </div>

                {/* Expanded details */}
                {isOpen && (
                  <div className="border-t border-zinc-700 p-4 bg-zinc-900 space-y-4">
                    <p className="text-sm text-zinc-300">{opp.description}</p>

                    {/* Market data */}
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                      <div className="bg-white rounded-lg p-3 border border-zinc-800">
                        <div className="text-xs text-zinc-500 mb-1">TAM</div>
                        <div className="font-semibold text-zinc-50">
                          ${opp.total_addressable_market_billion}B
                        </div>
                      </div>
                      <div className="bg-white rounded-lg p-3 border border-zinc-800">
                        <div className="text-xs text-zinc-500 mb-1">Growth Rate</div>
                        <div className="font-semibold text-zinc-50">
                          {opp.expected_growth_rate_pct}%/yr
                        </div>
                      </div>
                      <div className="bg-white rounded-lg p-3 border border-zinc-800">
                        <div className="text-xs text-zinc-500 mb-1">Est. CAPEX</div>
                        <div className="font-semibold text-zinc-50">
                          {formatCapex(opp.estimated_capex_min, opp.estimated_capex_max)}
                        </div>
                      </div>
                      <div className="bg-white rounded-lg p-3 border border-zinc-800">
                        <div className="text-xs text-zinc-500 mb-1">Time to Market</div>
                        <div className="font-semibold text-zinc-50">
                          {opp.time_to_market_months} months
                        </div>
                      </div>
                    </div>

                    {/* Customer types */}
                    {opp.addressable_customer_types.length > 0 && (
                      <div>
                        <div className="text-xs font-medium text-zinc-500 mb-1.5">Addressable Customers</div>
                        <div className="flex flex-wrap gap-1.5">
                          {opp.addressable_customer_types.map(c => (
                            <span key={c} className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-accent-blue/10 text-accent-blue text-xs border border-accent-blue/20">
                              <Building2 size={10} /> {c}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Jobs */}
                    <div className="flex items-center gap-2 text-sm">
                      <Users className="text-zinc-600" size={14} />
                      <span className="text-zinc-400">
                        Estimated <strong className="text-zinc-50">{opp.jobs_creation_estimate.toLocaleString()}</strong> direct manufacturing jobs
                      </span>
                    </div>

                    {/* CAPEX confidence note */}
                    <div className="flex items-start gap-2 text-xs text-zinc-500 bg-white rounded-lg p-3 border border-zinc-800">
                      <Info size={14} className="flex-shrink-0 mt-0.5" />
                      CAPEX estimates are model-based (±30% accuracy). Validate with equipment suppliers
                      and real estate brokers before decision-making.
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}