'use client';

import React, { Component, ErrorInfo, ReactNode } from 'react';
import { AlertTriangle, RefreshCw, Home, ArrowLeft } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
  showDetails?: boolean;
}

interface State {
  hasError: boolean;
  error?: Error;
  errorInfo?: ErrorInfo;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Uncaught error:', error, errorInfo);
    this.setState({
      error,
      errorInfo,
    });
  }

  public render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <ErrorFallback
          error={this.state.error}
          errorInfo={this.state.errorInfo}
          resetError={() => this.setState({ hasError: false, error: undefined, errorInfo: undefined })}
          showDetails={this.props.showDetails}
        />
      );
    }

    return this.props.children;
  }
}

interface ErrorFallbackProps {
  error?: Error;
  errorInfo?: ErrorInfo;
  resetError: () => void;
  showDetails?: boolean;
}

function ErrorFallback({ error, errorInfo, resetError, showDetails = false }: ErrorFallbackProps) {
  const handleGoHome = () => {
    window.location.href = '/';
  };

  const handleGoBack = () => {
    window.history.back();
  };

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4">
      <Card className="max-w-2xl w-full">
        <CardHeader className="text-center">
          <div className="mx-auto mb-4 h-16 w-16 rounded-full bg-red-100 flex items-center justify-center">
            <AlertTriangle className="h-8 w-8 text-red-600" />
          </div>
          <CardTitle className="text-2xl font-bold text-gray-900">
            Something went wrong
          </CardTitle>
          <CardDescription className="text-lg">
            We encountered an unexpected error while processing your request.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="text-center space-y-4">
            <p className="text-gray-600">
              Don&apos;t worry, this has been automatically reported to our team. 
              You can try refreshing the page or go back to continue using the application.
            </p>
            
            <div className="flex flex-col sm:flex-row gap-3 justify-center">
              <Button onClick={resetError} className="flex items-center">
                <RefreshCw className="h-4 w-4 mr-2" />
                Try Again
              </Button>
              <Button variant="outline" onClick={handleGoBack} className="flex items-center">
                <ArrowLeft className="h-4 w-4 mr-2" />
                Go Back
              </Button>
              <Button variant="outline" onClick={handleGoHome} className="flex items-center">
                <Home className="h-4 w-4 mr-2" />
                Go Home
              </Button>
            </div>
          </div>

          {showDetails && error && (
            <Alert variant="destructive">
              <AlertTriangle className="h-4 w-4" />
              <AlertDescription>
                <details className="mt-2">
                  <summary className="cursor-pointer font-medium mb-2">
                    Technical Details (Click to expand)
                  </summary>
                  <div className="mt-2 p-3 bg-gray-50 rounded border text-xs font-mono">
                    <div className="mb-2">
                      <strong>Error:</strong> {error.message}
                    </div>
                    {error.stack && (
                      <div>
                        <strong>Stack Trace:</strong>
                        <pre className="whitespace-pre-wrap mt-1">{error.stack}</pre>
                      </div>
                    )}
                    {errorInfo && (
                      <div className="mt-2">
                        <strong>Component Stack:</strong>
                        <pre className="whitespace-pre-wrap mt-1">{errorInfo.componentStack}</pre>
                      </div>
                    )}
                  </div>
                </details>
              </AlertDescription>
            </Alert>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

// Simple Error Display Component
interface ErrorDisplayProps {
  title?: string;
  message?: string;
  onRetry?: () => void;
  onGoBack?: () => void;
  showHomeButton?: boolean;
  className?: string;
}

export function ErrorDisplay({
  title = "Something went wrong",
  message = "We encountered an error while processing your request.",
  onRetry,
  onGoBack,
  showHomeButton = false,
  className = ""
}: ErrorDisplayProps) {
  const handleGoHome = () => {
    window.location.href = '/';
  };

  const handleGoBack = () => {
    if (onGoBack) {
      onGoBack();
    } else {
      window.history.back();
    }
  };

  return (
    <div className={`text-center py-12 ${className}`}>
      <div className="mx-auto mb-4 h-12 w-12 rounded-full bg-red-100 flex items-center justify-center">
        <AlertTriangle className="h-6 w-6 text-red-600" />
      </div>
      <h3 className="text-lg font-medium text-gray-900 mb-2">
        {title}
      </h3>
      <p className="text-gray-600 mb-6 max-w-md mx-auto">
        {message}
      </p>
      <div className="flex flex-col sm:flex-row gap-3 justify-center">
        {onRetry && (
          <Button onClick={onRetry} className="flex items-center">
            <RefreshCw className="h-4 w-4 mr-2" />
            Try Again
          </Button>
        )}
        <Button variant="outline" onClick={handleGoBack} className="flex items-center">
          <ArrowLeft className="h-4 w-4 mr-2" />
          Go Back
        </Button>
        {showHomeButton && (
          <Button variant="outline" onClick={handleGoHome} className="flex items-center">
            <Home className="h-4 w-4 mr-2" />
            Go Home
          </Button>
        )}
      </div>
    </div>
  );
}

// Network Error Display
export function NetworkErrorDisplay({ onRetry }: { onRetry?: () => void }) {
  return (
    <ErrorDisplay
      title="Connection Error"
      message="Unable to connect to our servers. Please check your internet connection and try again."
      onRetry={onRetry}
    />
  );
}

// 404 Error Display  
export function NotFoundDisplay() {
  return (
    <ErrorDisplay
      title="Page Not Found"
      message="The page you're looking for doesn't exist or may have been moved."
      showHomeButton={true}
    />
  );
}

// Unauthorized Error Display
export function UnauthorizedDisplay() {
  const handleSignIn = () => {
    window.location.href = '/sign-in';
  };

  return (
    <div className="text-center py-12">
      <div className="mx-auto mb-4 h-12 w-12 rounded-full bg-yellow-100 flex items-center justify-center">
        <AlertTriangle className="h-6 w-6 text-yellow-600" />
      </div>
      <h3 className="text-lg font-medium text-gray-900 mb-2">
        Access Denied
      </h3>
      <p className="text-gray-600 mb-6 max-w-md mx-auto">
        You need to be signed in to access this page.
      </p>
      <Button onClick={handleSignIn}>
        Sign In
      </Button>
    </div>
  );
}