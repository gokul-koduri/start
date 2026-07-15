'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import {
  Search,
  Filter,
  Grid,
  List,
  ChevronDown,
  X,
  ExternalLink,
  Copy,
  Star,
  MoreVertical,
  ArrowUpDown,
} from 'lucide-react';
import { Card, Button, SearchInput, Select, MethodBadge, StatusBadge, CategoryBadge, SecurityBadge, TagBadge, Collapsible, Tabs, TabList, TabTrigger, TabContent } from '@/app/components/ui';

interface APIRegistry {
  id: number;
  name: string;
  base_url: string;
  category: string;
  api_version: string;
  popularity_score: number;
  description: string;
  tags: string[];
  is_public: number;
  organization_name: string;
  endpoint_count: number;
  created_at: string;
  updated_at: string;
}

interface APIListResponse {
  apis: APIRegistry[];
  total: number;
  limit: number;
  offset: number;
  has_more: boolean;
}

async function fetchAPIs(params: {
  limit?: number;
  offset?: number;
  category?: string;
  search?: string;
}): Promise<APIListResponse | null> {
  try {
    const searchParams = new URLSearchParams();
    searchParams.set('limit', String(params.limit || 20));
    searchParams.set('offset', String(params.offset || 0));
    if (params.category) searchParams.set('category', params.category);
    if (params.search) searchParams.set('search', params.search);

    const response = await fetch(`/api/v2/apis?${searchParams}`);
    if (!response.ok) return null;
    return await response.json();
  } catch {
    return null;
  }
}

// Mock data for demo
const mockAPIs: APIRegistry[] = [
  { id: 1, name: 'Stripe API', base_url: 'https://api.stripe.com', category: 'payment', api_version: 'v1', popularity_score: 98, description: 'Online payment processing for internet businesses', tags: ['payment', 'billing', 'subscriptions'], is_public: 1, organization_name: 'Stripe', endpoint_count: 156, created_at: '2023-01-15', updated_at: '2024-01-20' },
  { id: 2, name: 'GitHub API', base_url: 'https://api.github.com', category: 'social', api_version: 'v3', popularity_score: 96, description: 'Build and integrate with GitHub', tags: ['version-control', 'collaboration'], is_public: 1, organization_name: 'GitHub', endpoint_count: 89, created_at: '2023-02-10', updated_at: '2024-01-22' },
  { id: 3, name: 'Twilio API', base_url: 'https://api.twilio.com', category: 'communication', api_version: '2010-04-01', popularity_score: 92, description: 'Programmable voice, video, and messaging', tags: ['sms', 'voice', 'messaging'], is_public: 1, organization_name: 'Twilio', endpoint_count: 67, created_at: '2023-03-05', updated_at: '2024-01-18' },
  { id: 4, name: 'OpenAI API', base_url: 'https://api.openai.com', category: 'ai', api_version: 'v1', popularity_score: 99, description: 'Access advanced AI models', tags: ['ai', 'ml', 'gpt', 'llm'], is_public: 1, organization_name: 'OpenAI', endpoint_count: 34, created_at: '2023-04-20', updated_at: '2024-01-25' },
  { id: 5, name: 'AWS API Gateway', base_url: 'https://execute-api.amazonaws.com', category: 'devtools', api_version: 'v1', popularity_score: 88, description: 'Build, deploy, and manage APIs at scale', tags: ['aws', 'cloud', 'serverless'], is_public: 1, organization_name: 'Amazon', endpoint_count: 45, created_at: '2023-05-12', updated_at: '2024-01-19' },
  { id: 6, name: 'Slack API', base_url: 'https://slack.com/api', category: 'communication', api_version: 'v1', popularity_score: 90, description: 'Build tools for the Slack platform', tags: ['messaging', 'teamwork', 'bots'], is_public: 1, organization_name: 'Slack', endpoint_count: 78, created_at: '2023-06-01', updated_at: '2024-01-15' },
  { id: 7, name: 'SendGrid API', base_url: 'https://api.sendgrid.com', category: 'communication', api_version: 'v3', popularity_score: 85, description: 'Email delivery and marketing', tags: ['email', 'marketing'], is_public: 1, organization_name: 'Twilio', endpoint_count: 56, created_at: '2023-07-08', updated_at: '2024-01-12' },
  { id: 8, name: 'Shopify Admin API', base_url: 'https://{shop}.myshopify.com/admin/api', category: 'commerce', api_version: '2024-01', popularity_score: 87, description: 'Build apps for Shopify merchants', tags: ['ecommerce', 'retail', 'pos'], is_public: 1, organization_name: 'Shopify', endpoint_count: 112, created_at: '2023-08-15', updated_at: '2024-01-24' },
];

