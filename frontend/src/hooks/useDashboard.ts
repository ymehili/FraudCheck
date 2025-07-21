'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { useAuth } from '@clerk/nextjs';
import { api } from '@/lib/api';
import { DashboardStats, AnalysisHistoryItem, PaginatedResponse } from '@/types/api';
import { FilterState } from '@/components/FilterControls';

interface UseDashboardOptions {
  refreshInterval?: number; // in milliseconds
  autoRefresh?: boolean;
  initialFilters?: Partial<FilterState>;
}

interface UseDashboardReturn {
  // Data
  stats: DashboardStats | null;
  recentAnalyses: AnalysisHistoryItem[];
  
  // Loading states
  isLoading: boolean;
  isRefreshing: boolean;
  
  // Error states
  error: string | null;
  
  // Actions
  refresh: () => Promise<void>;
  setAutoRefresh: (enabled: boolean) => void;
  updateFilters: (filters: Partial<FilterState>) => void;
  
  // Meta information
  lastUpdated: Date | null;
  refreshCount: number;
}

export function useDashboard(options: UseDashboardOptions = {}): UseDashboardReturn {
  const { getToken } = useAuth();
  const {
    refreshInterval = 30000, // 30 seconds default
    autoRefresh = true,
    initialFilters = {},
  } = options;

  // State
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [recentAnalyses, setRecentAnalyses] = useState<AnalysisHistoryItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [refreshCount, setRefreshCount] = useState(0);
  const [currentFilters, setCurrentFilters] = useState<Partial<FilterState>>(initialFilters);
  const [autoRefreshEnabled, setAutoRefreshEnabled] = useState(autoRefresh);

  // Refs for cleanup and interval management
  const refreshIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  // Fetch dashboard data
  const fetchDashboardData = useCallback(async (showLoading = false) => {
    try {
      if (showLoading) setIsLoading(true);
      setIsRefreshing(true);
      setError(null);

      // Cancel previous request
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }

      // Create new abort controller
      abortControllerRef.current = new AbortController();

      const token = await getToken();
      if (!token) {
        throw new Error('Authentication required');
      }

      // Prepare filters for API calls
      const dashboardFilters: any = {};
      if (currentFilters.dateRange?.start) {
        dashboardFilters.start_date = currentFilters.dateRange.start;
      }
      if (currentFilters.dateRange?.end) {
        dashboardFilters.end_date = currentFilters.dateRange.end;
      }
      if (currentFilters.riskScore?.min !== undefined && currentFilters.riskScore.min > 0) {
        dashboardFilters.risk_threshold = currentFilters.riskScore.min;
      }

      const historyFilters: any = {
        ...dashboardFilters,
      };
      if (currentFilters.status) {
        historyFilters.status = currentFilters.status;
      }
      if (currentFilters.riskScore?.min !== undefined) {
        historyFilters.min_risk_score = currentFilters.riskScore.min;
      }
      if (currentFilters.riskScore?.max !== undefined) {
        historyFilters.max_risk_score = currentFilters.riskScore.max;
      }

      // Fetch data concurrently
      const [statsResponse, historyResponse] = await Promise.all([
        api.getDashboardStats(token, dashboardFilters),
        api.getAnalysisHistory(token, 1, 10, historyFilters), // Get recent 10 analyses
      ]);

      // Update state
      setStats(statsResponse);
      setRecentAnalyses(historyResponse.items);
      setLastUpdated(new Date());
      setRefreshCount(prev => prev + 1);

    } catch (error) {
      if (error instanceof Error) {
        if (error.name === 'AbortError') {
          return; // Request was cancelled, don't update state
        }
        setError(error.message);
      } else {
        setError('Failed to fetch dashboard data');
      }
      console.error('Dashboard fetch error:', error);
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  }, [getToken, currentFilters]);

  // Manual refresh
  const refresh = useCallback(async () => {
    await fetchDashboardData(false);
  }, [fetchDashboardData]);

  // Update filters
  const updateFilters = useCallback((newFilters: Partial<FilterState>) => {
    setCurrentFilters(prev => ({ ...prev, ...newFilters }));
  }, []);

  // Set auto refresh
  const setAutoRefresh = useCallback((enabled: boolean) => {
    setAutoRefreshEnabled(enabled);
  }, []);

  // Initial data fetch
  useEffect(() => {
    fetchDashboardData(true);
  }, [fetchDashboardData]);

  // Auto-refresh setup
  useEffect(() => {
    if (!autoRefreshEnabled) {
      if (refreshIntervalRef.current) {
        clearInterval(refreshIntervalRef.current);
        refreshIntervalRef.current = null;
      }
      return;
    }

    // Set up auto-refresh interval
    refreshIntervalRef.current = setInterval(() => {
      if (!document.hidden) { // Only refresh when tab is visible
        fetchDashboardData(false);
      }
    }, refreshInterval);

    // Cleanup function
    return () => {
      if (refreshIntervalRef.current) {
        clearInterval(refreshIntervalRef.current);
        refreshIntervalRef.current = null;
      }
    };
  }, [autoRefreshEnabled, refreshInterval, fetchDashboardData]);

  // Page visibility handling
  useEffect(() => {
    const handleVisibilityChange = () => {
      if (!document.hidden && autoRefreshEnabled) {
        // Refresh when page becomes visible again
        fetchDashboardData(false);
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [fetchDashboardData, autoRefreshEnabled]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (refreshIntervalRef.current) {
        clearInterval(refreshIntervalRef.current);
      }
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

  return {
    stats,
    recentAnalyses,
    isLoading,
    isRefreshing,
    error,
    refresh,
    setAutoRefresh,
    updateFilters,
    lastUpdated,
    refreshCount,
  };
}

// Helper hook for getting dashboard stats with caching
export function useDashboardStats(filters?: Partial<FilterState>) {
  const { getToken } = useAuth();
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const cacheRef = useRef<Map<string, { data: DashboardStats; timestamp: number }>>(new Map());

  const fetchStats = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);

      const token = await getToken();
      if (!token) {
        throw new Error('Authentication required');
      }

      // Create cache key from filters
      const cacheKey = JSON.stringify(filters || {});
      const cached = cacheRef.current.get(cacheKey);
      const now = Date.now();

      // Return cached data if less than 5 minutes old
      if (cached && now - cached.timestamp < 5 * 60 * 1000) {
        setStats(cached.data);
        setIsLoading(false);
        return;
      }

      // Prepare filters for API
      const apiFilters: any = {};
      if (filters?.dateRange?.start) apiFilters.start_date = filters.dateRange.start;
      if (filters?.dateRange?.end) apiFilters.end_date = filters.dateRange.end;
      if (filters?.riskScore?.min) apiFilters.risk_threshold = filters.riskScore.min;

      const response = await api.getDashboardStats(token, apiFilters);
      
      // Cache the response
      cacheRef.current.set(cacheKey, { data: response, timestamp: now });
      
      setStats(response);
    } catch (error) {
      setError(error instanceof Error ? error.message : 'Failed to fetch stats');
      console.error('Stats fetch error:', error);
    } finally {
      setIsLoading(false);
    }
  }, [getToken, filters]);

  useEffect(() => {
    fetchStats();
  }, [fetchStats]);

  return { stats, isLoading, error, refetch: fetchStats };
}