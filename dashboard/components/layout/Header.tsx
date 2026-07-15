'use client';

import { useState, useRef, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import {
  Search,
  Bell,
  Sun,
  Moon,
  User,
  Settings,
  LogOut,
  ChevronDown,
  Plus,
  RefreshCw,
  HelpCircle,
  Check,
  X,
} from 'lucide-react';

interface HeaderProps {
  className?: string;
}

export function Header({ className = '' }: HeaderProps) {
  const router = useRouter();
  const [searchQuery, setSearchQuery] = useState('');
  const [isDarkMode, setIsDarkMode] = useState(false);
  const [showSearch, setShowSearch] = useState(false);
  const [showNotifications, setShowNotifications] = useState(false);
  const [showUserMenu, setShowUserMenu] = useState(false);
  const searchRef = useRef<HTMLDivElement>(null);
  const notificationsRef = useRef<HTMLDivElement>(null);
  const userMenuRef = useRef<HTMLDivElement>(null);

  // Mock notifications
  const notifications = [
    { id: 1, title: 'New API discovered', message: 'GitHub API v3 endpoints updated', time: '5m ago', unread: true },
    { id: 2, title: 'Security alert', message: 'TLS certificate expiring for Stripe API', time: '1h ago', unread: true },
    { id: 3, title: 'Scan complete', message: 'Completed scanning 150 endpoints', time: '2h ago', unread: false },
  ];

  // Handle click outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (searchRef.current && !searchRef.current.contains(event.target as Node)) {
        setShowSearch(false);
      }
      if (notificationsRef.current && !notificationsRef.current.contains(event.target as Node)) {
        setShowNotifications(false);
      }
      if (userMenuRef.current && !userMenuRef.current.contains(event.target as Node)) {
        setShowUserMenu(false);
      }
    }

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Handle theme toggle
  const toggleTheme = () => {
    const newMode = !isDarkMode;
    setIsDarkMode(newMode);
    document.documentElement.classList.toggle('dark', newMode);
  };

  // Handle search
  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      router.push(`/explorer?search=${encodeURIComponent(searchQuery)}`);
      setShowSearch(false);
    }
  };

  const unreadCount = notifications.filter(n => n.unread).length;

  return (
    <header
      className={`
        sticky top-0 z-20 h-16 bg-surface-card/80 backdrop-blur-md
        border-b border-border flex items-center justify-between px-6
        ${className}
      `}
    >
      {/* Search bar */}
      <div ref={searchRef} className="relative flex-1 max-w-xl">
        <form onSubmit={handleSearch}>
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-tertiary" />
            <input
              type="text"
              placeholder="Search APIs, endpoints, organizations..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onFocus={() => setShowSearch(true)}
              className="input pl-10 pr-4 py-2 bg-bg-secondary border-border"
            />
            <kbd className="absolute right-3 top-1/2 -translate-y-1/2 px-1.5 py-0.5 text-xs font-medium text-text-tertiary bg-bg-tertiary rounded border border-border">
              /
            </kbd>
          </div>
        </form>

        {/* Search dropdown */}
        {showSearch && searchQuery.length > 0 && (
          <div className="absolute top-full left-0 right-0 mt-2 card p-2 animate-slide-down">
            <div className="p-3 text-sm text-text-secondary">
              Press Enter to search for "{searchQuery}"
            </div>
            <div className="border-t border-border pt-2">
              <div className="px-3 py-2 text-xs font-medium text-text-tertiary uppercase">
                Quick Links
              </div>
              <button
                onClick={() => router.push(`/explorer?category=payment`)}
                className="w-full flex items-center gap-2 px-3 py-2 text-sm text-left hover:bg-bg-secondary rounded-lg transition-colors"
              >
                <span className="w-2 h-2 rounded-full bg-accent-green" />
                Payment APIs
              </button>
              <button
                onClick={() => router.push(`/explorer?category=ai`)}
                className="w-full flex items-center gap-2 px-3 py-2 text-sm text-left hover:bg-bg-secondary rounded-lg transition-colors"
              >
                <span className="w-2 h-2 rounded-full bg-accent-purple" />
                AI & Machine Learning
              </button>
              <button
                onClick={() => router.push(`/explorer?category=social`)}
                className="w-full flex items-center gap-2 px-3 py-2 text-sm text-left hover:bg-bg-secondary rounded-lg transition-colors"
              >
                <span className="w-2 h-2 rounded-full bg-accent-blue" />
                Social APIs
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Right side actions */}
      <div className="flex items-center gap-2 ml-4">
        {/* Scan button - hidden on mobile */}
        <button className="hidden sm:flex items-center gap-2 btn btn-primary">
          <Plus className="w-4 h-4" />
          <span>New Scan</span>
        </button>

        {/* Icons */}
        <button
          onClick={toggleTheme}
          className="p-2 rounded-lg hover:bg-bg-secondary transition-colors"
          title={isDarkMode ? 'Light mode' : 'Dark mode'}
        >
          {isDarkMode ? (
            <Sun className="w-5 h-5 text-text-secondary" />
          ) : (
            <Moon className="w-5 h-5 text-text-secondary" />
          )}
        </button>

        {/* Notifications */}
        <div ref={notificationsRef} className="relative">
          <button
            onClick={() => setShowNotifications(!showNotifications)}
            className="relative p-2 rounded-lg hover:bg-bg-secondary transition-colors"
          >
            <Bell className="w-5 h-5 text-text-secondary" />
            {unreadCount > 0 && (
              <span className="absolute top-1 right-1 w-4 h-4 text-[10px] font-bold text-white bg-accent-red rounded-full flex items-center justify-center">
                {unreadCount}
              </span>
            )}
          </button>

          {showNotifications && (
            <div className="absolute right-0 top-full mt-2 w-80 card p-0 overflow-hidden animate-scale-in">
              <div className="flex items-center justify-between p-4 border-b border-border">
                <h3 className="font-semibold text-text-primary">Notifications</h3>
                <button className="text-xs text-accent-blue hover:underline">
                  Mark all read
                </button>
              </div>
              <div className="max-h-80 overflow-y-auto">
                {notifications.map((notif) => (
                  <button
                    key={notif.id}
                    className={`w-full flex items-start gap-3 p-4 hover:bg-bg-secondary transition-colors text-left ${
                      notif.unread ? 'bg-accent-blue/5' : ''
                    }`}
                  >
                    <div className={`w-2 h-2 mt-2 rounded-full flex-shrink-0 ${
                      notif.unread ? 'bg-accent-blue' : 'bg-text-tertiary'
                    }`} />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-text-primary">{notif.title}</p>
                      <p className="text-xs text-text-secondary mt-0.5 truncate">{notif.message}</p>
                      <p className="text-xs text-text-tertiary mt-1">{notif.time}</p>
                    </div>
                  </button>
                ))}
              </div>
              <div className="p-3 border-t border-border">
                <button className="w-full text-center text-sm text-accent-blue hover:underline">
                  View all notifications
                </button>
              </div>
            </div>
          )}
        </div>

        {/* User menu */}
        <div ref={userMenuRef} className="relative">
          <button
            onClick={() => setShowUserMenu(!showUserMenu)}
            className="flex items-center gap-2 p-1 rounded-lg hover:bg-bg-secondary transition-colors"
          >
            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-accent-blue to-accent-cyan flex items-center justify-center">
              <span className="text-sm font-semibold text-white">JD</span>
            </div>
            <ChevronDown className="w-4 h-4 text-text-tertiary" />
          </button>

          {showUserMenu && (
            <div className="absolute right-0 top-full mt-2 w-56 card p-2 animate-scale-in">
              <div className="p-3 border-b border-border mb-2">
                <p className="font-medium text-text-primary">John Doe</p>
                <p className="text-sm text-text-secondary">john@example.com</p>
              </div>
              <button className="w-full flex items-center gap-2 px-3 py-2 text-sm rounded-lg hover:bg-bg-secondary transition-colors">
                <User className="w-4 h-4 text-text-tertiary" />
                Profile
              </button>
              <button className="w-full flex items-center gap-2 px-3 py-2 text-sm rounded-lg hover:bg-bg-secondary transition-colors">
                <Settings className="w-4 h-4 text-text-tertiary" />
                Settings
              </button>
              <button className="w-full flex items-center gap-2 px-3 py-2 text-sm rounded-lg hover:bg-bg-secondary transition-colors">
                <HelpCircle className="w-4 h-4 text-text-tertiary" />
                Help & Support
              </button>
              <div className="border-t border-border mt-2 pt-2">
                <button className="w-full flex items-center gap-2 px-3 py-2 text-sm rounded-lg hover:bg-bg-secondary transition-colors text-accent-red">
                  <LogOut className="w-4 h-4" />
                  Sign out
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}