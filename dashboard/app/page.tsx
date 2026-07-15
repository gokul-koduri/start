'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import {
  Database,
  Building2,
  Cpu,
  Globe,
  Clock,
  Shield,
  Code2,
  Radar,
  Plus,
  Activity,
  ChevronRight,
} from 'lucide-react';
import {
  Card,
  StatCard,
  KPICard,
  Button,
  SearchInput,
  CategoryBadge,
} from '@/app/components/ui';

interface DashboardStats {
  total_apis: number;
  total_endpoints: number;
  total_organizations: number;
  technologies_detected: number;
  public_apis: number;
  recently_updated: number;
  avg_security_score: number;
  avg_latency_ms: number;
  method_distribution: Array<{ method: string; count: number }>;
  auth_distribution: Array<{ auth_type: string; count: number }>;
  top_categories: Array<{ category: string; count: number }>;
  top_technologies: Array<{ technology: string; category: string; count: number }>;
  top_organizations: Array<{ name: string; logo_url: string; api_count: number }>;
  security_breakdown: { high: number; medium: number; low: number; unrated: number };
}

async function fetchDashboardStats(): Promise<DashboardStats | null> {
  try {
    const response = await fetch('/api/v2/stats/dashboard');
    if (!response.ok) return null;
    return await response.json();
  } catch {
    return null;
  }
}

const mockStats: DashboardStats = {
  total_apis: 127,
  total_endpoints: 2843,
  total_organizations: 89,
  technologies_detected: 156,
  public_apis: 112,
  recently_updated: 23,
  avg_security_score: 78,
  avg_latency_ms: 142,
  method_distribution: [
    { method: 'GET', count: 1842 },
    { method: 'POST', count: 612 },
    { method: 'PUT', count: 234 },
    { method: 'DELETE', count: 123 },
    { method: 'PATCH', count: 32 },
  ],
  auth_distribution: [
    { auth_type: 'apiKey', count: 892 },
    { auth_type: 'bearer', count: 756 },
    { auth_type: 'none', count: 654 },
    { auth_type: 'basic', count: 298 },
    { auth_type: 'oauth2', count: 243 },
  ],
  top_categories: [
    { category: 'payment', count: 34 },
    { category: 'social', count: 28 },
    { category: 'ai', count: 22 },
    { category: 'analytics', count: 18 },
    { category: 'communication', count: 15 },
    { category: 'storage', count: 12 },
    { category: 'devtools', count: 10 },
    { category: 'commerce', count: 8 },
  ],
  top_technologies: [
    { technology: 'Node.js', category: 'backend', count: 156 },
    { technology: 'Python', category: 'backend', count: 134 },
    { technology: 'Express', category: 'backend', count: 98 },
    { technology: 'Django', category: 'backend', count: 67 },
    { technology: 'FastAPI', category: 'backend', count: 54 },
  ],
  top_organizations: [
    { name: 'Stripe', logo_url: '', api_count: 12 },
    { name: 'GitHub', logo_url: '', api_count: 9 },
    { name: 'Twilio', logo_url: '', api_count: 8 },
    { name: 'OpenAI', logo_url: '', api_count: 7 },
    { name: 'AWS', logo_url: '', api_count: 6 },
  ],
  security_breakdown: {
    high: 1423,
    medium: 876,
    low: 312,
    unrated: 232,
  },
};

const recentActivity = [
  { id: 1, type: 'api', action: 'Stripe API updated', time: '2 hours ago', color: 'emerald' },
  { id: 2, type: 'endpoint', action: 'New endpoint discovered in OpenAI API', time: '3 hours ago', color: 'purple' },
  { id: 3, type: 'scan', action: 'Scan completed: api.github.com', time: '5 hours ago', color: 'blue' },
  { id: 4, type: 'security', action: 'Security alert: expiring certificate', time: '1 day ago', color: 'amber' },
  { id: 5, type: 'api', action: 'GitHub API v3 documentation updated', time: '1 day ago', color: 'gray' },
];

