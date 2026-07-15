"use client";

import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  LineChart,
  Line,
  Legend,
} from "recharts";

const CHART_COLORS = {
  primary: "#3b82f6", // blue-500
  secondary: "#10b981", // green-500
  tertiary: "#f59e0b", // amber-500
  quaternary: "#ef4444", // red-500
  muted: "#52525b", // zinc-600
};

const PALETTE = [
  CHART_COLORS.primary,
  CHART_COLORS.secondary,
  CHART_COLORS.tertiary,
  CHART_COLORS.quaternary,
  "#8b5cf6", // violet-500
  "#ec4899", // pink-500
  "#06b6d4", // cyan-500
  CHART_COLORS.muted,
];

interface ChartTooltipProps {
  active?: boolean;
  payload?: Array<{ name: string; value: number; color?: string }>;
  label?: string;
}

function CustomTooltip({ active, payload, label }: ChartTooltipProps) {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-3 shadow-xl">
      <p className="text-xs text-zinc-400 mb-1">{label}</p>
      {payload.map((entry, i) => (
        <div key={i} className="flex items-center gap-2 text-sm">
          <div
            className="w-2 h-2 rounded-full"
            style={{ backgroundColor: entry.color }}
          />
          <span className="text-zinc-300">{entry.name}:</span>
          <span className="text-zinc-100 font-mono">{entry.value}</span>
        </div>
      ))}
    </div>
  );
}

// Score Distribution Chart (Histogram)
interface ScoreDistributionChartProps {
  data: Array<{ range: string; count: number; score?: number }>;
  title?: string;
}