const categories = [
  { value: '', label: 'All Categories' },
  { value: 'payment', label: 'Payment' },
  { value: 'social', label: 'Social' },
  { value: 'ai', label: 'AI & ML' },
  { value: 'analytics', label: 'Analytics' },
  { value: 'communication', label: 'Communication' },
  { value: 'storage', label: 'Storage' },
  { value: 'devtools', label: 'Developer Tools' },
  { value: 'commerce', label: 'E-Commerce' },
];

const sortOptions = [
  { value: 'popularity_score', label: 'Most Popular' },
  { value: 'name', label: 'Name (A-Z)' },
  { value: 'created_at', label: 'Recently Added' },
  { value: 'updated_at', label: 'Recently Updated' },
];

export default function ExplorerPage() {
  const [apis, setAPIs] = useState<APIRegistry[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [category, setCategory] = useState('');
  const [sortBy, setSortBy] = useState('popularity_score');
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  const [showFilters, setShowFilters] = useState(true);
  const [favorites, setFavorites] = useState<number[]>([]);

  useEffect(() => {
    const loadAPIs = async () => {
      setLoading(true);
      const data = await fetchAPIs({ search, category, limit: 20 });
      setAPIs(data?.apis || mockAPIs);
      setLoading(false);
    };
    const timer = setTimeout(loadAPIs, 300);
    return () => clearTimeout(timer);
  }, [search, category]);

  const toggleFavorite = (id: number) => {
    setFavorites(prev => prev.includes(id) ? prev.filter(f => f !== id) : [...prev, id]);
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
  };

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-text-primary">API Explorer</h1>
          <p className="text-text-secondary mt-1">
            Discover and explore {mockAPIs.length} APIs
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="outline" icon={Filter} onClick={() => setShowFilters(!showFilters)}>
            Filters
          </Button>
          <div className="flex items-center bg-bg-secondary rounded-lg border border-border">
            <button
              onClick={() => setViewMode('grid')}
              className={`p-2 ${viewMode === 'grid' ? 'bg-surface-card text-accent-blue' : 'text-text-tertiary'}`}
            >
              <Grid className="w-4 h-4" />
            </button>
            <button
              onClick={() => setViewMode('list')}
              className={`p-2 ${viewMode === 'list' ? 'bg-surface-card text-accent-blue' : 'text-text-tertiary'}`}
            >
              <List className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Search & Filters */}
      <Card padding="none" className="overflow-hidden">
        <div className="p-4 bg-bg-secondary border-b border-border">
          <SearchInput
            placeholder="Search APIs by name, description, or organization..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="max-w-xl"
          />
        </div>

        {/* Filter Panel */}
        {showFilters && (
          <div className="p-4 border-b border-border bg-bg-secondary/50">
            <div className="flex flex-wrap items-center gap-4">
              <Select
                label="Category"
                options={categories}
                value={category}
                onChange={setCategory}
                placeholder="All Categories"
                className="w-48"
              />
              <Select
                label="Sort By"
                options={sortOptions}
                value={sortBy}
                onChange={setSortBy}
                className="w-48"
              />
              {(search || category) && (
                <div className="flex items-center gap-2 ml-auto">
                  <span className="text-sm text-text-secondary">Active filters:</span>
                  {search && (
                    <TagBadge variant="blue" removable onRemove={() => setSearch('')}>
                      Search: {search}
                    </TagBadge>
                  )}
                  {category && (
                    <TagBadge variant="purple" removable onRemove={() => setCategory('')}>
                      {categories.find(c => c.value === category)?.label}
                    </TagBadge>
                  )}
                </div>
              )}
            </div>
          </div>
        )}
      </Card>

      {/* Results */}
      {loading ? (
        <div className={viewMode === 'grid' ? 'grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4' : 'space-y-3'}>
          {Array.from({ length: 6 }).map((_, i) => (
            <Card key={i} padding="lg">
              <div className="space-y-3">
                <div className="skeleton h-5 w-3/4" />
                <div className="skeleton h-4 w-full" />
                <div className="skeleton h-4 w-2/3" />
              </div>
            </Card>
          ))}
        </div>
      ) : apis.length === 0 ? (
        <Card padding="lg" className="text-center py-12">
          <Search className="w-12 h-12 text-text-tertiary mx-auto mb-4" />
          <h3 className="text-lg font-medium text-text-primary">No APIs found</h3>
          <p className="text-text-secondary mt-2">Try adjusting your search or filters</p>
          <Button variant="outline" className="mt-4" onClick={() => { setSearch(''); setCategory(''); }}>
            Clear filters
          </Button>
        </Card>
      ) : viewMode === 'grid' ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {apis.map((api) => (
            <Card key={api.id} hover className="flex flex-col">
              {/* Header */}
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-accent-blue to-accent-cyan flex items-center justify-center text-white font-bold text-sm">
                    {api.name.charAt(0)}
                  </div>
                  <div>
                    <h3 className="font-semibold text-text-primary">{api.name}</h3>
                    <p className="text-xs text-text-tertiary">{api.organization_name}</p>
                  </div>
                </div>
                <button
                  onClick={() => toggleFavorite(api.id)}
                  className={`p-1.5 rounded ${favorites.includes(api.id) ? 'text-amber-500' : 'text-text-tertiary hover:text-amber-500'}`}
                >
                  <Star className={`w-4 h-4 ${favorites.includes(api.id) ? 'fill-current' : ''}`} />
                </button>
              </div>

              {/* Description */}
              <p className="text-sm text-text-secondary line-clamp-2 mb-3 flex-1">
                {api.description}
              </p>

              {/* Badges */}
              <div className="flex flex-wrap gap-2 mb-3">
                <CategoryBadge category={api.category} />
                <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-600">
                  v{api.api_version}
                </span>
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-emerald-50 text-emerald-600">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                  Public
                </span>
              </div>

              {/* Stats */}
              <div className="flex items-center gap-4 text-xs text-text-tertiary mb-3">
                <span>{api.endpoint_count} endpoints</span>
                <span>Score: {api.popularity_score}</span>
              </div>

              {/* Tags */}
              <div className="flex flex-wrap gap-1.5 mb-4">
                {api.tags.slice(0, 3).map(tag => (
                  <span key={tag} className="px-1.5 py-0.5 text-[10px] font-medium bg-bg-tertiary text-text-secondary rounded">
                    {tag}
                  </span>
                ))}
                {api.tags.length > 3 && (
                  <span className="text-xs text-text-tertiary">+{api.tags.length - 3}</span>
                )}
              </div>

              {/* Actions */}
              <div className="flex items-center gap-2 pt-3 border-t border-border">
                <Link href={`/explorer/${api.id}`} className="flex-1">
                  <Button variant="secondary" size="sm" fullWidth>
                    View Details
                  </Button>
                </Link>
                <button
                  onClick={() => copyToClipboard(api.base_url)}
                  className="p-2 rounded-lg hover:bg-bg-secondary transition-colors"
                  title="Copy URL"
                >
                  <Copy className="w-4 h-4 text-text-tertiary" />
                </button>
              </div>
            </Card>
          ))}
        </div>
      ) : (
        <div className="space-y-2">
          {apis.map((api) => (
            <Card key={api.id} hover className="flex items-center gap-4">
              <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-accent-blue to-accent-cyan flex items-center justify-center text-white font-bold">
                {api.name.charAt(0)}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <h3 className="font-medium text-text-primary">{api.name}</h3>
                  <CategoryBadge category={api.category} />
                  <StatusBadge status="active" />
                </div>
                <p className="text-sm text-text-secondary truncate">{api.description}</p>
              </div>
              <div className="hidden md:flex items-center gap-6 text-sm text-text-tertiary">
                <span>{api.endpoint_count} endpoints</span>
                <span>{api.organization_name}</span>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => toggleFavorite(api.id)}
                  className={`p-2 rounded ${favorites.includes(api.id) ? 'text-amber-500' : 'text-text-tertiary'}`}
                >
                  <Star className={`w-4 h-4 ${favorites.includes(api.id) ? 'fill-current' : ''}`} />
                </button>
                <Link href={`/explorer/${api.id}`}>
                  <Button size="sm">View</Button>
                </Link>
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* Pagination placeholder */}
      <div className="flex items-center justify-between">
        <p className="text-sm text-text-secondary">
          Showing {apis.length} of {mockAPIs.length} results
        </p>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" disabled>
            Previous
          </Button>
          <Button variant="outline" size="sm">
            Next
          </Button>
        </div>
      </div>
    </div>
  );
}