"use client";

import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '@clerk/nextjs';
import Link from 'next/link';
import RiskScoreChart from '@/components/RiskScoreChart';
import { RiskDistribution, TrendDataPoint } from '@/types';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import Button from '@/components/ui/Button';
import { Skeleton } from '@/components/ui/skeleton';
import { Alert, AlertDescription } from '@/components/ui/alert';

interface DashboardStats {
  totalAnalyses: number;
  analysesToday: number;
  analysesThisWeek: number;
  analysesThisMonth: number;
  averageRiskScore: number;
  averageConfidence: number;
  riskDistribution: RiskDistribution;
  trendData: TrendDataPoint[];
}

export default function DashboardPage() {
  const { getToken } = useAuth();
  const [dashboardData, setDashboardData] = useState<DashboardStats | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchDashboardData = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);

      const token = await getToken();
      if (!token) {
        throw new Error('Authentication token not available');
      }

      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/dashboard/stats`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error('Failed to fetch dashboard data');
      }

      const data = await response.json();
      setDashboardData(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load dashboard data');
    } finally {
      setIsLoading(false);
    }
  }, [getToken]);

  useEffect(() => {
    fetchDashboardData();
  }, [fetchDashboardData]);

  const formatPercentage = (value: number) => {
    return `${Math.round(value * 100)}%`;
  };


  const StatCard = ({ title, value, subtitle, icon, trend }: {
    title: string;
    value: string | number;
    subtitle?: string;
    icon: React.ReactNode;
    trend?: { value: number; label: string };
  }) => (
    <Card>
      <CardContent>
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-muted-foreground">{title}</p>
            <p className="text-2xl font-semibold text-foreground">{value}</p>
            {subtitle && <p className="text-sm text-muted-foreground">{subtitle}</p>}
          </div>
          <div className="text-muted-foreground">
            {icon}
          </div>
        </div>
        {trend && (
          <div className="mt-4 flex items-center">
            <span className={`text-sm font-medium ${trend.value > 0 ? 'text-green-600' : 'text-red-600'}`}>
              {trend.value > 0 ? '+' : ''}{trend.value}%
            </span>
            <span className="text-sm text-muted-foreground ml-2">{trend.label}</span>
          </div>
        )}
      </CardContent>
    </Card>
  );

  const RiskDistributionChart = ({ distribution }: { distribution: RiskDistribution | null | undefined }) => {
    // Provide default values if distribution is null/undefined
    const safeDistribution = distribution || {
      low: 0,
      medium: 0,
      high: 0,
      critical: 0,
      total: 0
    };

    return (
      <Card>
        <CardHeader>
          <CardTitle>Risk Distribution</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {[
              { level: 'LOW', count: safeDistribution.low, color: 'bg-green-500' },
              { level: 'MEDIUM', count: safeDistribution.medium, color: 'bg-yellow-500' },
              { level: 'HIGH', count: safeDistribution.high, color: 'bg-red-500' },
              { level: 'CRITICAL', count: safeDistribution.critical, color: 'bg-red-600' }
            ].map((item) => {
              const percentage = safeDistribution.total > 0 ? (item.count / safeDistribution.total) * 100 : 0;
              return (
                <div key={item.level} className="flex items-center justify-between">
                  <div className="flex items-center space-x-3">
                    <div className={`w-3 h-3 rounded-full ${item.color}`}></div>
                    <span className="text-sm font-medium text-foreground">{item.level}</span>
                  </div>
                  <div className="flex items-center space-x-3">
                    <div className="w-32 bg-muted rounded-full h-2">
                      <div 
                        className={`h-2 rounded-full ${item.color}`}
                        style={{ width: `${percentage}%` }}
                      ></div>
                    </div>
                    <span className="text-sm text-muted-foreground w-12 text-right">{item.count}</span>
                  </div>
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>
    );
  };

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold text-foreground">Dashboard</h1>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {[1, 2, 3, 4].map((i) => (
            <Card key={i}>
              <CardContent>
                <div className="flex items-center justify-between">
                  <div className="space-y-2">
                    <Skeleton className="h-4 w-24" />
                    <Skeleton className="h-8 w-16" />
                  </div>
                  <Skeleton className="h-8 w-8" />
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold text-foreground">Dashboard</h1>
        </div>
        <Alert variant="destructive">
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.732-.833-2.5 0L4.268 18.5c-.77.833.192 2.5 1.732 2.5z" />
          </svg>
          <AlertDescription>
            <div>
              <h3 className="text-sm font-medium">Error loading dashboard</h3>
              <p className="text-sm mt-1">{error}</p>
            </div>
            <Button
              onClick={fetchDashboardData}
              variant="outline"
              size="sm"
              className="mt-4"
            >
              Try Again
            </Button>
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  if (!dashboardData) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold text-foreground">Dashboard</h1>
        </div>
        <Card>
          <CardContent className="text-center">
            <p className="text-muted-foreground">No dashboard data available</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Ensure dashboardData is properly structured with defaults
  const safeData = {
    totalAnalyses: dashboardData.totalAnalyses || 0,
    analysesToday: dashboardData.analysesToday || 0,
    analysesThisWeek: dashboardData.analysesThisWeek || 0,
    analysesThisMonth: dashboardData.analysesThisMonth || 0,
    averageRiskScore: dashboardData.averageRiskScore || 0,
    averageConfidence: dashboardData.averageConfidence || 0,
    riskDistribution: dashboardData.riskDistribution || {
      low: 0,
      medium: 0,
      high: 0,
      critical: 0,
      total: 0
    },
    trendData: dashboardData.trendData || []
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Dashboard</h1>
          <p className="text-muted-foreground">Overview of your check analysis activity</p>
        </div>
        <Link href="/upload">
          <Button variant="primary">
            Upload New Check
          </Button>
        </Link>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard
          title="Total Analyses"
          value={safeData.totalAnalyses}
          icon={
            <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          }
        />
        <StatCard
          title="Today"
          value={safeData.analysesToday}
          subtitle="analyses completed"
          icon={
            <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          }
        />
        <StatCard
          title="Average Risk Score"
          value={`${Math.round(safeData.averageRiskScore)}%`}
          subtitle="across all analyses"
          icon={
            <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
          }
        />
        <StatCard
          title="Average Confidence"
          value={formatPercentage(safeData.averageConfidence)}
          subtitle="detection confidence"
          icon={
            <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          }
        />
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <RiskDistributionChart distribution={safeData.riskDistribution} />
        
        {/* Sample Risk Score Chart */}
        {safeData.averageRiskScore > 0 && (
          <RiskScoreChart 
            riskScore={{
              overallScore: Math.round(safeData.averageRiskScore),
              categoryScores: {
                forensics: Math.round(safeData.averageRiskScore * 0.8),
                ocr: Math.round(safeData.averageRiskScore * 0.9),
                rules: Math.round(safeData.averageRiskScore * 0.7)
              },
              riskFactors: ['Sample risk factor'],
              confidenceLevel: safeData.averageConfidence,
              recommendation: safeData.averageRiskScore >= 80 ? 'CRITICAL' :
                            safeData.averageRiskScore >= 60 ? 'HIGH' :
                            safeData.averageRiskScore >= 30 ? 'MEDIUM' : 'LOW'
            }}
            size="medium"
          />
        )}
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Link href="/upload">
          <Card className="hover:shadow-md transition-shadow cursor-pointer">
            <CardContent>
              <div className="flex items-center space-x-4">
                <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center">
                  <svg className="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                  </svg>
                </div>
                <div>
                  <h3 className="text-lg font-medium text-foreground">Upload Check</h3>
                  <p className="text-sm text-muted-foreground">Start a new fraud analysis</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </Link>

        <Link href="/history">
          <Card className="hover:shadow-md transition-shadow cursor-pointer">
            <CardContent>
              <div className="flex items-center space-x-4">
                <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center">
                  <svg className="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
                <div>
                  <h3 className="text-lg font-medium text-foreground">View History</h3>
                  <p className="text-sm text-muted-foreground">Browse past analyses</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </Link>

        <Card>
          <CardContent>
            <div className="flex items-center space-x-4">
              <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center">
                <svg className="w-6 h-6 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
              </div>
              <div>
                <h3 className="text-lg font-medium text-foreground">Analytics</h3>
                <p className="text-sm text-muted-foreground">Detailed insights and trends</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Recent Activity */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Recent Activity</CardTitle>
            <Link
              href="/history"
              className="text-sm text-primary hover:text-primary/80"
            >
              View all
            </Link>
          </div>
        </CardHeader>
        <CardContent>
          <div className="text-center text-muted-foreground">
            <svg className="w-12 h-12 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            <p className="text-sm">No recent activity</p>
            <p className="text-xs text-muted-foreground/60 mt-1">Upload a check to get started</p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}