export function ScoreDistributionChart({
  data,
  title = "Score Distribution",
}: ScoreDistributionChartProps) {
  return (
    <div className="bg-surface-card border border-zinc-800 rounded-lg p-4">
      <h3 className="text-sm font-medium text-zinc-400 mb-4">{title}</h3>
      <ResponsiveContainer width="100%" height={200}>
        <BarChart data={data} margin={{ top: 5, right: 5, left: -20, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
          <XAxis
            dataKey="range"
            tick={{ fontSize: 10, fill: "#71717a" }}
            axisLine={{ stroke: "#27272a" }}
          />
          <YAxis
            tick={{ fontSize: 10, fill: "#71717a" }}
            axisLine={{ stroke: "#27272a" }}
          />
          <Tooltip content={<CustomTooltip />} />
          <Bar dataKey="count" radius={[4, 4, 0, 0]}>
            {data.map((_, index) => (
              <Cell
                key={`cell-${index}`}
                fill={PALETTE[index % PALETTE.length]}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

// Opportunity Trend Chart (Area)
interface TrendChartProps {
  data: Array<{ date: string; score: number; signals: number }>;
  title?: string;
}

export function TrendChart({ data, title = "Opportunity Trends" }: TrendChartProps) {
  return (
    <div className="bg-surface-card border border-zinc-800 rounded-lg p-4">
      <h3 className="text-sm font-medium text-zinc-400 mb-4">{title}</h3>
      <ResponsiveContainer width="100%" height={200}>
        <AreaChart data={data} margin={{ top: 5, right: 5, left: -20, bottom: 5 }}>
          <defs>
            <linearGradient id="colorScore" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={CHART_COLORS.primary} stopOpacity={0.3} />
              <stop offset="95%" stopColor={CHART_COLORS.primary} stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
          <XAxis
            dataKey="date"
            tick={{ fontSize: 10, fill: "#71717a" }}
            axisLine={{ stroke: "#27272a" }}
          />
          <YAxis
            tick={{ fontSize: 10, fill: "#71717a" }}
            axisLine={{ stroke: "#27272a" }}
          />
          <Tooltip content={<CustomTooltip />} />
          <Area
            type="monotone"
            dataKey="score"
            stroke={CHART_COLORS.primary}
            fill="url(#colorScore)"
            name="Score"
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

// Category Breakdown (Donut Chart)
interface CategoryChartProps {
  data: Array<{ name: string; value: number }>;
  title?: string;
}

export function CategoryChart({ data, title = "Category Breakdown" }: CategoryChartProps) {
  return (
    <div className="bg-surface-card border border-zinc-800 rounded-lg p-4">
      <h3 className="text-sm font-medium text-zinc-400 mb-4">{title}</h3>
      <div className="flex items-center gap-4">
        <ResponsiveContainer width={140} height={140}>
          <PieChart>
            <Pie
              data={data}
              cx="50%"
              cy="50%"
              innerRadius={40}
              outerRadius={60}
              paddingAngle={2}
              dataKey="value"
            >
              {data.map((_, index) => (
                <Cell
                  key={`cell-${index}`}
                  fill={PALETTE[index % PALETTE.length]}
                />
              ))}
            </Pie>
            <Tooltip content={<CustomTooltip />} />
          </PieChart>
        </ResponsiveContainer>
        <div className="flex-1 space-y-1.5">
          {data.slice(0, 5).map((entry, index) => (
            <div key={entry.name} className="flex items-center gap-2 text-xs">
              <div
                className="w-2 h-2 rounded-full shrink-0"
                style={{ backgroundColor: PALETTE[index % PALETTE.length] }}
              />
              <span className="text-zinc-400 truncate">{entry.name}</span>
              <span className="text-zinc-200 ml-auto font-mono">{entry.value}</span>
            </div>
          ))}
          {data.length > 5 && (
            <p className="text-[10px] text-zinc-600">+{data.length - 5} more</p>
          )}
        </div>
      </div>
    </div>
  );
}

// Signal Volume Chart (Line)
interface SignalVolumeChartProps {
  data: Array<{ date: string; signals: number; alerts: number }>;
  title?: string;
}

export function SignalVolumeChart({
  data,
  title = "Signal Volume",
}: SignalVolumeChartProps) {
  return (
    <div className="bg-surface-card border border-zinc-800 rounded-lg p-4">
      <h3 className="text-sm font-medium text-zinc-400 mb-4">{title}</h3>
      <ResponsiveContainer width="100%" height={200}>
        <LineChart data={data} margin={{ top: 5, right: 5, left: -20, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
          <XAxis
            dataKey="date"
            tick={{ fontSize: 10, fill: "#71717a" }}
            axisLine={{ stroke: "#27272a" }}
          />
          <YAxis
            tick={{ fontSize: 10, fill: "#71717a" }}
            axisLine={{ stroke: "#27272a" }}
          />
          <Tooltip content={<CustomTooltip />} />
          <Legend
            wrapperStyle={{ fontSize: 10, paddingTop: 10 }}
            iconType="circle"
            iconSize={6}
          />
          <Line
            type="monotone"
            dataKey="signals"
            stroke={CHART_COLORS.primary}
            strokeWidth={2}
            dot={false}
            name="Signals"
          />
          <Line
            type="monotone"
            dataKey="alerts"
            stroke={CHART_COLORS.tertiary}
            strokeWidth={2}
            dot={false}
            name="Alerts"
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

// Funding Activity Chart (Bar)
interface FundingChartProps {
  data: Array<{ month: string; seed: number; seriesA: number; seriesB: number }>;
  title?: string;
}

export function FundingChart({ data, title = "Funding Activity" }: FundingChartProps) {
  return (
    <div className="bg-surface-card border border-zinc-800 rounded-lg p-4">
      <h3 className="text-sm font-medium text-zinc-400 mb-4">{title}</h3>
      <ResponsiveContainer width="100%" height={200}>
        <BarChart data={data} margin={{ top: 5, right: 5, left: -20, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
          <XAxis
            dataKey="month"
            tick={{ fontSize: 10, fill: "#71717a" }}
            axisLine={{ stroke: "#27272a" }}
          />
          <YAxis
            tick={{ fontSize: 10, fill: "#71717a" }}
            axisLine={{ stroke: "#27272a" }}
          />
          <Tooltip content={<CustomTooltip />} />
          <Legend
            wrapperStyle={{ fontSize: 10, paddingTop: 10 }}
            iconType="circle"
            iconSize={6}
          />
          <Bar dataKey="seed" stackId="a" fill={CHART_COLORS.primary} name="Seed" />
          <Bar dataKey="seriesA" stackId="a" fill={CHART_COLORS.secondary} name="Series A" />
          <Bar dataKey="seriesB" stackId="a" fill={CHART_COLORS.tertiary} name="Series B" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}