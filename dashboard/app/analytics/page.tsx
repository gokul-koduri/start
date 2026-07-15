'use client';

import { useState } from 'react';
import {
  TrendingUp,
  Activity,
  BarChart3,
  PieChart,
  Globe,
  Cpu,
  Shield,
  Code2,
} from 'lucide-react';
import { Card, Select } from '@/app/components/ui';

// Mock chart data
const apiGrowthData = [
  { month: 'Jan', count: 45 },
  { month: 'Feb', count: 52 },
  { month: 'Mar', count: 61 },
  { month: 'Apr', count: 78 },
  { month: 'May', count: 89 },
  { month: 'Jun', count: 98 },
  { month: 'Jul', count: 110 },
  { month: 'Aug', count: 118 },
  { month: 'Sep', count: 124 },
  { month: 'Oct', count: 131 },
  { month: 'Nov', count: 142 },
  { month: 'Dec', count: 156 },
];

const methodData = [
  { method: 'GET', count: 1842, color: '#10B981' },
  { method: 'POST', count: 612, color: '#2563EB' },
  { method: 'PUT', count: 234, color: '#F59E0B' },
  { method: 'DELETE', count: 123, color: '#EF4444' },
  { method: 'PATCH', count: 32, color: '#8B5CF6' },
];

const categoryData = [
  { category: 'payment', count: 34, color: '#10B981' },
  { category: 'social', count: 28, color: '#2563EB' },
  { category: 'ai', count: 22, color: '#8B5CF6' },
  { category: 'analytics', count: 18, color: '#F59E0B' },
  { category: 'communication', count: 15, color: '#06B6D4' },
  { category: 'devtools', count: 10, color: '#EF4444' },
];

const techData = [
  { tech: 'Node.js', count: 156 },
  { tech: 'Python', count: 134 },
  { tech: 'Express', count: 98 },
  { tech: 'Django', count: 67 },
  { tech: 'FastAPI', count: 54 },
  { tech: 'React', count: 48 },
  { tech: 'PostgreSQL', count: 42 },
  { tech: 'Redis', count: 38 },
];

