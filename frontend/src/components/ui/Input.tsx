import React, { forwardRef, InputHTMLAttributes } from 'react';
import { cn } from '../../utils/cn';
import { AlertCircle } from 'lucide-react';

export interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  helperText?: string;
  error?: string;
  fullWidth?: boolean;
  leftAddon?: React.ReactNode;
  rightAddon?: React.ReactNode;
  containerClassName?: string;
}

const Input = forwardRef<HTMLInputElement, InputProps>(
  (
    {
      className,
      label,
      helperText,
      error,
      fullWidth = false,
      leftAddon,
      rightAddon,
      containerClassName,
      ...props
    },
    ref
  ) => {
    const id = props.id || props.name;
    
    return (
      <div className={cn('flex flex-col space-y-1.5', fullWidth && 'w-full', containerClassName)}>
        {label && (
          <label
            htmlFor={id}
            className="text-sm font-medium text-gray-700 dark:text-gray-300"
          >
            {label}
          </label>
        )}
        
        <div className="relative flex">
          {leftAddon && (
            <div className="flex items-center justify-center rounded-l-md border border-r-0 border-gray-300 bg-gray-100 px-3 text-gray-500 dark:border-gray-600 dark:bg-gray-800">
              {leftAddon}
            </div>
          )}
          
          <input
            ref={ref}
            id={id}
            className={cn(
              // Base styles
              'flex h-10 w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm transition-colors file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-gray-500 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 disabled:cursor-not-allowed disabled:opacity-50 dark:border-gray-600 dark:bg-gray-900 dark:placeholder:text-gray-400',
              
              // Error state
              error && 'border-red-500 focus-visible:ring-red-500',
              
              // Left addon modifier
              leftAddon && 'rounded-l-none',
              
              // Right addon modifier
              rightAddon && 'rounded-r-none',
              
              className
            )}
            aria-invalid={!!error}
            aria-describedby={
              error 
                ? `${id}-error` 
                : helperText 
                  ? `${id}-description` 
                  : undefined
            }
            {...props}
          />
          
          {rightAddon && (
            <div className="flex items-center justify-center rounded-r-md border border-l-0 border-gray-300 bg-gray-100 px-3 text-gray-500 dark:border-gray-600 dark:bg-gray-800">
              {rightAddon}
            </div>
          )}
        </div>
        
        {/* Error or helper text */}
        {error ? (
          <div className="flex items-center space-x-1 text-sm text-red-500" id={`${id}-error`}>
            <AlertCircle className="h-4 w-4" />
            <span>{error}</span>
          </div>
        ) : helperText ? (
          <p className="text-sm text-gray-500 dark:text-gray-400" id={`${id}-description`}>
            {helperText}
          </p>
        ) : null}
      </div>
    );
  }
);

Input.displayName = 'Input';

export default Input;