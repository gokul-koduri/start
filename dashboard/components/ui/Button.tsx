'use client';

import { clsx } from 'clsx';
import { ButtonHTMLAttributes, forwardRef } from 'react';
import { LucideIcon } from 'lucide-react';

// Button Component
interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger' | 'outline';
  size?: 'sm' | 'md' | 'lg';
  icon?: LucideIcon;
  iconPosition?: 'left' | 'right';
  loading?: boolean;
  fullWidth?: boolean;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      children,
      variant = 'primary',
      size = 'md',
      icon: Icon,
      iconPosition = 'left',
      loading = false,
      fullWidth = false,
      className,
      disabled,
      ...props
    },
    ref
  ) => {
    const variantClasses = {
      primary: 'bg-accent-blue text-white hover:bg-accent-blueHover border-accent-blue',
      secondary: 'bg-surface-card text-text-primary hover:bg-bg-secondary border-border',
      ghost: 'bg-transparent text-text-secondary hover:text-text-primary hover:bg-bg-secondary border-transparent',
      danger: 'bg-accent-red text-white hover:bg-red-600 border-accent-red',
      outline: 'bg-transparent text-accent-blue hover:bg-accent-blue/5 border-accent-blue',
    };

    const sizeClasses = {
      sm: 'px-2.5 py-1.5 text-xs gap-1.5',
      md: 'px-4 py-2 text-sm gap-2',
      lg: 'px-6 py-3 text-base gap-2.5',
    };

    const IconComponent = Icon;

    return (
      <button
        ref={ref}
        disabled={disabled || loading}
        className={clsx(
          'inline-flex items-center justify-center font-medium rounded-lg border transition-all duration-150',
          'focus:outline-none focus:ring-2 focus:ring-accent-blue/30 focus:ring-offset-2',
          'disabled:opacity-50 disabled:cursor-not-allowed',
          variantClasses[variant],
          sizeClasses[size],
          fullWidth && 'w-full',
          className
        )}
        {...props}
      >
        {loading ? (
          <svg
            className={clsx('animate-spin', size === 'sm' ? 'w-3 h-3' : size === 'lg' ? 'w-5 h-5' : 'w-4 h-4')}
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
        ) : (
          IconComponent && iconPosition === 'left' && <IconComponent className={clsx(size === 'sm' ? 'w-3.5 h-3.5' : 'w-4 h-4')} />
        )}
        {children}
        {!loading && IconComponent && iconPosition === 'right' && (
          <IconComponent className={clsx(size === 'sm' ? 'w-3.5 h-3.5' : 'w-4 h-4')} />
        )}
      </button>
    );
  }
);

Button.displayName = 'Button';

// Icon Button (square)
interface IconButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  icon: LucideIcon;
  variant?: 'primary' | 'secondary' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
  label: string; // For accessibility
}

export const IconButton = forwardRef<HTMLButtonElement, IconButtonProps>(
  ({ icon: Icon, variant = 'ghost', size = 'md', label, className, ...props }, ref) => {
    const variantClasses = {
      primary: 'bg-accent-blue text-white hover:bg-accent-blueHover',
      secondary: 'bg-surface-card text-text-primary hover:bg-bg-secondary border border-border',
      ghost: 'bg-transparent text-text-secondary hover:text-text-primary hover:bg-bg-secondary',
    };

    const sizeClasses = {
      sm: 'w-7 h-7',
      md: 'w-9 h-9',
      lg: 'w-11 h-11',
    };

    const iconSizes = {
      sm: 'w-4 h-4',
      md: 'w-5 h-5',
      lg: 'w-6 h-6',
    };

    return (
      <button
        ref={ref}
        aria-label={label}
        className={clsx(
          'inline-flex items-center justify-center rounded-lg transition-all duration-150',
          'focus:outline-none focus:ring-2 focus:ring-accent-blue/30 focus:ring-offset-2',
          variantClasses[variant],
          sizeClasses[size],
          className
        )}
        {...props}
      >
        <Icon className={iconSizes[size]} />
      </button>
    );
  }
);

IconButton.displayName = 'IconButton';