'use client';

import { useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  LayoutDashboard,
  Search,
  Radar,
  Database,
  Building2,
  Cpu,
  Shield,
  FileText,
  Star,
  Settings,
  ChevronDown,
  ChevronRight,
  ExternalLink,
  Menu,
  X,
} from 'lucide-react';

interface NavItem {
  label: string;
  href: string;
  icon: React.ReactNode;
  badge?: string;
  children?: NavItem[];
}

const mainNavItems: NavItem[] = [
  { label: 'Dashboard', href: '/', icon: <LayoutDashboard className="w-5 h-5" /> },
  { label: 'API Explorer', href: '/explorer', icon: <Search className="w-5 h-5" /> },
  { label: 'Internet Scan', href: '/scan', icon: <Radar className="w-5 h-5" /> },
  { label: 'Endpoint Database', href: '/database', icon: <Database className="w-5 h-5" /> },
  { label: 'Organizations', href: '/organizations', icon: <Building2 className="w-5 h-5" /> },
  { label: 'Technologies', href: '/technologies', icon: <Cpu className="w-5 h-5" /> },
  { label: 'Security Status', href: '/security', icon: <Shield className="w-5 h-5" /> },
];

const secondaryNavItems: NavItem[] = [
  { label: 'Reports', href: '/reports', icon: <FileText className="w-5 h-5" /> },
  { label: 'Favorites', href: '/favorites', icon: <Star className="w-5 h-5" />, badge: '5' },
  { label: 'Settings', href: '/settings', icon: <Settings className="w-5 h-5" /> },
];

interface NavSectionProps {
  title?: string;
  items: NavItem[];
  pathname: string;
  isCollapsed: boolean;
}

function NavSection({ title, items, pathname, isCollapsed }: NavSectionProps) {
  return (
    <div className="space-y-1">
      {title && !isCollapsed && (
        <div className="px-3 mb-2 text-xs font-semibold text-text-secondary uppercase tracking-wider">
          {title}
        </div>
      )}
      {items.map((item) => {
        const isActive = pathname === item.href || pathname.startsWith(item.href + '/');
        return (
          <Link
            key={item.href}
            href={item.href}
            className={`
              group flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium
              transition-all duration-150 ease-out
              ${isActive
                ? 'bg-accent-blue text-white shadow-sm'
                : 'text-text-secondary hover:text-text-primary hover:bg-bg-secondary'
              }
              ${isCollapsed ? 'justify-center' : ''}
            `}
            title={isCollapsed ? item.label : undefined}
          >
            <span className={`${isActive ? 'text-white' : 'text-text-tertiary group-hover:text-accent-blue'} transition-colors`}>
              {item.icon}
            </span>
            {!isCollapsed && (
              <>
                <span className="flex-1">{item.label}</span>
                {item.badge && (
                  <span className="px-2 py-0.5 text-xs font-semibold rounded-full bg-accent-blue/10 text-white">
                    {item.badge}
                  </span>
                )}
              </>
            )}
          </Link>
        );
      })}
    </div>
  );
}

interface SidebarProps {
  isCollapsed?: boolean;
  onToggle?: () => void;
}

export function Sidebar({ isCollapsed = false, onToggle }: SidebarProps) {
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);

  const sidebarContent = (
    <div className={`flex flex-col h-full ${isCollapsed ? 'w-16' : 'w-64'}`}>
      {/* Logo */}
      <div className="flex items-center justify-between px-4 h-16 border-b border-border">
        {!isCollapsed ? (
          <Link href="/" className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-accent-blue to-accent-cyan flex items-center justify-center">
              <Radar className="w-5 h-5 text-white" />
            </div>
            <span className="font-semibold text-text-primary">API Explorer</span>
          </Link>
        ) : (
          <Link href="/" className="mx-auto">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-accent-blue to-accent-cyan flex items-center justify-center">
              <Radar className="w-5 h-5 text-white" />
            </div>
          </Link>
        )}
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto py-4 px-2 space-y-6">
        <NavSection items={mainNavItems} pathname={pathname} isCollapsed={isCollapsed} />

        <div className="h-px bg-border mx-2" />

        <NavSection items={secondaryNavItems} pathname={pathname} isCollapsed={isCollapsed} />
      </nav>

      {/* Footer */}
      {!isCollapsed && (
        <div className="p-4 border-t border-border">
          <div className="card p-3 bg-gradient-to-br from-accent-blue/5 to-accent-cyan/5 border-accent-blue/20">
            <div className="flex items-start gap-3">
              <div className="p-2 rounded-lg bg-accent-blue/10">
                <ExternalLink className="w-4 h-4 text-accent-blue" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-xs font-medium text-text-primary">Start Scanning</p>
                <p className="text-xs text-text-tertiary mt-0.5">Discover new APIs</p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Collapse toggle */}
      <button
        onClick={onToggle}
        className="absolute -right-3 top-20 w-6 h-6 rounded-full bg-surface-card border border-border flex items-center justify-center shadow-sm hover:bg-bg-secondary transition-colors"
        title={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
      >
        {isCollapsed ? (
          <ChevronRight className="w-4 h-4 text-text-secondary" />
        ) : (
          <ChevronLeft className="w-4 h-4 text-text-secondary" />
        )}
      </button>
    </div>
  );

  return (
    <>
      {/* Mobile toggle */}
      <button
        onClick={() => setMobileOpen(true)}
        className="lg:hidden fixed top-4 left-4 z-50 p-2 rounded-lg bg-surface-card border border-border shadow-md"
      >
        <Menu className="w-5 h-5 text-text-primary" />
      </button>

      {/* Mobile overlay */}
      {mobileOpen && (
        <div
          className="lg:hidden fixed inset-0 bg-black/50 z-40 animate-fade-in"
          onClick={() => setMobileOpen(false)}
        />
      )}

      {/* Mobile sidebar */}
      <div
        className={`
          lg:hidden fixed inset-y-0 left-0 z-50 w-64 bg-surface-card border-r border-border
          transform transition-transform duration-300 ease-out
          ${mobileOpen ? 'translate-x-0' : '-translate-x-full'}
        `}
      >
        <button
          onClick={() => setMobileOpen(false)}
          className="absolute top-4 right-4 p-1 rounded-lg hover:bg-bg-secondary transition-colors"
        >
          <X className="w-5 h-5 text-text-secondary" />
        </button>
        <div className="pt-16">
          <Sidebar />
        </div>
      </div>

      {/* Desktop sidebar */}
      <aside
        className={`
          hidden lg:flex fixed inset-y-0 left-0 z-30
          bg-surface-card border-r border-border
          transition-all duration-300 ease-out
          ${isCollapsed ? 'w-16' : 'w-64'}
        `}
      >
        {sidebarContent}
      </aside>
    </>
  );
}

// ChevronLeft component
function ChevronLeft(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      {...props}
    >
      <path d="m15 18-6-6 6-6" />
    </svg>
  );
}