const quickActions = [
  { label: 'New Scan', icon: Radar, href: '/scan', color: 'blue' },
  { label: 'Add API', icon: Plus, href: '/explorer?action=add', color: 'emerald' },
  { label: 'View Reports', icon: Database, href: '/reports', color: 'purple' },
];

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadStats = async () => {
      const data = await fetchDashboardStats();
      setStats(data || mockStats);
      setLoading(false);
    };
    const timer = setTimeout(loadStats, 500);
    return () => clearTimeout(timer);
  }, []);

  const displayStats = stats || mockStats;

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-text-primary">Dashboard</h1>
          <p className="text-text-secondary mt-1">
            Overview of your API ecosystem
          </p>
        </div>
        <div className="flex items-center gap-3">
          <SearchInput placeholder="Quick search..." className="w-64" />
          <Link href="/scan">
            <Button icon={Radar}>Start Scan</Button>
          </Link>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <KPICard label="Total APIs" value={displayStats.total_apis} change={12} changeLabel="vs last month" icon={<Database className="w-5 h-5" />} loading={loading} />
        <KPICard label="Active Endpoints" value={displayStats.total_endpoints.toLocaleString()} change={8} changeLabel="vs last month" icon={<Code2 className="w-5 h-5" />} loading={loading} />
        <KPICard label="Organizations" value={displayStats.total_organizations} change={5} changeLabel="vs last month" icon={<Building2 className="w-5 h-5" />} loading={loading} />
        <KPICard label="Technologies" value={displayStats.technologies_detected} change={15} changeLabel="vs last month" icon={<Cpu className="w-5 h-5" />} loading={loading} />
      </div>

      {/* Secondary Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        <StatCard label="Public APIs" value={displayStats.public_apis} change={3} changeLabel="new this week" icon={<Globe className="w-5 h-5" />} loading={loading} />
        <StatCard label="Recently Updated" value={displayStats.recently_updated} change={-2} changeLabel="vs last week" icon={<Clock className="w-5 h-5" />} loading={loading} />
        <StatCard label="Avg Security Score" value={`${displayStats.avg_security_score}%`} change={2} changeLabel="vs last month" icon={<Shield className="w-5 h-5" />} loading={loading} />
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Methods Distribution */}
        <Card padding="lg" className="lg:col-span-2">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-text-primary">API Methods Distribution</h2>
            <Link href="/analytics" className="text-sm text-accent-blue hover:underline flex items-center gap-1">
              View all <ChevronRight className="w-4 h-4" />
            </Link>
          </div>
          <div className="grid grid-cols-5 gap-4">
            {displayStats.method_distribution.map((item) => {
              const total = displayStats.method_distribution.reduce((sum, m) => sum + m.count, 0);
              const percentage = Math.round((item.count / total) * 100);
              return (
                <div key={item.method} className="text-center">
                  <span className={`inline-block px-2 py-1 text-xs font-bold rounded-md ${
                    item.method === 'GET' ? 'bg-emerald-50 text-emerald-600' :
                    item.method === 'POST' ? 'bg-blue-50 text-blue-600' :
                    item.method === 'PUT' ? 'bg-amber-50 text-amber-600' :
                    item.method === 'DELETE' ? 'bg-red-50 text-red-600' :
                    'bg-purple-50 text-purple-600'
                  }`}>
                    {item.method}
                  </span>
                  <p className="text-2xl font-bold text-text-primary mt-2">{item.count}</p>
                  <p className="text-xs text-text-tertiary">{percentage}%</p>
                </div>
              );
            })}
          </div>
          <div className="mt-6 space-y-3">
            {displayStats.method_distribution.map((item) => {
              const total = displayStats.method_distribution.reduce((sum, m) => sum + m.count, 0);
              const percentage = (item.count / total) * 100;
              return (
                <div key={item.method} className="flex items-center gap-3">
                  <span className="w-16 text-xs font-medium text-text-secondary">{item.method}</span>
                  <div className="flex-1 h-6 bg-bg-secondary rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full ${
                        item.method === 'GET' ? 'bg-emerald-500' :
                        item.method === 'POST' ? 'bg-blue-500' :
                        item.method === 'PUT' ? 'bg-amber-500' :
                        item.method === 'DELETE' ? 'bg-red-500' : 'bg-purple-500'
                      }`}
                      style={{ width: `${percentage}%` }}
                    />
                  </div>
                  <span className="w-12 text-xs text-text-tertiary text-right">{percentage}%</span>
                </div>
              );
            })}
          </div>
        </Card>

        {/* Quick Actions */}
        <Card padding="lg">
          <h2 className="text-lg font-semibold text-text-primary mb-4">Quick Actions</h2>
          <div className="space-y-3">
            {quickActions.map((action) => (
              <Link key={action.label} href={action.href}>
                <Card hover className="flex items-center gap-3">
                  <div className={`p-2 rounded-lg bg-${action.color}-50 text-${action.color}-600`}>
                    <action.icon className="w-5 h-5" />
                  </div>
                  <span className="font-medium text-text-primary">{action.label}</span>
                  <ChevronRight className="w-4 h-4 text-text-tertiary ml-auto" />
                </Card>
              </Link>
            ))}
          </div>
          <div className="mt-6 pt-6 border-t border-border">
            <h3 className="text-sm font-semibold text-text-primary mb-3">Top APIs</h3>
            <div className="space-y-2">
              {displayStats.top_organizations.slice(0, 5).map((org) => (
                <Link key={org.name} href={`/explorer?org=${org.name}`}>
                  <div className="flex items-center gap-3 p-2 rounded-lg hover:bg-bg-secondary transition-colors">
                    <div className="w-8 h-8 rounded-full bg-gradient-to-br from-accent-blue to-accent-cyan flex items-center justify-center text-white text-xs font-bold">
                      {org.name.charAt(0)}
                    </div>
                    <span className="text-sm text-text-primary">{org.name}</span>
                    <span className="text-xs text-text-tertiary ml-auto">{org.api_count} APIs</span>
                  </div>
                </Link>
              ))}
            </div>
          </div>
        </Card>
      </div>

      {/* Bottom Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Activity */}
        <Card padding="lg">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-text-primary">Recent Activity</h2>
            <span className="flex items-center gap-1.5 text-xs text-accent-green">
              <span className="w-2 h-2 rounded-full bg-accent-green animate-pulse-dot" />
              Live
            </span>
          </div>
          <div className="space-y-4">
            {recentActivity.map((activity) => (
              <div key={activity.id} className="flex items-start gap-3">
                <div className={`w-8 h-8 rounded-full flex items-center justify-center bg-${activity.color}-50 text-${activity.color}-600`}>
                  <Activity className="w-4 h-4" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-text-primary">{activity.action}</p>
                  <p className="text-xs text-text-tertiary">{activity.time}</p>
                </div>
              </div>
            ))}
          </div>
        </Card>

        {/* Top Categories */}
        <Card padding="lg">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-text-primary">API Categories</h2>
            <Link href="/analytics" className="text-sm text-accent-blue hover:underline flex items-center gap-1">
              Analytics <ChevronRight className="w-4 h-4" />
            </Link>
          </div>
          <div className="space-y-3">
            {displayStats.top_categories.map((cat) => {
              const maxCount = Math.max(...displayStats.top_categories.map(c => c.count));
              const percentage = (cat.count / maxCount) * 100;
              return (
                <div key={cat.category} className="flex items-center gap-3">
                  <div className="w-24">
                    <CategoryBadge category={cat.category} />
                  </div>
                  <div className="flex-1 h-8 bg-bg-secondary rounded-lg overflow-hidden">
                    <div className="h-full bg-gradient-to-r from-accent-blue to-accent-cyan rounded-lg" style={{ width: `${percentage}%` }} />
                  </div>
                  <span className="w-8 text-sm text-text-secondary text-right">{cat.count}</span>
                </div>
              );
            })}
          </div>
        </Card>
      </div>

      {/* Security Overview */}
      <Card padding="lg">
        <h2 className="text-lg font-semibold text-text-primary mb-4">Security Overview</h2>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div className="text-center p-4 rounded-lg bg-emerald-50 border border-emerald-100">
            <p className="text-3xl font-bold text-emerald-600">{displayStats.security_breakdown.high}</p>
            <p className="text-sm text-emerald-600 mt-1">High Security</p>
            <p className="text-xs text-emerald-600/60">Score ≥ 80</p>
          </div>
          <div className="text-center p-4 rounded-lg bg-amber-50 border border-amber-100">
            <p className="text-3xl font-bold text-amber-600">{displayStats.security_breakdown.medium}</p>
            <p className="text-sm text-amber-600 mt-1">Medium Security</p>
            <p className="text-xs text-amber-600/60">Score 50-79</p>
          </div>
          <div className="text-center p-4 rounded-lg bg-red-50 border border-red-100">
            <p className="text-3xl font-bold text-red-600">{displayStats.security_breakdown.low}</p>
            <p className="text-sm text-red-600 mt-1">Low Security</p>
            <p className="text-xs text-red-600/60">Score < 50</p>
          </div>
          <div className="text-center p-4 rounded-lg bg-gray-100 border border-gray-200">
            <p className="text-3xl font-bold text-gray-600">{displayStats.security_breakdown.unrated}</p>
            <p className="text-sm text-gray-600 mt-1">Unrated</p>
            <p className="text-xs text-gray-500">Not scanned</p>
          </div>
        </div>
      </Card>
    </div>
  );
}