export default function AnalyticsPage() {
  const [period, setPeriod] = useState('12m');
  const [chartType, setChartType] = useState<'line' | 'bar' | 'area'>('line');

  const maxGrowth = Math.max(...apiGrowthData.map(d => d.count));
  const totalMethods = methodData.reduce((sum, m) => sum + m.count, 0);
  const totalCategories = categoryData.reduce((sum, c) => sum + c.count, 0);
  const maxTech = Math.max(...techData.map(t => t.count));

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-text-primary">Analytics</h1>
          <p className="text-text-secondary mt-1">
            Insights and trends from your API ecosystem
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Select
            options={[
              { value: '7d', label: 'Last 7 days' },
              { value: '30d', label: 'Last 30 days' },
              { value: '90d', label: 'Last 90 days' },
              { value: '12m', label: 'Last 12 months' },
            ]}
            value={period}
            onChange={setPeriod}
            className="w-40"
          />
        </div>
      </div>

      {/* Stats Overview */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
        {[
          { label: 'Total APIs', value: '127', change: '+12%', icon: Code2, color: 'blue' },
          { label: 'API Growth', value: '+42', change: '+25%', icon: TrendingUp, color: 'emerald' },
          { label: 'Avg Response', value: '142ms', change: '-8%', icon: Activity, color: 'amber' },
          { label: 'Security Score', value: '78%', change: '+3%', icon: Shield, color: 'purple' },
        ].map((stat) => (
          <Card key={stat.label} padding="md">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-sm text-text-secondary">{stat.label}</p>
                <p className="text-2xl font-bold text-text-primary mt-1">{stat.value}</p>
                <p className={`text-xs mt-1 ${stat.change.startsWith('+') ? 'text-emerald-600' : 'text-amber-600'}`}>
                  {stat.change} vs last period
                </p>
              </div>
              <div className={`p-2 rounded-lg bg-${stat.color}-50 text-${stat.color}-600`}>
                <stat.icon className="w-5 h-5" />
              </div>
            </div>
          </Card>
        ))}
      </div>

      {/* Charts Row 1 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* API Growth Over Time */}
        <Card padding="lg">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h2 className="text-lg font-semibold text-text-primary">API Growth</h2>
              <p className="text-sm text-text-secondary">Total APIs over time</p>
            </div>
          </div>
          <div className="space-y-2">
            {apiGrowthData.map((item, idx) => (
              <div key={item.month} className="flex items-center gap-3">
                <span className="w-12 text-xs text-text-tertiary">{item.month}</span>
                <div className="flex-1 bg-bg-secondary rounded-full h-8 overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-accent-blue to-accent-cyan rounded-full flex items-center justify-end pr-2"
                    style={{ width: `${(item.count / maxGrowth) * 100}%` }}
                  >
                    <span className="text-xs font-medium text-white">{item.count}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
          <div className="mt-4 pt-4 border-t border-border">
            <div className="flex items-center justify-between text-sm">
              <span className="text-text-secondary">Total growth</span>
              <span className="text-emerald-600 font-medium">+246%</span>
            </div>
          </div>
        </Card>

        {/* Method Distribution */}
        <Card padding="lg">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h2 className="text-lg font-semibold text-text-primary">HTTP Methods</h2>
              <p className="text-sm text-text-secondary">Distribution by method type</p>
            </div>
          </div>
          <div className="flex items-center justify-center">
            {/* Simple Donut Chart */}
            <div className="relative w-48 h-48">
              <svg viewBox="0 0 100 100" className="transform -rotate-90">
                {(() => {
                  let cumulative = 0;
                  return methodData.map((item, idx) => {
                    const percentage = (item.count / totalMethods) * 100;
                    const dashArray = `${percentage} ${100 - percentage}`;
                    const dashOffset = -cumulative;
                    cumulative += percentage;
                    return (
                      <circle
                        key={item.method}
                        cx="50"
                        cy="50"
                        r="40"
                        fill="none"
                        stroke={item.color}
                        strokeWidth="20"
                        strokeDasharray={dashArray}
                        strokeDashoffset={dashOffset}
                        className="transition-all duration-500"
                      />
                    );
                  });
                })()}
              </svg>
              <div className="absolute inset-0 flex flex-col items-center justify-center">
                <span className="text-3xl font-bold text-text-primary">{totalMethods}</span>
                <span className="text-xs text-text-tertiary">Total</span>
              </div>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-2 mt-4">
            {methodData.map((item) => (
              <div key={item.method} className="flex items-center gap-2 p-2 bg-bg-secondary rounded-lg">
                <span
                  className="w-3 h-3 rounded-full"
                  style={{ backgroundColor: item.color }}
                />
                <span className="text-sm font-medium text-text-primary">{item.method}</span>
                <span className="text-xs text-text-tertiary ml-auto">{item.count}</span>
              </div>
            ))}
          </div>
        </Card>
      </div>

      {/* Charts Row 2 */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Category Distribution */}
        <Card padding="lg">
          <h2 className="text-lg font-semibold text-text-primary mb-4">Categories</h2>
          <div className="space-y-3">
            {categoryData.map((item) => (
              <div key={item.category} className="space-y-1">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-text-primary capitalize">{item.category}</span>
                  <span className="text-text-tertiary">{item.count}</span>
                </div>
                <div className="h-2 bg-bg-secondary rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all duration-500"
                    style={{
                      width: `${(item.count / (totalCategories || 1)) * 100}%`,
                      backgroundColor: item.color,
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
        </Card>

        {/* Top Technologies */}
        <Card padding="lg" className="lg:col-span-2">
          <h2 className="text-lg font-semibold text-text-primary mb-4 flex items-center gap-2">
            <Cpu className="w-5 h-5" />
            Top Technologies
          </h2>
          <div className="space-y-2">
            {techData.map((item, idx) => (
              <div key={item.tech} className="flex items-center gap-3 p-2 rounded-lg hover:bg-bg-secondary transition-colors">
                <span className="w-6 h-6 flex items-center justify-center rounded-full bg-bg-secondary text-xs font-bold text-text-secondary">
                  {idx + 1}
                </span>
                <span className="flex-1 text-sm font-medium text-text-primary">{item.tech}</span>
                <div className="w-32 h-2 bg-bg-secondary rounded-full overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-accent-blue to-accent-cyan rounded-full"
                    style={{ width: `${(item.count / maxTech) * 100}%` }}
                  />
                </div>
                <span className="text-sm text-text-tertiary w-8 text-right">{item.count}</span>
              </div>
            ))}
          </div>
        </Card>
      </div>

      {/* Geographic Distribution */}
      <Card padding="lg">
        <h2 className="text-lg font-semibold text-text-primary mb-4 flex items-center gap-2">
          <Globe className="w-5 h-5" />
          Geographic Distribution
        </h2>
        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-4">
          {[
            { country: 'United States', count: 67, flag: 'US' },
            { country: 'United Kingdom', count: 12, flag: 'UK' },
            { country: 'Germany', count: 8, flag: 'DE' },
            { country: 'Canada', count: 5, flag: 'CA' },
            { country: 'Australia', count: 4, flag: 'AU' },
            { country: 'France', count: 4, flag: 'FR' },
          ].map((item) => (
            <div key={item.country} className="p-3 bg-bg-secondary rounded-lg text-center">
              <div className="w-10 h-10 mx-auto rounded-full bg-accent-blue/10 flex items-center justify-center text-sm font-bold text-accent-blue mb-2">
                {item.flag}
              </div>
              <p className="text-sm font-medium text-text-primary">{item.country}</p>
              <p className="text-xs text-text-tertiary">{item.count}%</p>
            </div>
          ))}
        </div>
      </Card>

      {/* Performance Metrics */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card padding="lg">
          <h2 className="text-lg font-semibold text-text-primary mb-4">Response Time Distribution</h2>
          <div className="space-y-3">
            {[
              { range: '< 100ms', count: 890, percentage: 45 },
              { range: '100-200ms', count: 623, percentage: 31 },
              { range: '200-500ms', count: 312, percentage: 16 },
              { range: '500ms-1s', count: 118, percentage: 6 },
              { range: '> 1s', count: 45, percentage: 2 },
            ].map((item) => (
              <div key={item.range} className="flex items-center gap-3">
                <span className="w-20 text-sm text-text-secondary">{item.range}</span>
                <div className="flex-1 h-6 bg-bg-secondary rounded-lg overflow-hidden">
                  <div
                    className="h-full rounded-lg flex items-center justify-end pr-2"
                    style={{
                      width: `${item.percentage}%`,
                      backgroundColor:
                        item.range.includes('<') ? '#10B981' :
                        item.range.includes('200') ? '#2563EB' :
                        item.range.includes('500') ? '#F59E0B' :
                        '#EF4444',
                    }}
                  >
                    <span className="text-xs font-medium text-white">
                      {item.percentage}%
                    </span>
                  </div>
                </div>
                <span className="w-12 text-sm text-text-tertiary text-right">{item.count}</span>
              </div>
            ))}
          </div>
        </Card>

        <Card padding="lg">
          <h2 className="text-lg font-semibold text-text-primary mb-4">Security Trends</h2>
          <div className="space-y-4">
            <div className="flex items-center justify-between p-3 bg-emerald-50 rounded-lg border border-emerald-100">
              <div className="flex items-center gap-2">
                <Shield className="w-5 h-5 text-emerald-600" />
                <span className="font-medium text-emerald-700">High Security Apis</span>
              </div>
              <span className="text-xl font-bold text-emerald-700">1423</span>
            </div>
            <div className="flex items-center justify-between p-3 bg-blue-50 rounded-lg border border-blue-100">
              <div className="flex items-center gap-2">
                <Shield className="w-5 h-5 text-blue-600" />
                <span className="font-medium text-blue-700">Medium Security</span>
              </div>
              <span className="text-xl font-bold text-blue-700">876</span>
            </div>
            <div className="flex items-center justify-between p-3 bg-red-50 rounded-lg border border-red-100">
              <div className="flex items-center gap-2">
                <Shield className="w-5 h-5 text-red-600" />
                <span className="font-medium text-red-700">Needs Attention</span>
              </div>
              <span className="text-xl font-bold text-red-700">312</span>
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
}