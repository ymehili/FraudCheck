'use client';

import { useState, useEffect } from 'react';
import { useAuth } from '@clerk/nextjs';
import { NavigationBar } from '@/components/NavigationBar';
import { FilterControls } from '@/components/FilterControls';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { 
  AlertTriangle,
  FileText,
  Eye,
  Download,
  ChevronLeft,
  ChevronRight,
  RefreshCw,
  Filter
} from 'lucide-react';
import { usePDFGenerator } from '@/components/PDFGenerator';
import { api } from '@/lib/api';
import { AnalysisHistoryItem, PaginatedResponse } from '@/types/api';
import { formatDate, getRiskLevel, cn } from '@/lib/utils';
import { ROUTES, RISK_THRESHOLDS } from '@/lib/constants';
import Link from 'next/link';

interface HistoryFilters {
  start_date?: string;
  end_date?: string;
  min_risk_score?: number;
  max_risk_score?: number;
  status?: string;
}

export default function HistoryPage() {
  const { getToken } = useAuth();
  const { generateAnalysisReport, isGenerating } = usePDFGenerator();
  const [analyses, setAnalyses] = useState<AnalysisHistoryItem[]>([]);
  const [pagination, setPagination] = useState({
    page: 1,
    size: 20,
    total: 0,
    pages: 0
  });
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState<HistoryFilters>({});
  const [showFilters, setShowFilters] = useState(false);

  const fetchAnalysisHistory = async (
    page: number = 1, 
    currentFilters: HistoryFilters = {}
  ) => {
    try {
      setIsLoading(true);
      setError(null);

      const token = await getToken();
      if (!token) {
        throw new Error('Authentication token not available');
      }

      const response = await api.getAnalysisHistory(
        token, 
        page, 
        pagination.size, 
        currentFilters
      );
      
      setAnalyses(response.items);
      setPagination({
        page: response.page,
        size: response.size,
        total: response.total,
        pages: response.pages
      });
    } catch (error) {
      console.error('Failed to fetch analysis history:', error);
      setError(error instanceof Error ? error.message : 'Failed to load analysis history');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchAnalysisHistory(1, filters);
  }, []);

  const handleFiltersChange = (newFilters: HistoryFilters) => {
    setFilters(newFilters);
    fetchAnalysisHistory(1, newFilters);
  };

  const handlePageChange = (newPage: number) => {
    if (newPage >= 1 && newPage <= pagination.pages) {
      fetchAnalysisHistory(newPage, filters);
    }
  };

  const handleRefresh = () => {
    fetchAnalysisHistory(pagination.page, filters);
  };

  const handleDownloadPDF = async (analysisId: string) => {
    try {
      const token = await getToken();
      if (!token) {
        throw new Error('Authentication token not available');
      }

      // Get the full analysis data
      const analysisData = await api.getAnalysis(analysisId, token);
      
      // Generate PDF
      await generateAnalysisReport(
        analysisData, 
        `check-analysis-${analysisId.slice(-8)}.pdf`
      );
    } catch (error) {
      console.error('Failed to download PDF:', error);
    }
  };

  const getRiskBadgeVariant = (riskScore: number) => {
    if (riskScore >= RISK_THRESHOLDS.HIGH) return 'destructive';
    if (riskScore >= RISK_THRESHOLDS.MEDIUM) return 'default';
    return 'secondary';
  };

  const getStatusBadgeVariant = (status: string) => {
    switch (status.toLowerCase()) {
      case 'completed':
        return 'default';
      case 'processing':
        return 'secondary';
      case 'failed':
        return 'destructive';
      default:
        return 'outline';
    }
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
              Analysis History
            </h1>
            <p className="text-lg text-gray-600">
              View and manage all your check analysis results
            </p>
          </div>
          <div className="flex space-x-2">
            <Button
              variant="outline"
              onClick={() => setShowFilters(!showFilters)}
            >
              <Filter className="h-4 w-4 mr-2" />
              Filters
            </Button>
            <Button
              variant="outline"
              onClick={handleRefresh}
              disabled={isLoading}
            >
              <RefreshCw className={cn("h-4 w-4 mr-2", isLoading && "animate-spin")} />
              Refresh
            </Button>
          </div>
        </div>

        {/* Filters */}
        {showFilters && (
          <div className="mb-8">
            <Card>
              <CardHeader>
                <CardTitle>Filter Results</CardTitle>
                <CardDescription>
                  Narrow down the analysis history by date, risk score, or status
                </CardDescription>
              </CardHeader>
              <CardContent>
                <FilterControls
                  filters={filters}
                  onFiltersChange={handleFiltersChange}
                  isLoading={isLoading}
                  showStatusFilter={true}
                />
              </CardContent>
            </Card>
          </div>
        )}

        {/* Statistics Summary */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium">Total Analyses</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {isLoading ? <Skeleton className="h-8 w-16" /> : pagination.total}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium">High Risk Found</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-red-600">
                {isLoading ? (
                  <Skeleton className="h-8 w-16" />
                ) : (
                  (analyses || []).filter(a => a.overall_risk_score >= RISK_THRESHOLDS.HIGH).length
                )}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium">Average Risk</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {isLoading ? (
                  <Skeleton className="h-8 w-16" />
                ) : (analyses || []).length > 0 ? (
                  ((analyses || []).reduce((sum, a) => sum + a.overall_risk_score, 0) / (analyses || []).length).toFixed(1)
                ) : (
                  '0.0'
                )}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Analysis Table */}
        <Card>
          <CardHeader>
            <CardTitle>Analysis Results</CardTitle>
            <CardDescription>
              {pagination.total > 0 ? (
                `Showing ${((pagination.page - 1) * pagination.size) + 1}-${Math.min(pagination.page * pagination.size, pagination.total)} of ${pagination.total} results`
              ) : (
                'No analyses found'
              )}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="rounded-md border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Date</TableHead>
                    <TableHead>Analysis ID</TableHead>
                    <TableHead>Risk Score</TableHead>
                    <TableHead>Risk Level</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Processing Time</TableHead>
                    <TableHead className="w-[100px]">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {isLoading ? (
                    [...Array(5)].map((_, i) => (
                      <TableRow key={i}>
                        <TableCell><Skeleton className="h-4 w-20" /></TableCell>
                        <TableCell><Skeleton className="h-4 w-24" /></TableCell>
                        <TableCell><Skeleton className="h-4 w-12" /></TableCell>
                        <TableCell><Skeleton className="h-6 w-16" /></TableCell>
                        <TableCell><Skeleton className="h-6 w-16" /></TableCell>
                        <TableCell><Skeleton className="h-4 w-12" /></TableCell>
                        <TableCell><Skeleton className="h-8 w-16" /></TableCell>
                      </TableRow>
                    ))
                  ) : (analyses || []).length > 0 ? (
                    (analyses || []).map((analysis) => (
                      <TableRow key={analysis.analysis_id}>
                        <TableCell className="font-medium">
                          {formatDate(analysis.created_at)}
                        </TableCell>
                        <TableCell className="font-mono text-sm">
                          #{analysis.analysis_id.slice(-8)}
                        </TableCell>
                        <TableCell>
                          <span className="font-medium">{analysis.overall_risk_score}</span>
                        </TableCell>
                        <TableCell>
                          <Badge variant={getRiskBadgeVariant(analysis.overall_risk_score)}>
                            {getRiskLevel(analysis.overall_risk_score)}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <Badge variant={getStatusBadgeVariant(analysis.status)}>
                            {analysis.status}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          {analysis.processing_time ? `${analysis.processing_time.toFixed(1)}s` : '-'}
                        </TableCell>
                        <TableCell>
                          <div className="flex space-x-2">
                            <Link href={`${ROUTES.ANALYSIS}/${analysis.analysis_id}`}>
                              <Button variant="ghost" size="sm">
                                <Eye className="h-4 w-4" />
                              </Button>
                            </Link>
                            <Button 
                              variant="ghost" 
                              size="sm"
                              onClick={() => handleDownloadPDF(analysis.analysis_id)}
                              disabled={isGenerating}
                            >
                              <Download className="h-4 w-4" />
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    ))
                  ) : (
                    <TableRow>
                      <TableCell colSpan={7} className="text-center py-8">
                        <div className="flex flex-col items-center space-y-4">
                          <FileText className="h-12 w-12 text-gray-400" />
                          <div>
                            <p className="text-lg font-medium text-gray-900">No analyses found</p>
                            <p className="text-gray-500">
                              {Object.keys(filters).length > 0 
                                ? 'Try adjusting your filters or start a new analysis'
                                : 'Start your first check analysis'
                              }
                            </p>
                          </div>
                          <Link href={ROUTES.UPLOAD}>
                            <Button>Start New Analysis</Button>
                          </Link>
                        </div>
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </div>

            {/* Pagination */}
            {pagination.pages > 1 && (
              <div className="flex items-center justify-between space-x-2 py-4">
                <div className="text-sm text-muted-foreground">
                  Page {pagination.page} of {pagination.pages}
                </div>
                <div className="flex space-x-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handlePageChange(pagination.page - 1)}
                    disabled={pagination.page <= 1}
                  >
                    <ChevronLeft className="h-4 w-4" />
                    Previous
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handlePageChange(pagination.page + 1)}
                    disabled={pagination.page >= pagination.pages}
                  >
                    Next
                    <ChevronRight className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}