'use client';

import { useState } from 'react';
import {
  Radar,
  Search,
  Globe,
  Link2,
  Server,
  Loader2,
  CheckCircle,
  XCircle,
  Clock,
  AlertTriangle,
  ChevronRight,
  RefreshCw,
  Plus,
} from 'lucide-react';
import {
  Card,
  Button,
  Input,
  Select,
  Collapsible,
  Progress,
} from '@/app/components/ui';

interface ScanResult {
  id: number;
  type: 'discovered' | 'technology' | 'subdomain' | 'endpoint';
  message: string;
  details?: string;
}

interface ScanJob {
  id: number;
  target: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  progress: number;
  logs: Array<{ level: string; message: string; timestamp: string }>;
  results: ScanResult[];
}

const mockScans: ScanJob[] = [
  {
    id: 1,
    target: 'https://api.stripe.com',
    status: 'completed',
    progress: 100,
    logs: [
      { level: 'info', message: 'Starting scan...', timestamp: '2024-01-25T10:00:00Z' },
      { level: 'success', message: 'HTTPS enabled', timestamp: '2024-01-25T10:00:01Z' },
      { level: 'info', message: 'Discovered 156 endpoints', timestamp: '2024-01-25T10:00:15Z' },
    ],
    results: [
      { id: 1, type: 'endpoint', message: 'GET /v1/charges', details: '156 endpoints found' },
      { id: 2, type: 'technology', message: 'Node.js + Express', details: 'Backend stack detected' },
    ],
  },
  {
    id: 2,
    target: 'https://api.github.com',
    status: 'running',
    progress: 65,
    logs: [
      { level: 'info', message: 'Starting scan...', timestamp: '2024-01-25T10:05:00Z' },
      { level: 'info', message: 'Probing endpoints...', timestamp: '2024-01-25T10:05:05Z' },
    ],
    results: [],
  },
];

