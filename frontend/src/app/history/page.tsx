"use client";

import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '@clerk/nextjs';
import { useRouter } from 'next/navigation';
import AnalysisHistory from '@/components/AnalysisHistory';
import FilterControls from '@/components/FilterControls';
import { EnhancedAnalysisResult, DashboardFilter, PaginationParams } from '@/types';

export default function HistoryPage() {
  const { getToken } = useAuth();
  const router = useRouter();
  const [analyses, setAnalyses] = useState<EnhancedAnalysisResult[]>([]);
  const [pagination, setPagination] = useState<PaginationParams>({
    page: 1,
    perPage: 20,
    sortField: 'analysisTimestamp',
    sortDirection: 'desc'
  });
  const [filters, setFilters] = useState<DashboardFilter>({});
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchAnalysisHistory = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);

      const token = await getToken();
      if (!token) {
        throw new Error('Authentication token not available');
      }

      // Build query parameters
      const params = new URLSearchParams();
      params.append('page', pagination.page.toString());
      params.append('per_page', pagination.perPage.toString());
      if (pagination.sortField) {
        params.append('sort_field', pagination.sortField);
      }
      if (pagination.sortDirection) {
        params.append('sort_direction', pagination.sortDirection);
      }

      // Add filters
      if (filters.timeRange) {
        params.append('time_range', filters.timeRange);
      }
      if (filters.customDateRange) {
        params.append('start_date', filters.customDateRange.start);
        params.append('end_date', filters.customDateRange.end);
      }
      if (filters.riskScoreRange) {
        if (filters.riskScoreRange.min !== undefined) {
          params.append('min_risk_score', filters.riskScoreRange.min.toString());
        }
        if (filters.riskScoreRange.max !== undefined) {
          params.append('max_risk_score', filters.riskScoreRange.max.toString());
        }
      }
      if (filters.riskLevels && filters.riskLevels.length > 0) {
        filters.riskLevels.forEach(level => {
          params.append('risk_levels', level);
        });
      }
      if (filters.fileTypes && filters.fileTypes.length > 0) {
        filters.fileTypes.forEach(type => {
          params.append('file_types', type);
        });
      }
      if (filters.hasViolations !== undefined) {
        params.append('has_violations', filters.hasViolations.toString());
      }
      if (filters.minConfidence !== undefined) {
        params.append('min_confidence', filters.minConfidence.toString());
      }

      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/dashboard/history?${params.toString()}`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error('Failed to fetch analysis history');
      }

      const data = await response.json();
      
      // Transform API response to match our types
      const transformedAnalyses: EnhancedAnalysisResult[] = data.analyses.map((analysis: {
        id: string;
        file_id: string;
        filename: string;
        file_size: number;
        mime_type: string;
        upload_timestamp: string;
        analysis_timestamp: string;
        risk_score_details: {
          overall_score: number;
          category_scores: Record<string, number>;
          risk_factors: string[];
          confidence_level: number;
          recommendation: string;
        };
        forensics_score: number;
        ocr_confidence: number;
        overall_risk_score: number;
        violations: string[];
        processing_time: number | null;
      }) => ({
        id: analysis.id,
        fileId: analysis.file_id,
        filename: analysis.filename,
        fileSize: analysis.file_size,
        mimeType: analysis.mime_type,
        uploadTimestamp: analysis.upload_timestamp,
        analysisTimestamp: analysis.analysis_timestamp,
        riskScore: {
          overallScore: analysis.risk_score_details.overall_score,
          categoryScores: analysis.risk_score_details.category_scores,
          riskFactors: analysis.risk_score_details.risk_factors,
          confidenceLevel: analysis.risk_score_details.confidence_level,
          recommendation: analysis.risk_score_details.recommendation
        },
        forensicsScore: analysis.forensics_score,
        ocrConfidence: analysis.ocr_confidence,
        overallRiskScore: analysis.overall_risk_score,
        violations: analysis.violations,
        processingTime: analysis.processing_time
      }));

      setAnalyses(transformedAnalyses);
      
      // Update pagination info if available
      if (data.pagination) {
        setPagination(prev => ({
          ...prev,
          page: data.pagination.page,
          perPage: data.pagination.per_page
        }));
      }

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load analysis history');
    } finally {
      setIsLoading(false);
    }
  }, [getToken, pagination, filters]);

  useEffect(() => {
    fetchAnalysisHistory();
  }, [fetchAnalysisHistory]);

  const handlePageChange = (page: number) => {
    setPagination(prev => ({ ...prev, page }));
  };

  const handleSortChange = (field: string, direction: 'asc' | 'desc') => {
    setPagination(prev => ({ 
      ...prev, 
      sortField: field, 
      sortDirection: direction,
      page: 1 // Reset to first page when sorting
    }));
  };

  const handleFiltersChange = (newFilters: DashboardFilter) => {
    setFilters(newFilters);
    setPagination(prev => ({ ...prev, page: 1 })); // Reset to first page when filtering
  };

  const handleFiltersReset = () => {
    setFilters({});
    setPagination(prev => ({ ...prev, page: 1 }));
  };

  const handleViewDetails = (analysisId: string) => {
    router.push(`/analysis/${analysisId}`);
  };

  const handleExportPDF = async (analysisId: string) => {
    try {
      const token = await getToken();
      if (!token) {
        throw new Error('Authentication token not available');
      }

      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/analysis/${analysisId}/export-pdf`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        throw new Error('Failed to export PDF');
      }

      // Create a blob from the response
      const blob = await response.blob();
      
      // Create a download link
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `analysis-${analysisId}.pdf`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);

    } catch (err) {
      console.error('Export failed:', err);
      // You might want to show a toast notification here
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Analysis History</h1>
          <p className="text-gray-600">Review and manage your check analysis results</p>
        </div>
        <div className="flex items-center space-x-4">
          <button
            onClick={fetchAnalysisHistory}
            className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 transition-colors"
          >
            <svg className="w-4 h-4 inline mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            Refresh
          </button>
        </div>
      </div>

      {/* Filters */}
      <FilterControls
        filters={filters}
        onFiltersChange={handleFiltersChange}
        onReset={handleFiltersReset}
      />

      {/* Error State */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="flex items-center">
            <svg className="w-5 h-5 text-red-400 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.732-.833-2.5 0L4.268 18.5c-.77.833.192 2.5 1.732 2.5z" />
            </svg>
            <div>
              <h3 className="text-sm font-medium text-red-800">Error loading history</h3>
              <p className="text-sm text-red-700 mt-1">{error}</p>
            </div>
          </div>
          <button
            onClick={fetchAnalysisHistory}
            className="mt-3 px-4 py-2 bg-red-100 text-red-800 rounded-md hover:bg-red-200 transition-colors text-sm"
          >
            Try Again
          </button>
        </div>
      )}

      {/* Analysis History Table */}
      <AnalysisHistory
        analyses={analyses}
        pagination={pagination}
        onPageChange={handlePageChange}
        onSortChange={handleSortChange}
        onViewDetails={handleViewDetails}
        onExportPDF={handleExportPDF}
        isLoading={isLoading}
      />

      {/* Empty State */}
      {!isLoading && !error && analyses.length === 0 && (
        <div className="bg-white rounded-lg shadow-sm border p-12 text-center">
          <svg className="w-16 h-16 text-gray-400 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          <h3 className="text-lg font-medium text-gray-900 mb-2">No analyses found</h3>
          <p className="text-gray-600 mb-6">
            {Object.keys(filters).length > 0 
              ? 'No analyses match your current filters. Try adjusting your search criteria.'
              : 'You haven\'t analyzed any checks yet. Upload a check to get started.'
            }
          </p>
          <div className="flex justify-center space-x-4">
            {Object.keys(filters).length > 0 && (
              <button
                onClick={handleFiltersReset}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 transition-colors"
              >
                Clear Filters
              </button>
            )}
            <button
              onClick={() => router.push('/upload')}
              className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 transition-colors"
            >
              Upload Check
            </button>
          </div>
        </div>
      )}

      {/* Results Summary */}
      {!isLoading && !error && analyses.length > 0 && (
        <div className="bg-white rounded-lg shadow-sm border p-4">
          <div className="flex items-center justify-between text-sm text-gray-600">
            <span>
              Showing {analyses.length} result{analyses.length !== 1 ? 's' : ''}
              {Object.keys(filters).length > 0 && ' with active filters'}
            </span>
            <div className="flex items-center space-x-4">
              <span>
                Page {pagination.page} of {Math.ceil(pagination.page)}
              </span>
              <div className="flex items-center space-x-2">
                <label className="text-sm text-gray-600">Show:</label>
                <select
                  value={pagination.perPage}
                  onChange={(e) => setPagination(prev => ({ 
                    ...prev, 
                    perPage: parseInt(e.target.value),
                    page: 1 
                  }))}
                  className="text-sm border-gray-300 rounded-md"
                >
                  <option value={10}>10</option>
                  <option value={20}>20</option>
                  <option value={50}>50</option>
                  <option value={100}>100</option>
                </select>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}