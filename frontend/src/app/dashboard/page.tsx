'use client';

import { useState, useEffect } from 'react';
import { useAuth } from '@clerk/nextjs';
import { NavigationBar } from '@/components/NavigationBar';
import { RiskScoreChart } from '@/components/RiskScoreChart';
import { FilterControls } from '@/components/FilterControls';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Skeleton } from '@/components/ui/skeleton';
import { 
  TrendingUp, 
  TrendingDown, 
  Users, 
  FileText, 
  AlertTriangle,
  CheckCircle,
  Clock,
  Plus
} from 'lucide-react';
import { api } from '@/lib/api';
import { DashboardStats } from '@/types/api';
import { formatNumber, formatPercentage, cn } from '@/lib/utils';
import { ROUTES, RISK_THRESHOLDS } from '@/lib/constants';
import Link from 'next/link';

interface DashboardFilters {
  start_date?: string;
  end_date?: string;
  risk_threshold?: number;
}

export default function DashboardPage() {
  const { getToken } = useAuth();
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState<DashboardFilters>({});

  const fetchDashboardStats = async (currentFilters: DashboardFilters = {}) => {
    try {
      setIsLoading(true);
      setError(null);

      const token = await getToken();
      if (!token) {
        throw new Error('Authentication token not available');
      }

      const dashboardData = await api.getDashboardStats(token, currentFilters);
      setStats(dashboardData);
    } catch (error) {
      console.error('Failed to fetch dashboard stats:', error);
      setError(error instanceof Error ? error.message : 'Failed to load dashboard data');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardStats(filters);
  }, []);

  const handleFiltersChange = (newFilters: DashboardFilters) => {
    setFilters(newFilters);
    fetchDashboardStats(newFilters);
  };

  const handleRefresh = () => {
    fetchDashboardStats(filters);
  };

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50">
        <NavigationBar />
        <div className="max-w-7xl mx-auto px-4 py-12">
          <Alert variant="destructive">
            <AlertTriangle className="h-4 w-4" />
            <AlertDescription>
              {error}
              <Button 
                variant="outline" 
                size="sm" 
                onClick={handleRefresh}
                className="ml-4"
              >
                Try Again
              </Button>
            </AlertDescription>
          </Alert>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <NavigationBar />
      
      <div className="max-w-7xl mx-auto px-4 py-12">
        {/* Header */}
        <div className="flex justify-between items-start mb-8">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 mb-2">
              Dashboard
            </h1>
            <p className="text-lg text-gray-600">
              Monitor fraud detection analytics and system performance
            </p>
          </div>
          <Link href={ROUTES.UPLOAD}>
            <Button>
              <Plus className="h-4 w-4 mr-2" />
              New Analysis
            </Button>
          </Link>
        </div>

        {/* Filters */}
        <div className="mb-8">
          <FilterControls
            filters={filters}
            onFiltersChange={handleFiltersChange}
            isLoading={isLoading}
          />
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          {/* Total Analyses */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Analyses</CardTitle>
              <FileText className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              {isLoading ? (
                <div className="space-y-2">
                  <Skeleton className="h-8 w-16" />
                  <Skeleton className="h-4 w-20" />
                </div>
              ) : (
                <div>
                  <div className="text-2xl font-bold">
                    {formatNumber(stats?.total_analyses || 0)}
                  </div>
                  <p className="text-xs text-muted-foreground">
                    {stats?.analyses_change !== undefined && (
                      <span className={cn(
                        "flex items-center",
                        stats.analyses_change >= 0 ? "text-green-600" : "text-red-600"
                      )}>
                        {stats.analyses_change >= 0 ? (
                          <TrendingUp className="h-3 w-3 mr-1" />
                        ) : (
                          <TrendingDown className="h-3 w-3 mr-1" />
                        )}
                        {Math.abs(stats.analyses_change)}% from last period
                      </span>
                    )}
                  </p>
                </div>
              )}
            </CardContent>
          </Card>

          {/* High Risk Detected */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">High Risk Detected</CardTitle>
              <AlertTriangle className="h-4 w-4 text-red-500" />
            </CardHeader>
            <CardContent>
              {isLoading ? (
                <div className="space-y-2">
                  <Skeleton className="h-8 w-16" />
                  <Skeleton className="h-4 w-20" />
                </div>
              ) : (
                <div>
                  <div className="text-2xl font-bold text-red-600">
                    {formatNumber(stats?.high_risk_count || 0)}
                  </div>
                  <p className="text-xs text-muted-foreground">
                    {stats?.total_analyses ? 
                      formatPercentage((stats.high_risk_count || 0) / stats.total_analyses) : '0%'
                    } of total analyses
                  </p>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Average Risk Score */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Average Risk Score</CardTitle>
              <TrendingUp className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              {isLoading ? (
                <div className="space-y-2">
                  <Skeleton className="h-8 w-16" />
                  <Skeleton className="h-4 w-20" />
                </div>
              ) : (
                <div>
                  <div className="text-2xl font-bold">
                    {(stats?.average_risk_score || 0).toFixed(1)}
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Out of 100 scale
                  </p>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Processing Time */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Avg Processing Time</CardTitle>
              <Clock className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              {isLoading ? (
                <div className="space-y-2">
                  <Skeleton className="h-8 w-16" />
                  <Skeleton className="h-4 w-20" />
                </div>
              ) : (
                <div>
                  <div className="text-2xl font-bold">
                    {(stats?.average_processing_time || 0).toFixed(1)}s
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Per analysis
                  </p>
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Charts Row */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
          {/* Risk Distribution Chart */}
          <Card>
            <CardHeader>
              <CardTitle>Risk Score Distribution</CardTitle>
              <CardDescription>
                Distribution of risk scores across all analyses
              </CardDescription>
            </CardHeader>
            <CardContent>
              {isLoading ? (
                <div className="space-y-4">
                  <Skeleton className="h-4 w-full" />
                  <Skeleton className="h-4 w-full" />
                  <Skeleton className="h-4 w-3/4" />
                </div>
              ) : (
                <RiskScoreChart 
                  data={stats?.risk_distribution || []}
                  showLegend={true}
                />
              )}
            </CardContent>
          </Card>

          {/* Recent Activity */}
          <Card>
            <CardHeader>
              <CardTitle>Recent Activity</CardTitle>
              <CardDescription>
                Latest analysis results and system activity
              </CardDescription>
            </CardHeader>
            <CardContent>
              {isLoading ? (
                <div className="space-y-4">
                  {[...Array(5)].map((_, i) => (
                    <div key={i} className="flex items-center space-x-3">
                      <Skeleton className="h-8 w-8 rounded-full" />
                      <div className="space-y-2 flex-1">
                        <Skeleton className="h-4 w-full" />
                        <Skeleton className="h-3 w-1/2" />
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="space-y-4">
                  {stats?.recent_analyses?.slice(0, 5).map((analysis) => (
                    <div key={analysis.analysis_id} className="flex items-center space-x-3">
                      <div className={cn(
                        "w-2 h-2 rounded-full",
                        analysis.risk_score >= RISK_THRESHOLDS.HIGH ? "bg-red-500" :
                        analysis.risk_score >= RISK_THRESHOLDS.MEDIUM ? "bg-yellow-500" :
                        "bg-green-500"
                      )} />
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-gray-900 truncate">
                          Analysis #{analysis.analysis_id.slice(-8)}
                        </p>
                        <p className="text-xs text-gray-500">
                          Risk Score: {analysis.risk_score} • {new Date(analysis.created_at).toLocaleDateString()}
                        </p>
                      </div>
                      <Link href={`${ROUTES.ANALYSIS}/${analysis.analysis_id}`}>
                        <Button variant="ghost" size="sm">View</Button>
                      </Link>
                    </div>
                  )) || (
                    <div className="text-center py-8">
                      <FileText className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                      <p className="text-gray-500">No recent analyses found</p>
                      <Link href={ROUTES.UPLOAD}>
                        <Button variant="outline" className="mt-4">
                          Start First Analysis
                        </Button>
                      </Link>
                    </div>
                  )}
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Quick Actions */}
        <Card>
          <CardHeader>
            <CardTitle>Quick Actions</CardTitle>
            <CardDescription>
              Common tasks and navigation shortcuts
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <Link href={ROUTES.UPLOAD}>
                <Button className="w-full justify-start" variant="outline">
                  <Plus className="h-4 w-4 mr-2" />
                  New Analysis
                </Button>
              </Link>
              <Link href={ROUTES.HISTORY}>
                <Button className="w-full justify-start" variant="outline">
                  <Clock className="h-4 w-4 mr-2" />
                  View History
                </Button>
              </Link>
              <Button 
                className="w-full justify-start" 
                variant="outline"
                onClick={handleRefresh}
              >
                <TrendingUp className="h-4 w-4 mr-2" />
                Refresh Data
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}