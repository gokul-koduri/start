'use client';

import { useState } from 'react';
import Link from 'next/link';
import { clsx } from 'clsx';

// Card Component
interface CardProps {
  children: React.ReactNode;
  className?: string;
  hover?: boolean;
  padding?: 'none' | 'sm' | 'md' | 'lg';
  onClick?: () => void;
}

export function Card({
  children,
  className,
  hover = false,
  padding = 'md',
  onClick
}: CardProps) {
  const paddingClasses = {
    none: '',
    sm: 'p-3',
    md: 'p-4',
    lg: 'p-6',
  };

  return (
    <div
      className={clsx(
        'bg-surface-card border border-border rounded-xl shadow-card',
        hover && 'card-hover cursor-pointer',
        paddingClasses[padding],
        className
      )}
      onClick={onClick}
    >
      {children}
    </div>
  );
}

// Stat Card Component
interface StatCardProps {
  label: string;
  value: string | number;
  change?: number;
  changeLabel?: string;
  icon?: React.ReactNode;
  loading?: boolean;
}

export function StatCard({ label, value, change, changeLabel, icon, loading }: StatCardProps) {
  return (
    <Card>
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm text-text-secondary mb-1">{label}</p>
          {loading ? (
            <div className="skeleton h-8 w-20" />
          ) : (
            <p className="text-2xl font-semibold text-text-primary">{value}</p>
          )}
          {change !== undefined && !loading && (
            <div className="flex items-center gap-1 mt-2">
              <span
                className={clsx(
                  'text-sm font-medium',
                  change > 0 ? 'text-accent-green' : change < 0 ? 'text-accent-red' : 'text-text-tertiary'
                )}
              >
                {change > 0 ? '+' : ''}{change}%
              </span>
              {changeLabel && (
                <span className="text-sm text-text-tertiary">{changeLabel}</span>
              )}
            </div>
          )}
        </div>
        {icon && (
          <div className="p-2 rounded-lg bg-accent-blue/10 text-accent-blue">
            {icon}
          </div>
        )}
      </div>
    </Card>
  );
}

// KPI Card with Sparkline
interface KPICardProps extends StatCardProps {
  sparklineData?: number[];
  sparklineColor?: string;
}

export function KPICard({ sparklineData, sparklineColor = '#2563EB', ...props }: KPICardProps) {
  const maxVal = Math.max(...(sparklineData || [1]));
  const height = 40;

  return (
    <Card>
      <div className="flex items-start justify-between mb-3">
        <div>
          <p className="text-sm text-text-secondary mb-1">{props.label}</p>
          {props.loading ? (
            <div className="skeleton h-9 w-24" />
          ) : (
            <p className="text-3xl font-bold text-text-primary">{props.value}</p>
          )}
          {props.change !== undefined && !props.loading && (
            <p className={clsx(
              'text-sm mt-1',
              props.change > 0 ? 'text-accent-green' : props.change < 0 ? 'text-accent-red' : 'text-text-tertiary'
            )}>
              {props.change > 0 ? '+' : ''}{props.change}% {props.changeLabel}
            </p>
          )}
        </div>
        {props.icon && (
          <div className="p-2 rounded-lg bg-accent-blue/10 text-accent-blue">
            {props.icon}
          </div>
        )}
      </div>
      {sparklineData && (
        <svg width="100%" height={height} viewBox={`0 0 100 ${height}`} preserveAspectRatio="none">
          <polyline
            fill="none"
            stroke={sparklineColor}
            strokeWidth="2"
            strokeLinejoin="round"
            strokeLinecap="round"
            points={sparklineData.map((val, i) => {
              const x = (i / (sparklineData.length - 1)) * 100;
              const y = height - (val / maxVal) * height;
              return `${x},${y}`;
            }).join(' ')}
          />
        </svg>
      )}
    </Card>
  );
}

// Empty State
interface EmptyStateProps {
  icon?: React.ReactNode;
  title: string;
  description?: string;
  action?: {
    label: string;
    onClick: () => void;
  };
}

export function EmptyState({ icon, title, description, action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-12 px-4 text-center">
      {icon && (
        <div className="w-12 h-12 rounded-full bg-bg-secondary flex items-center justify-center text-text-tertiary mb-4">
          {icon}
        </div>
      )}
      <h3 className="text-lg font-medium text-text-primary mb-2">{title}</h3>
      {description && (
        <p className="text-sm text-text-secondary mb-4 max-w-sm">{description}</p>
      )}
      {action && (
        <button
          onClick={action.onClick}
          className="btn btn-primary"
        >
          {action.label}
        </button>
      )}
    </div>
  );
}

// Loading Skeleton
interface SkeletonProps {
  className?: string;
  count?: number;
}

export function Skeleton({ className, count = 1 }: SkeletonProps) {
  return (
    <>
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className={clsx('skeleton', className)} />
      ))}
    </>
  );
}

export function CardSkeleton() {
  return (
    <Card>
      <div className="space-y-3">
        <Skeleton className="h-4 w-1/3" />
        <Skeleton className="h-6 w-1/2" />
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-2/3" />
      </div>
    </Card>
  );
}

export function StatCardSkeleton() {
  return (
    <Card>
      <div className="flex items-start justify-between">
        <div className="space-y-2">
          <Skeleton className="h-4 w-20" />
          <Skeleton className="h-9 w-24" />
          <Skeleton className="h-4 w-16" />
        </div>
        <Skeleton className="w-10 h-10 rounded-lg" />
      </div>
    </Card>
  );
}