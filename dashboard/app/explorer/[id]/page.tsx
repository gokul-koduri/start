'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import {
  ArrowLeft,
  ExternalLink,
  Copy,
  Star,
  Shield,
  Clock,
  Lock,
  Globe,
  Zap,
  Play,
  ChevronRight,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Loader2,
} from 'lucide-react';
import {
  Card,
  Button,
  MethodBadge,
  StatusBadge,
  SecurityBadge,
  TagBadge,
  Collapsible,
  Tabs,
  TabList,
  TabTrigger,
  TabContent,
  Select,
} from '@/app/components/ui';

interface Endpoint {
  id: number;
  registry_id: number;
  method: string;
  path: string;
  full_url: string;
  summary: string;
  auth_type: string;
  rate_limit: string;
  status: string;
  latency_ms: number;
  security_score: number;
  tags: string[];
}

interface APIRegistry {
  id: number;
  name: string;
  organization_name: string;
  base_url: string;
  documentation_url: string;
  api_version: string;
  category: string;
  description: string;
  popularity_score: number;
  endpoint_count: number;
  tags: string[];
}

interface TestResult {
  status_code: number;
  headers: Record<string, string>;
  body: string;
  latency_ms: number;
  success: boolean;
  error?: string;
}

export default function APIDetailsPage() {
  const params = useParams();
  const apiId = params.id as string;

  const [api, setAPI] = useState<APIRegistry | null>(null);
  const [endpoints, setEndpoints] = useState<Endpoint[]>([]);
  const [loading, setLoading] = useState(true);

  // Test panel state
  const [testMethod, setTestMethod] = useState('GET');
  const [testUrl, setTestUrl] = useState('');
  const [testHeaders, setTestHeaders] = useState('');
  const [testBody, setTestBody] = useState('');
  const [testResult, setTestResult] = useState<TestResult | null>(null);
  const [testing, setTesting] = useState(false);

  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      try {
        const response = await fetch(`/api/v2/apis/${apiId}`);
        if (response.ok) {
          const data = await response.json();
          setAPI(data);

          const epResponse = await fetch(`/api/v2/apis/${apiId}/endpoints`);
          if (epResponse.ok) {
            const epData = await epResponse.json();
            setEndpoints(epData.endpoints || []);
          }
        }
      } catch (error) {
        console.error("Failed to load API:", error);
      }
      setLoading(false);
    };

    loadData();
  }, [apiId]);

  const handleTest = async () => {
    setTesting(true);
    setTestResult(null);

    try {
      const response = await fetch('/api/v2/endpoints/test', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          method: testMethod,
          url: testUrl,
          headers: testHeaders ? JSON.parse(testHeaders) : {},
          body: testBody || undefined,
        }),
      });

      const result = await response.json();
      setTestResult(result);
    } catch (error) {
      setTestResult({
        status_code: 0,
        headers: {},
        body: '',
        latency_ms: 0,
        success: false,
        error: String(error),
      });
    }

    setTesting(false);
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
  };

  const generateCurl = () => {
    let curl = `curl -X ${testMethod} "${testUrl}"`;
    if (testHeaders) {
      try {
        const headers = JSON.parse(testHeaders);
        Object.entries(headers).forEach(([key, value]) => {
          curl += ` \\\n  -H "${key}: ${value}"`;
        });
      } catch {}
    }
    if (testBody) {
      curl += ` \\\n  -d '${testBody}'`;
    }
    return curl;
  };

  // Mock data for demo
  const mockAPI: APIRegistry = {
    id: parseInt(apiId),
    name: 'Stripe API',
    organization_name: 'Stripe',
    base_url: 'https://api.stripe.com',
    documentation_url: 'https://stripe.com/docs/api',
    api_version: 'v1',
    category: 'payment',
    description: 'The Stripe API is organized around REST. Our API has predictable resource-oriented URLs, accepts JSON-encoded request bodies, returns JSON-encoded responses, and uses standard HTTP response codes, authentication, and verbs.',
    popularity_score: 98,
    endpoint_count: 156,
    tags: ['payment', 'billing', 'subscriptions', 'invoicing'],
  };

  const mockEndpoints: Endpoint[] = [
    { id: 1, registry_id: parseInt(apiId), method: 'GET', path: '/v1/charges', full_url: 'https://api.stripe.com/v1/charges', summary: 'Returns a list of charges', auth_type: 'bearer', rate_limit: '100/min', status: 'active', latency_ms: 120, security_score: 92, tags: [] },
    { id: 2, registry_id: parseInt(apiId), method: 'POST', path: '/v1/charges', full_url: 'https://api.stripe.com/v1/charges', summary: 'Creates a new charge', auth_type: 'bearer', rate_limit: '100/min', status: 'active', latency_ms: 145, security_score: 95, tags: [] },
    { id: 3, registry_id: parseInt(apiId), method: 'GET', path: '/v1/customers', full_url: 'https://api.stripe.com/v1/customers', summary: 'Returns a list of customers', auth_type: 'bearer', rate_limit: '100/min', status: 'active', latency_ms: 98, security_score: 90, tags: [] },
    { id: 4, registry_id: parseInt(apiId), method: 'POST', path: '/v1/customers', full_url: 'https://api.stripe.com/v1/customers', summary: 'Creates a new customer', auth_type: 'bearer', rate_limit: '100/min', status: 'active', latency_ms: 134, security_score: 88, tags: [] },
    { id: 5, registry_id: parseInt(apiId), method: 'GET', path: '/v1/subscriptions', full_url: 'https://api.stripe.com/v1/subscriptions', summary: 'Returns a list of subscriptions', auth_type: 'bearer', rate_limit: '100/min', status: 'active', latency_ms: 110, security_score: 94, tags: [] },
    { id: 6, registry_id: parseInt(apiId), method: 'POST', path: '/v1/payment_intents', full_url: 'https://api.stripe.com/v1/payment_intents', summary: 'Creates a payment intent', auth_type: 'bearer', rate_limit: '100/min', status: 'active', latency_ms: 156, security_score: 96, tags: [] },
  ];

  const displayAPI = loading ? mockAPI : (api || mockAPI);
  const displayEndpoints = loading ? mockEndpoints : (endpoints.length > 0 ? endpoints : mockEndpoints);

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Back Navigation */}
      <Link href="/explorer" className="inline-flex items-center gap-2 text-text-secondary hover:text-accent-blue transition-colors">
        <ArrowLeft className="w-4 h-4" />
        Back to API Explorer
      </Link>

      {/* API Overview */}
      <Card padding="lg">
        <div className="flex flex-col lg:flex-row lg:items-start justify-between gap-4">
          <div className="flex items-start gap-4">
            <div className="w-16 h-16 rounded-xl bg-gradient-to-br from-accent-blue to-accent-cyan flex items-center justify-center text-white font-bold text-xl">
              {displayAPI.name.charAt(0)}
            </div>
            <div>
              <h1 className="text-2xl font-bold text-text-primary">{displayAPI.name}</h1>
              <p className="text-text-secondary mt-1">{displayAPI.organization_name}</p>
              <div className="flex items-center gap-2 mt-2">
                <StatusBadge status="active" />
                <TagBadge variant="blue">{displayAPI.category}</TagBadge>
                <span className="text-sm text-text-tertiary">v{displayAPI.api_version}</span>
              </div>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="ghost" icon={Star}>Favorite</Button>
            <Button variant="outline" icon={ExternalLink}>Documentation</Button>
          </div>
        </div>

        <p className="mt-6 text-text-secondary">{displayAPI.description}</p>

        {/* Quick Stats */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mt-6">
          <div className="p-4 bg-bg-secondary rounded-lg">
            <p className="text-sm text-text-secondary">Endpoints</p>
            <p className="text-2xl font-bold text-text-primary">{displayAPI.endpoint_count}</p>
          </div>
          <div className="p-4 bg-bg-secondary rounded-lg">
            <p className="text-sm text-text-secondary">Security Score</p>
            <div className="flex items-center gap-2">
              <p className="text-2xl font-bold text-emerald-600">94</p>
              <Shield className="w-5 h-5 text-emerald-600" />
            </div>
          </div>
          <div className="p-4 bg-bg-secondary rounded-lg">
            <p className="text-sm text-text-secondary">Popularity</p>
            <p className="text-2xl font-bold text-text-primary">{displayAPI.popularity_score}/100</p>
          </div>
          <div className="p-4 bg-bg-secondary rounded-lg">
            <p className="text-sm text-text-secondary">Rate Limit</p>
            <p className="text-2xl font-bold text-text-primary">100/min</p>
          </div>
        </div>

        {/* Base URL */}
        <div className="mt-6 p-4 bg-bg-secondary rounded-lg flex items-center justify-between">
          <div>
            <p className="text-sm text-text-secondary">Base URL</p>
            <p className="font-mono text-text-primary">{displayAPI.base_url}</p>
          </div>
          <Button
            variant="ghost"
            icon={Copy}
            onClick={() => copyToClipboard(displayAPI.base_url)}
          >
            Copy
          </Button>
        </div>
      </Card>

      {/* Main Content */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Endpoints List */}
        <div className="lg:col-span-2 space-y-4">
          <Card padding="none">
            <div className="p-4 border-b border-border">
              <h2 className="text-lg font-semibold text-text-primary">Endpoints ({displayEndpoints.length})</h2>
            </div>
            <div className="divide-y divide-border">
              {displayEndpoints.map((endpoint) => (
                <div
                  key={endpoint.id}
                  className="p-4 hover:bg-bg-secondary transition-colors cursor-pointer"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-3">
                      <MethodBadge method={endpoint.method} />
                      <div>
                        <p className="font-mono text-sm text-text-primary">{endpoint.path}</p>
                        <p className="text-xs text-text-tertiary mt-0.5">{endpoint.summary}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-3 text-sm text-text-tertiary">
                      <span className="flex items-center gap-1">
                        <Clock className="w-3.5 h-3.5" />
                        {endpoint.latency_ms}ms
                      </span>
                      <SecurityBadge score={endpoint.security_score} showValue={false} />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </Card>

          {/* Security Overview */}
          <Card padding="lg">
            <h2 className="text-lg font-semibold text-text-primary mb-4">Security Overview</h2>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
              <div className="flex items-center gap-3 p-3 bg-emerald-50 rounded-lg border border-emerald-100">
                <CheckCircle className="w-5 h-5 text-emerald-600" />
                <div>
                  <p className="font-medium text-emerald-600">HTTPS</p>
                  <p className="text-xs text-emerald-600/80">Enabled</p>
                </div>
              </div>
              <div className="flex items-center gap-3 p-3 bg-emerald-50 rounded-lg border border-emerald-100">
                <Lock className="w-5 h-5 text-emerald-600" />
                <div>
                  <p className="font-medium text-emerald-600">TLS 1.3</p>
                  <p className="text-xs text-emerald-600/80">Encrypted</p>
                </div>
              </div>
              <div className="flex items-center gap-3 p-3 bg-emerald-50 rounded-lg border border-emerald-100">
                <Shield className="w-5 h-5 text-emerald-600" />
                <div>
                  <p className="font-medium text-emerald-600">CORS</p>
                  <p className="text-xs text-emerald-600/80">Configured</p>
                </div>
              </div>
            </div>

            <div className="mt-4 p-4 bg-bg-secondary rounded-lg">
              <h3 className="font-medium text-text-primary mb-2">Rate Limiting</h3>
              <p className="text-sm text-text-secondary">
                This API enforces rate limits of 100 requests per minute per access token.
                Exceeding this limit will result in a 429 Too Many Requests response.
              </p>
            </div>
          </Card>
        </div>

        {/* Interactive Testing Panel */}
        <div className="lg:col-span-1">
          <Card padding="none" className="sticky top-6">
            <div className="p-4 border-b border-border bg-gradient-to-r from-accent-blue to-accent-cyan">
              <h2 className="text-lg font-semibold text-white flex items-center gap-2">
                <Zap className="w-5 h-5" />
                Test Endpoint
              </h2>
            </div>

            <div className="p-4 space-y-4">
              {/* Method & URL */}
              <div>
                <label className="block text-sm font-medium text-text-primary mb-1.5">Request URL</label>
                <div className="flex gap-2">
                  <select
                    value={testMethod}
                    onChange={(e) => setTestMethod(e.target.value)}
                    className="px-3 py-2 bg-bg-secondary border border-border rounded-lg text-sm font-medium"
                  >
                    <option value="GET">GET</option>
                    <option value="POST">POST</option>
                    <option value="PUT">PUT</option>
                    <option value="PATCH">PATCH</option>
                    <option value="DELETE">DELETE</option>
                  </select>
                  <input
                    type="text"
                    value={testUrl || displayAPI.base_url}
                    onChange={(e) => setTestUrl(e.target.value)}
                    placeholder="https://api.example.com/endpoint"
                    className="flex-1 px-3 py-2 bg-surface-card border border-border rounded-lg text-sm"
                  />
                </div>
              </div>

              {/* Headers (Expandable) */}
              <Collapsible title="Headers" defaultOpen={false}>
                <textarea
                  value={testHeaders}
                  onChange={(e) => setTestHeaders(e.target.value)}
                  placeholder='{"Authorization": "Bearer sk_test_...", "Content-Type": "application/json"}'
                  rows={3}
                  className="w-full px-3 py-2 text-sm bg-surface-card border border-border rounded-lg font-mono resize-none"
                />
              </Collapsible>

              {/* Body (Expandable) */}
              {testMethod !== 'GET' && (
                <Collapsible title="Request Body" defaultOpen={false}>
                  <textarea
                    value={testBody}
                    onChange={(e) => setTestBody(e.target.value)}
                    placeholder='{"key": "value"}'
                    rows={4}
                    className="w-full px-3 py-2 text-sm bg-surface-card border border-border rounded-lg font-mono resize-none"
                  />
                </Collapsible>
              )}

              {/* Test Button */}
              <Button
                onClick={handleTest}
                loading={testing}
                fullWidth
                icon={Play}
                className="bg-gradient-to-r from-accent-blue to-accent-cyan"
              >
                {testing ? 'Testing...' : 'Send Request'}
              </Button>

              {/* Result */}
              {testResult && (
                <div className="mt-4 space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-text-primary">Response</span>
                    <div className="flex items-center gap-2">
                      {testResult.success ? (
                        <span className="flex items-center gap-1 text-emerald-600 text-sm">
                          <CheckCircle className="w-4 h-4" />
                          {testResult.status_code}
                        </span>
                      ) : (
                        <span className="flex items-center gap-1 text-red-600 text-sm">
                          <XCircle className="w-4 h-4" />
                          Error
                        </span>
                      )}
                      <span className="text-sm text-text-tertiary">{testResult.latency_ms}ms</span>
                    </div>
                  </div>

                  <div className="p-3 bg-bg-secondary rounded-lg border border-border">
                    <pre className="text-xs text-text-secondary overflow-auto max-h-48 font-mono">
                      {testResult.success ? (
                        testResult.body.slice(0, 1000) || 'Empty response body'
                      ) : (
                        testResult.error || 'Request failed'
                      )}
                    </pre>
                  </div>

                  {/* Code Snippet */}
                  <div>
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs font-medium text-text-secondary">cURL</span>
                      <Button
                        variant="ghost"
                        size="sm"
                        icon={Copy}
                        onClick={() => copyToClipboard(generateCurl())}
                      >
                        Copy
                      </Button>
                    </div>
                    <pre className="p-3 bg-bg-tertiary rounded-lg text-xs font-mono text-text-secondary overflow-auto">
                      {generateCurl()}
                    </pre>
                  </div>
                </div>
              )}
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}