export default function ScanPage() {
  const [target, setTarget] = useState('');
  const [scanType, setScanType] = useState('full');
  const [activeScan, setActiveScan] = useState<ScanJob | null>(null);
  const [scans, setScans] = useState<ScanJob[]>(mockScans);
  const [running, setRunning] = useState(false);
  const [depth, setDepth] = useState('2');

  const [options, setOptions] = useState({
    discoverEndpoints: true,
    detectTechnologies: true,
    findSubdomains: false,
    checkSecurity: true,
  });

  const startScan = async () => {
    if (!target) return;

    setRunning(true);

    // Simulate scan job
    const newScan: ScanJob = {
      id: Date.now(),
      target,
      status: 'running',
      progress: 0,
      logs: [{ level: 'info', message: `Starting scan of ${target}...`, timestamp: new Date().toISOString() }],
      results: [],
    };

    setActiveScan(newScan);
    setScans(prev => [newScan, ...prev]);

    // Simulate progress
    let progress = 0;
    const interval = setInterval(() => {
      progress += 10;
      setActiveScan(prev => prev ? { ...prev, progress: Math.min(progress, 100) } : null);
      setScans(prev => prev.map(s => s.id === newScan.id ? { ...s, progress: Math.min(progress, 100) } : s));

      if (progress >= 100) {
        clearInterval(interval);
        setActiveScan(prev => prev ? { ...prev, status: 'completed', progress: 100 } : null);
        setScans(prev => prev.map(s => s.id === newScan.id ? { ...s, status: 'completed' } : s));
        setRunning(false);
      }
    }, 500);
  };

  const getLogIcon = (level: string) => {
    switch (level) {
      case 'success': return <CheckCircle className="w-4 h-4 text-emerald-500" />;
      case 'error': return <XCircle className="w-4 h-4 text-red-500" />;
      case 'warning': return <AlertTriangle className="w-4 h-4 text-amber-500" />;
      default: return <Clock className="w-4 h-4 text-blue-500" />;
    }
  };

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-text-primary">Internet Scan</h1>
          <p className="text-text-secondary mt-1">
            Discover and analyze API endpoints across the internet
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="outline" icon={RefreshCw}>Scan History</Button>
          <Button icon={Plus}>New Scan</Button>
        </div>
      </div>

      {/* Scan Configuration */}
      <Card padding="lg">
        <div className="flex items-center gap-3 mb-6">
          <div className="p-2 rounded-lg bg-accent-blue/10">
            <Radar className="w-6 h-6 text-accent-blue" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-text-primary">Configure Scan</h2>
            <p className="text-sm text-text-secondary">Set up your target and options</p>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Target Input */}
          <div>
            <label className="block text-sm font-medium text-text-primary mb-1.5">
              Target URL or Domain
            </label>
            <div className="flex gap-2">
              <Input
                value={target}
                onChange={(e) => setTarget(e.target.value)}
                placeholder="https://api.example.com"
                icon={Globe}
                className="flex-1"
              />
            </div>
            <div className="flex gap-4 mt-3">
              <label className="flex items-center gap-2 text-sm text-text-secondary">
                <input type="radio" name="scanType" checked={scanType === 'quick'} onChange={() => setScanType('quick')} />
                Quick Scan
              </label>
              <label className="flex items-center gap-2 text-sm text-text-secondary">
                <input type="radio" name="scanType" checked={scanType === 'full'} onChange={() => setScanType('full')} />
                Full Scan
              </label>
              <label className="flex items-center gap-2 text-sm text-text-secondary">
                <input type="radio" name="scanType" checked={scanType === 'deep'} onChange={() => setScanType('deep')} />
                Deep Dive
              </label>
            </div>
          </div>

          {/* Options */}
          <div>
            <label className="block text-sm font-medium text-text-primary mb-1.5">
              Scan Options
            </label>
            <div className="space-y-2">
              <label className="flex items-center gap-2 text-sm text-text-secondary">
                <input
                  type="checkbox"
                  checked={options.discoverEndpoints}
                  onChange={(e) => setOptions({ ...options, discoverEndpoints: e.target.checked })}
                  className="rounded border-border"
                />
                Discover API endpoints
              </label>
              <label className="flex items-center gap-2 text-sm text-text-secondary">
                <input
                  type="checkbox"
                  checked={options.detectTechnologies}
                  onChange={(e) => setOptions({ ...options, detectTechnologies: e.target.checked })}
                  className="rounded border-border"
                />
                Detect Technologies
              </label>
              <label className="flex items-center gap-2 text-sm text-text-secondary">
                <input
                  type="checkbox"
                  checked={options.findSubdomains}
                  onChange={(e) => setOptions({ ...options, findSubdomains: e.target.checked })}
                  className="rounded border-border"
                />
                Find Subdomains
              </label>
              <label className="flex items-center gap-2 text-sm text-text-secondary">
                <input
                  type="checkbox"
                  checked={options.checkSecurity}
                  onChange={(e) => setOptions({ ...options, checkSecurity: e.target.checked })}
                  className="rounded border-border"
                />
                Security Check
              </label>
            </div>
          </div>
        </div>

        {/* Start Button */}
        <div className="mt-6 pt-6 border-t border-border">
          <Button
            onClick={startScan}
            loading={running}
            disabled={!target}
            icon={Radar}
            className="bg-gradient-to-r from-accent-blue to-accent-cyan"
          >
            {running ? 'Scanning...' : 'Start Scan'}
          </Button>
        </div>
      </Card>

      {/* Active Scan Progress */}
      {activeScan && activeScan.status === 'running' && (
        <Card padding="lg">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <div className="relative">
                <Loader2 className="w-5 h-5 text-accent-blue animate-spin" />
              </div>
              <div>
                <h3 className="font-medium text-text-primary">Scanning {activeScan.target}</h3>
                <p className="text-sm text-text-secondary">This may take a few minutes...</p>
              </div>
            </div>
            <span className="text-2xl font-bold text-accent-blue">{activeScan.progress}%</span>
          </div>
          <Progress value={activeScan.progress} color="blue" />
        </Card>
      )}

      {/* Live Logs */}
      {activeScan && (
        <Card padding="none">
          <div className="p-4 border-b border-border">
            <h2 className="text-lg font-semibold text-text-primary flex items-center gap-2">
              <Server className="w-5 h-5" />
              Live Logs
            </h2>
          </div>
          <div className="max-h-64 overflow-y-auto p-4 space-y-2 font-mono text-sm">
            {(activeScan.logs || []).map((log, idx) => (
              <div key={idx} className="flex items-start gap-2">
                {getLogIcon(log.level)}
                <span className="text-text-tertiary">{new Date(log.timestamp).toLocaleTimeString()}</span>
                <span className="text-text-primary">{log.message}</span>
              </div>
            ))}
            {running && (
              <div className="flex items-center gap-2 text-text-tertiary">
                <Loader2 className="w-4 h-4 animate-spin" />
                Probing endpoints...
              </div>
            )}
          </div>
        </Card>
      )}

      {/* Recent Scans */}
      <Card padding="none">
        <div className="p-4 border-b border-border">
          <h2 className="text-lg font-semibold text-text-primary">Recent Scans</h2>
        </div>
        <div className="divide-y divide-border">
          {scans.map((scan) => (
            <div key={scan.id} className="p-4 hover:bg-bg-secondary transition-colors">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  {scan.status === 'completed' ? (
                    <CheckCircle className="w-5 h-5 text-emerald-500" />
                  ) : scan.status === 'running' ? (
                    <Loader2 className="w-5 h-5 text-blue-500 animate-spin" />
                  ) : scan.status === 'failed' ? (
                    <XCircle className="w-5 h-5 text-red-500" />
                  ) : (
                    <Clock className="w-5 h-5 text-text-tertiary" />
                  )}
                  <div>
                    <p className="font-medium text-text-primary">{scan.target}</p>
                    <p className="text-sm text-text-tertiary">
                      {scan.status === 'running' ? `${scan.progress}% complete` : `Status: ${scan.status}`}
                    </p>
                  </div>
                </div>
                <Button variant="ghost" icon={ChevronRight}>View Results</Button>
              </div>
              {scan.status === 'running' && (
                <div className="mt-3">
                  <Progress value={scan.progress} size="sm" />
                </div>
              )}
            </div>
          ))}
        </div>
      </Card>

      {/* Quick Start Templates */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {[
          { name: 'Stripe API', url: 'https://api.stripe.com', desc: 'Payment APIs' },
          { name: 'GitHub API', url: 'https://api.github.com', desc: 'Version Control' },
          { name: 'OpenAI API', url: 'https://api.openai.com', desc: 'AI/ML APIs' },
        ].map((template) => (
          <Card
            key={template.name}
            hover
            padding="md"
            className="cursor-pointer"
            onClick={() => setTarget(template.url)}
          >
            <div className="flex items-start gap-3">
              <div className="p-2 rounded-lg bg-bg-secondary">
                <Link2 className="w-5 h-5 text-text-secondary" />
              </div>
              <div>
                <h3 className="font-medium text-text-primary">{template.name}</h3>
                <p className="text-sm text-text-tertiary">{template.desc}</p>
                <p className="text-xs text-text-tertiary mt-1 font-mono">{template.url}</p>
              </div>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}