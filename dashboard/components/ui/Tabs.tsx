'use client';

import { clsx } from 'clsx';
import { createContext, useContext, useState, ReactNode } from 'react';

// Tabs Component
interface TabsContextValue {
  activeTab: string;
  setActiveTab: (tab: string) => void;
}

const TabsContext = createContext<TabsContextValue | undefined>(undefined);

interface TabsProps {
  defaultValue: string;
  children: ReactNode;
  className?: string;
  onChange?: (value: string) => void;
}

export function Tabs({ defaultValue, children, className, onChange }: TabsProps) {
  const [activeTab, setActiveTab] = useState(defaultValue);

  const handleTabChange = (tab: string) => {
    setActiveTab(tab);
    onChange?.(tab);
  };

  return (
    <TabsContext.Provider value={{ activeTab, setActiveTab: handleTabChange }}>
      <div className={className}>{children}</div>
    </TabsContext.Provider>
  );
}

interface TabListProps {
  children: ReactNode;
  className?: string;
}

export function TabList({ children, className }: TabListProps) {
  return (
    <div className={clsx('flex gap-1 p-1 bg-bg-secondary rounded-lg', className)}>
      {children}
    </div>
  );
}

interface TabTriggerProps {
  value: string;
  children: ReactNode;
  icon?: ReactNode;
  count?: number;
}

export function TabTrigger({ value, children, icon, count }: TabTriggerProps) {
  const context = useContext(TabsContext);
  if (!context) throw new Error('TabTrigger must be used within Tabs');

  const { activeTab, setActiveTab } = context;
  const isActive = activeTab === value;

  return (
    <button
      onClick={() => setActiveTab(value)}
      className={clsx(
        'flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-md transition-all duration-150',
        isActive
          ? 'bg-surface-card text-text-primary shadow-sm'
          : 'text-text-secondary hover:text-text-primary'
      )}
    >
      {icon}
      {children}
      {count !== undefined && (
        <span
          className={clsx(
            'px-1.5 py-0.5 text-xs rounded-full',
            isActive ? 'bg-accent-blue/10 text-accent-blue' : 'bg-bg-tertiary text-text-tertiary'
          )}
        >
          {count}
        </span>
      )}
    </button>
  );
}

interface TabContentProps {
  value: string;
  children: ReactNode;
}

export function TabContent({ value, children }: TabContentProps) {
  const context = useContext(TabsContext);
  if (!context) throw new Error('TabContent must be used within Tabs');

  const { activeTab } = context;

  if (activeTab !== value) return null;

  return (
    <div className="animate-fade-in">
      {children}
    </div>
  );
}

// Collapsible Section
interface CollapsibleProps {
  title: string;
  children: ReactNode;
  defaultOpen?: boolean;
  icon?: ReactNode;
}

export function Collapsible({ title, children, defaultOpen = false, icon }: CollapsibleProps) {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  return (
    <div className="border border-border rounded-lg overflow-hidden">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between px-4 py-3 bg-bg-secondary text-left hover:bg-bg-tertiary transition-colors"
      >
        <div className="flex items-center gap-2">
          {icon}
          <span className="font-medium text-sm text-text-primary">{title}</span>
        </div>
        <svg
          className={clsx('w-4 h-4 text-text-tertiary transition-transform', isOpen && 'rotate-180')}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>
      <div
        className={clsx(
          'overflow-hidden transition-all duration-200',
          isOpen ? 'max-h-[1000px] opacity-100' : 'max-h-0 opacity-0'
        )}
      >
        <div className="p-4">{children}</div>
      </div>
    </div>
  );
}

// Progress Bar
interface ProgressProps {
  value: number;
  max?: number;
  size?: 'sm' | 'md' | 'lg';
  showLabel?: boolean;
  color?: 'blue' | 'green' | 'amber' | 'red';
}

export function Progress({ value, max = 100, size = 'md', showLabel, color = 'blue' }: ProgressProps) {
  const percentage = Math.min(100, Math.max(0, (value / max) * 100));

  const sizeClasses = {
    sm: 'h-1',
    md: 'h-2',
    lg: 'h-3',
  };

  const colorClasses = {
    blue: 'bg-accent-blue',
    green: 'bg-accent-green',
    amber: 'bg-accent-amber',
    red: 'bg-accent-red',
  };

  return (
    <div className="w-full">
      <div className={clsx('w-full bg-bg-tertiary rounded-full overflow-hidden', sizeClasses[size])}>
        <div
          className={clsx('h-full rounded-full transition-all duration-300', colorClasses[color])}
          style={{ width: `${percentage}%` }}
        />
      </div>
      {showLabel && (
        <p className="text-xs text-text-tertiary mt-1 text-right">{Math.round(percentage)}%</p>
      )}
    </div>
  );
}

// Loading Spinner
interface SpinnerProps {
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

export function Spinner({ size = 'md', className }: SpinnerProps) {
  const sizeClasses = {
    sm: 'w-4 h-4',
    md: 'w-6 h-6',
    lg: 'w-8 h-8',
  };

  return (
    <svg
      className={clsx('animate-spin text-accent-blue', sizeClasses[size], className)}
      fill="none"
      viewBox="0 0 24 24"
    >
      <circle
        className="opacity-25"
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="4"
      />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
      />
    </svg>
  );
}

// Overlay / Modal
interface OverlayProps {
  isOpen: boolean;
  onClose: () => void;
  children: ReactNode;
}

export function Overlay({ isOpen, onClose, children }: OverlayProps) {
  if (!isOpen) return null;

  return (
    <>
      <div
        className="fixed inset-0 bg-black/50 z-40 animate-fade-in"
        onClick={onClose}
      />
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div className="relative z-50 w-full max-w-lg animate-scale-in">
          {children}
        </div>
      </div>
    </>
  );
}