import React from 'react';
import { cn } from '../../utils/cn';
import { AlertCircle, CheckCircle, Info, XCircle, X } from 'lucide-react';

export interface AlertProps {
  variant?: 'info' | 'success' | 'warning' | 'error';
  title?: string;
  children: React.ReactNode;
  onClose?: () => void;
  className?: string;
}

const Alert: React.FC<AlertProps> = ({
  variant = 'info',
  title,
  children,
  onClose,
  className,
}) => {
  const getIcon = () => {
    switch (variant) {
      case 'info':
        return <Info className="h-5 w-5" />;
      case 'success':
        return <CheckCircle className="h-5 w-5" />;
      case 'warning':
        return <AlertCircle className="h-5 w-5" />;
      case 'error':
        return <XCircle className="h-5 w-5" />;
    }
  };

  return (
    <div
      className={cn(
        'relative rounded-lg border p-4',
        {
          'bg-blue-50 border-blue-200 text-blue-800 dark:bg-blue-900/30 dark:border-blue-800 dark:text-blue-300':
            variant === 'info',
          'bg-green-50 border-green-200 text-green-800 dark:bg-green-900/30 dark:border-green-800 dark:text-green-300':
            variant === 'success',
          'bg-yellow-50 border-yellow-200 text-yellow-800 dark:bg-yellow-900/30 dark:border-yellow-800 dark:text-yellow-300':
            variant === 'warning',
          'bg-red-50 border-red-200 text-red-800 dark:bg-red-900/30 dark:border-red-800 dark:text-red-300':
            variant === 'error',
        },
        className
      )}
      role="alert"
    >
      <div className="flex">
        <div className="flex-shrink-0">{getIcon()}</div>
        <div className="ml-3 flex-1">
          {title && <h3 className="text-sm font-medium">{title}</h3>}
          <div className={cn('text-sm', title && 'mt-2')}>{children}</div>
        </div>
        {onClose && (
          <button
            type="button"
            className={cn(
              'ml-auto -mx-1.5 -my-1.5 rounded-lg p-1.5 inline-flex items-center justify-center h-8 w-8',
              {
                'hover:bg-blue-200 focus:ring-blue-400 dark:hover:bg-blue-800':
                  variant === 'info',
                'hover:bg-green-200 focus:ring-green-400 dark:hover:bg-green-800':
                  variant === 'success',
                'hover:bg-yellow-200 focus:ring-yellow-400 dark:hover:bg-yellow-800':
                  variant === 'warning',
                'hover:bg-red-200 focus:ring-red-400 dark:hover:bg-red-800':
                  variant === 'error',
              }
            )}
            onClick={onClose}
            aria-label="Close"
          >
            <span className="sr-only">Close</span>
            <X className="h-5 w-5" />
          </button>
        )}
      </div>
    </div>
  );
};

export default Alert;