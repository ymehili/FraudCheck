'use client';

import { Loader2, Upload, FileText, Camera, RefreshCw } from 'lucide-react';
import { cn } from '@/lib/utils';

interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

export function LoadingSpinner({ size = 'md', className }: LoadingSpinnerProps) {
  const sizeClasses = {
    sm: 'h-4 w-4',
    md: 'h-8 w-8',
    lg: 'h-12 w-12'
  };

  return (
    <Loader2 className={cn(sizeClasses[size], 'animate-spin', className)} />
  );
}

interface LoadingStateProps {
  title?: string;
  description?: string;
  icon?: React.ReactNode;
  className?: string;
  size?: 'sm' | 'md' | 'lg';
}

export function LoadingState({ 
  title, 
  description, 
  icon,
  className,
  size = 'md'
}: LoadingStateProps) {
  const sizeClasses = {
    sm: 'py-6',
    md: 'py-12',
    lg: 'py-24'
  };

  const iconSizes = {
    sm: 'h-6 w-6',
    md: 'h-12 w-12',
    lg: 'h-16 w-16'
  };

  return (
    <div className={cn('text-center', sizeClasses[size], className)}>
      <div className="mx-auto mb-4 flex items-center justify-center">
        {icon || <LoadingSpinner size={size === 'sm' ? 'sm' : size === 'md' ? 'md' : 'lg'} />}
      </div>
      {title && (
        <h3 className={cn(
          'font-medium text-gray-900 mb-2',
          size === 'sm' ? 'text-sm' : size === 'md' ? 'text-lg' : 'text-xl'
        )}>
          {title}
        </h3>
      )}
      {description && (
        <p className={cn(
          'text-gray-600 max-w-md mx-auto',
          size === 'sm' ? 'text-xs' : 'text-sm'
        )}>
          {description}
        </p>
      )}
    </div>
  );
}

// Specific loading states for different operations
export function FileUploadLoadingState() {
  return (
    <LoadingState
      title="Uploading File"
      description="Please wait while we securely upload your file..."
      icon={<Upload className="h-12 w-12 text-blue-600 animate-pulse" />}
    />
  );
}

export function AnalysisLoadingState({ progress }: { progress?: number }) {
  return (
    <div className="text-center py-12">
      <div className="mx-auto mb-4 w-16 h-16 rounded-full bg-blue-100 flex items-center justify-center">
        <FileText className="h-8 w-8 text-blue-600 animate-pulse" />
      </div>
      <h3 className="text-lg font-medium text-gray-900 mb-2">
        Analyzing Check
      </h3>
      <p className="text-gray-600 mb-6">
        Our AI is examining your check for fraud indicators...
      </p>
      
      {progress !== undefined && (
        <div className="max-w-xs mx-auto">
          <div className="flex justify-between text-sm text-gray-600 mb-2">
            <span>Progress</span>
            <span>{Math.round(progress)}%</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div 
              className="bg-blue-600 h-2 rounded-full transition-all duration-300 ease-out"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
      )}
    </div>
  );
}

export function CameraLoadingState() {
  return (
    <LoadingState
      title="Initializing Camera"
      description="Please allow camera access when prompted..."
      icon={<Camera className="h-12 w-12 text-green-600 animate-pulse" />}
    />
  );
}

export function DashboardLoadingState() {
  return (
    <LoadingState
      title="Loading Dashboard"
      description="Fetching your latest analytics and reports..."
      icon={<RefreshCw className="h-12 w-12 text-purple-600 animate-spin" />}
    />
  );
}

// Button Loading State
interface LoadingButtonProps {
  isLoading: boolean;
  children: React.ReactNode;
  loadingText?: string;
  className?: string;
  [key: string]: unknown;
}

export function LoadingButton({ 
  isLoading, 
  children, 
  loadingText,
  className,
  ...props 
}: LoadingButtonProps) {
  return (
    <button
      className={cn(
        'inline-flex items-center justify-center',
        isLoading && 'cursor-not-allowed opacity-70',
        className
      )}
      disabled={isLoading}
      {...props}
    >
      {isLoading && <LoadingSpinner size="sm" className="mr-2" />}
      {isLoading && loadingText ? loadingText : children}
    </button>
  );
}

// Page Loading Overlay
interface LoadingOverlayProps {
  isVisible: boolean;
  message?: string;
  className?: string;
}

export function LoadingOverlay({ 
  isVisible, 
  message = "Loading...", 
  className 
}: LoadingOverlayProps) {
  if (!isVisible) return null;

  return (
    <div className={cn(
      'fixed inset-0 z-50 flex items-center justify-center',
      'bg-white bg-opacity-75 backdrop-blur-sm',
      className
    )}>
      <div className="text-center">
        <LoadingSpinner size="lg" className="text-blue-600 mb-4" />
        <p className="text-lg font-medium text-gray-900">
          {message}
        </p>
      </div>
    </div>
  );
}

// Inline Loading State (for small components)
interface InlineLoadingProps {
  text?: string;
  className?: string;
}

export function InlineLoading({ text = "Loading...", className }: InlineLoadingProps) {
  return (
    <div className={cn('flex items-center space-x-2 text-gray-600', className)}>
      <LoadingSpinner size="sm" />
      <span className="text-sm">{text}</span>
    </div>
  );
}

// Data Loading Placeholder
interface DataLoadingProps {
  rows?: number;
  className?: string;
}

export function DataLoading({ rows = 3, className }: DataLoadingProps) {
  return (
    <div className={cn('space-y-3', className)}>
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="animate-pulse">
          <div className="h-4 bg-gray-200 rounded w-full" />
        </div>
      ))}
    </div>
  );
}

// Empty State (not loading, but no data)
interface EmptyStateProps {
  title: string;
  description: string;
  icon?: React.ReactNode;
  action?: React.ReactNode;
  className?: string;
}

export function EmptyState({ 
  title, 
  description, 
  icon, 
  action, 
  className 
}: EmptyStateProps) {
  return (
    <div className={cn('text-center py-12', className)}>
      {icon && (
        <div className="mx-auto mb-4 h-12 w-12 text-gray-400">
          {icon}
        </div>
      )}
      <h3 className="text-lg font-medium text-gray-900 mb-2">
        {title}
      </h3>
      <p className="text-gray-600 mb-6 max-w-md mx-auto">
        {description}
      </p>
      {action}
    </div>
  );
}