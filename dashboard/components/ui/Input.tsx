'use client';

import { clsx } from 'clsx';
import { InputHTMLAttributes, TextareaHTMLAttributes, forwardRef } from 'react';
import { LucideIcon, Search } from 'lucide-react';

// Text Input
interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  icon?: LucideIcon;
  iconPosition?: 'left' | 'right';
  helperText?: string;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, icon: Icon, iconPosition = 'left', helperText, className, ...props }, ref) => {
    const InputIcon = Icon;

    return (
      <div className="w-full">
        {label && (
          <label className="block text-sm font-medium text-text-primary mb-1.5">
            {label}
          </label>
        )}
        <div className="relative">
          {InputIcon && iconPosition === 'left' && (
            <div className="absolute left-3 top-1/2 -translate-y-1/2 text-text-tertiary">
              <InputIcon className="w-4 h-4" />
            </div>
          )}
          <input
            ref={ref}
            className={clsx(
              'w-full px-3 py-2 text-sm bg-surface-card border rounded-lg transition-all duration-150',
              'placeholder:text-text-tertiary',
              'focus:outline-none focus:ring-2 focus:ring-accent-blue/30 focus:border-accent-blue',
              error ? 'border-accent-red focus:ring-accent-red/30 focus:border-accent-red' : 'border-border',
              InputIcon && iconPosition === 'left' && 'pl-10',
              InputIcon && iconPosition === 'right' && 'pr-10',
              className
            )}
            {...props}
          />
          {InputIcon && iconPosition === 'right' && (
            <div className="absolute right-3 top-1/2 -translate-y-1/2 text-text-tertiary">
              <InputIcon className="w-4 h-4" />
            </div>
          )}
        </div>
        {(error || helperText) && (
          <p className={clsx('mt-1.5 text-xs', error ? 'text-accent-red' : 'text-text-tertiary')}>
            {error || helperText}
          </p>
        )}
      </div>
    );
  }
);

Input.displayName = 'Input';

// Search Input
interface SearchInputProps extends Omit<InputProps, 'icon'> {
  onSearch?: (value: string) => void;
}

export const SearchInput = forwardRef<HTMLInputElement, SearchInputProps>(
  ({ onSearch, className, ...props }, ref) => {
    return (
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-tertiary pointer-events-none" />
        <input
          ref={ref}
          type="search"
          className={clsx(
            'w-full pl-10 pr-4 py-2 text-sm bg-bg-secondary border border-border rounded-lg',
            'placeholder:text-text-tertiary',
            'focus:outline-none focus:ring-2 focus:ring-accent-blue/30 focus:border-accent-blue',
            'transition-all duration-150',
            className
          )}
          {...props}
        />
      </div>
    );
  }
);

SearchInput.displayName = 'SearchInput';

// Textarea
interface TextareaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
  error?: string;
  helperText?: string;
}

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ label, error, helperText, className, ...props }, ref) => {
    return (
      <div className="w-full">
        {label && (
          <label className="block text-sm font-medium text-text-primary mb-1.5">
            {label}
          </label>
        )}
        <textarea
          ref={ref}
          className={clsx(
            'w-full px-3 py-2 text-sm bg-surface-card border rounded-lg',
            'placeholder:text-text-tertiary',
            'focus:outline-none focus:ring-2 focus:ring-accent-blue/30 focus:border-accent-blue',
            'resize-none transition-all duration-150',
            error ? 'border-accent-red' : 'border-border',
            className
          )}
          {...props}
        />
        {(error || helperText) && (
          <p className={clsx('mt-1.5 text-xs', error ? 'text-accent-red' : 'text-text-tertiary')}>
            {error || helperText}
          </p>
        )}
      </div>
    );
  }
);

Textarea.displayName = 'Textarea';

// Select
interface SelectOption {
  value: string;
  label: string;
}

interface SelectProps {
  label?: string;
  options: SelectOption[];
  value?: string;
  onChange?: (value: string) => void;
  placeholder?: string;
  error?: string;
  className?: string;
}

export function Select({ label, options, value, onChange, placeholder, error, className }: SelectProps) {
  return (
    <div className="w-full">
      {label && (
        <label className="block text-sm font-medium text-text-primary mb-1.5">
          {label}
        </label>
      )}
      <select
        value={value}
        onChange={(e) => onChange?.(e.target.value)}
        className={clsx(
          'w-full px-3 py-2 text-sm bg-surface-card border rounded-lg appearance-none cursor-pointer',
          'focus:outline-none focus:ring-2 focus:ring-accent-blue/30 focus:border-accent-blue',
          'transition-all duration-150',
          error ? 'border-accent-red' : 'border-border',
          className
        )}
        style={{
          backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 24 24' stroke='%239CA3AF'%3E%3Cpath stroke-linecap='round' stroke-linejoin='round' stroke-width='2' d='M19 9l-7 7-7-7'%3E%3C/path%3E%3C/svg%3E")`,
          backgroundRepeat: 'no-repeat',
          backgroundPosition: 'right 0.75rem center',
          backgroundSize: '1rem',
          paddingRight: '2.5rem',
        }}
      >
        {placeholder && (
          <option value="" disabled>
            {placeholder}
          </option>
        )}
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
      {error && <p className="mt-1.5 text-xs text-accent-red">{error}</p>}
    </div>
  );
}