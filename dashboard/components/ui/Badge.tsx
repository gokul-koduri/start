'use client';

import { clsx } from 'clsx';
import { ReactNode } from 'react';

// Method Badge - for HTTP methods (GET, POST, PUT, DELETE, etc.)
interface MethodBadgeProps {
  method: string;
  size?: 'sm' | 'md';
}

export function MethodBadge({ method, size = 'md' }: MethodBadgeProps) {
  const sizeClasses = {
    sm: 'px-1.5 py-0.5 text-[10px]',
    md: 'px-2 py-1 text-xs',
  };

  const methodStyles: Record<string, { bg: string; text: string }> = {
    GET: { bg: 'bg-emerald-50', text: 'text-emerald-600' },
    POST: { bg: 'bg-blue-50', text: 'text-blue-600' },
    PUT: { bg: 'bg-amber-50', text: 'text-amber-600' },
    PATCH: { bg: 'bg-purple-50', text: 'text-purple-600' },
    DELETE: { bg: 'bg-red-50', text: 'text-red-600' },
    OPTIONS: { bg: 'bg-gray-50', text: 'text-gray-600' },
    HEAD: { bg: 'bg-gray-50', text: 'text-gray-600' },
  };

  const style = methodStyles[method.toUpperCase()] || methodStyles.GET;

  return (
    <span
      className={clsx(
        'inline-flex items-center font-semibold rounded-md uppercase tracking-wide',
        style.bg,
        style.text,
        sizeClasses[size]
      )}
    >
      {method.toUpperCase()}
    </span>
  );
}

// Status Badge
interface StatusBadgeProps {
  status: 'active' | 'inactive' | 'deprecated' | 'beta' | 'maintenance';
  size?: 'sm' | 'md';
}

export function StatusBadge({ status, size = 'md' }: StatusBadgeProps) {
  const sizeClasses = {
    sm: 'px-1.5 py-0.5 text-[10px]',
    md: 'px-2 py-1 text-xs',
  };

  const statusStyles: Record<string, { bg: string; text: string; dot: string }> = {
    active: { bg: 'bg-emerald-50', text: 'text-emerald-600', dot: 'bg-emerald-500' },
    inactive: { bg: 'bg-gray-100', text: 'text-gray-500', dot: 'bg-gray-400' },
    deprecated: { bg: 'bg-amber-50', text: 'text-amber-600', dot: 'bg-amber-500' },
    beta: { bg: 'bg-purple-50', text: 'text-purple-600', dot: 'bg-purple-500' },
    maintenance: { bg: 'bg-amber-50', text: 'text-amber-600', dot: 'bg-amber-500' },
  };

  const style = statusStyles[status] || statusStyles.inactive;

  return (
    <span
      className={clsx(
        'inline-flex items-center gap-1.5 px-2 py-1 rounded-full text-xs font-medium',
        style.bg,
        style.text
      )}
    >
      <span className={clsx('w-1.5 h-1.5 rounded-full', style.dot)} />
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </span>
  );
}

// Tag Badge
interface TagBadgeProps {
  children: ReactNode;
  variant?: 'default' | 'blue' | 'green' | 'red' | 'amber' | 'purple';
  removable?: boolean;
  onRemove?: () => void;
}

export function TagBadge({ children, variant = 'default', removable, onRemove }: TagBadgeProps) {
  const variantStyles: Record<string, { bg: string; text: string }> = {
    default: { bg: 'bg-gray-100', text: 'text-gray-600' },
    blue: { bg: 'bg-blue-50', text: 'text-blue-600' },
    green: { bg: 'bg-emerald-50', text: 'text-emerald-600' },
    red: { bg: 'bg-red-50', text: 'text-red-600' },
    amber: { bg: 'bg-amber-50', text: 'text-amber-600' },
    purple: { bg: 'bg-purple-50', text: 'text-purple-600' },
  };

  const style = variantStyles[variant];

  return (
    <span
      className={clsx(
        'inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-xs font-medium',
        style.bg,
        style.text
      )}
    >
      {children}
      {removable && (
        <button
          onClick={(e) => {
            e.stopPropagation();
            onRemove?.();
          }}
          className="ml-0.5 hover:opacity-70 transition-opacity"
        >
          ×
        </button>
      )}
    </span>
  );
}

// Auth Type Badge
interface AuthBadgeProps {
  authType: string;
}

export function AuthBadge({ authType }: AuthBadgeProps) {
  const authStyles: Record<string, { bg: string; text: string; label: string }> = {
    none: { bg: 'bg-gray-100', text: 'text-gray-500', label: 'No Auth' },
    apiKey: { bg: 'bg-blue-50', text: 'text-blue-600', label: 'API Key' },
    bearer: { bg: 'bg-emerald-50', text: 'text-emerald-600', label: 'Bearer' },
    basic: { bg: 'bg-purple-50', text: 'text-purple-600', label: 'Basic' },
    oauth2: { bg: 'bg-amber-50', text: 'text-amber-600', label: 'OAuth 2' },
    jwt: { bg: 'bg-cyan-50', text: 'text-cyan-600', label: 'JWT' },
  };

  const style = authStyles[authType.toLowerCase()] || authStyles.none;

  return (
    <span
      className={clsx(
        'inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium',
        style.bg,
        style.text
      )}
    >
      {style.label}
    </span>
  );
}

// Security Score Badge
interface SecurityBadgeProps {
  score: number;
  showValue?: boolean;
}

export function SecurityBadge({ score, showValue = true }: SecurityBadgeProps) {
  const getSecurityLevel = (score: number) => {
    if (score >= 80) return { label: 'High', bg: 'bg-emerald-50', text: 'text-emerald-600', border: 'border-emerald-200' };
    if (score >= 50) return { label: 'Medium', bg: 'bg-amber-50', text: 'text-amber-600', border: 'border-amber-200' };
    if (score > 0) return { label: 'Low', bg: 'bg-red-50', text: 'text-red-600', border: 'border-red-200' };
    return { label: 'Unrated', bg: 'bg-gray-100', text: 'text-gray-500', border: 'border-gray-200' };
  };

  const level = getSecurityLevel(score);

  return (
    <span
      className={clsx(
        'inline-flex items-center gap-1.5 px-2 py-1 rounded-md text-xs font-medium border',
        level.bg,
        level.text,
        level.border
      )}
    >
      <svg
        className={clsx('w-3.5 h-3.5', level.text)}
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"
        />
      </svg>
      {showValue ? `${score}` : level.label}
    </span>
  );
}

// Category Badge
interface CategoryBadgeProps {
  category: string;
}

export function CategoryBadge({ category }: CategoryBadgeProps) {
  const categoryColors: Record<string, string> = {
    payment: 'bg-emerald-50 text-emerald-600',
    social: 'bg-blue-50 text-blue-600',
    ai: 'bg-purple-50 text-purple-600',
    analytics: 'bg-amber-50 text-amber-600',
    communication: 'bg-cyan-50 text-cyan-600',
    storage: 'bg-indigo-50 text-indigo-600',
    devtools: 'bg-pink-50 text-pink-600',
    commerce: 'bg-orange-50 text-orange-600',
    health: 'bg-red-50 text-red-600',
    finance: 'bg-green-50 text-green-600',
  };

  const [colorClass] = Object.entries(categoryColors).find(([key]) =>
    category.toLowerCase().includes(key)
  ) || ['default', 'bg-gray-100 text-gray-600'];

  return (
    <span className={clsx('inline-flex px-2 py-0.5 rounded-md text-xs font-medium', colorClass)}>
      {category}
    </span>
  );
}