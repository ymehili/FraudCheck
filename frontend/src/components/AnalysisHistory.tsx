"use client";

import { useState } from 'react';
import { ChevronDownIcon, ChevronUpIcon, EyeIcon, DocumentArrowDownIcon } from '@heroicons/react/24/outline';
import { EnhancedAnalysisResult, PaginationParams } from '@/types';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import Button from '@/components/ui/Button';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';

interface AnalysisHistoryProps {
  analyses: EnhancedAnalysisResult[];
  pagination: PaginationParams;
  onPageChange: (page: number) => void;
  onSortChange: (field: string, direction: 'asc' | 'desc') => void;
  onViewDetails: (analysisId: string) => void;
  onExportPDF: (analysisId: string) => void;
  isLoading?: boolean;
  className?: string;
}

const SORT_FIELDS = {
  filename: 'Filename',
  analysis_timestamp: 'Analysis Date',
  overall_risk_score: 'Risk Score',
  risk_level: 'Risk Level',
  file_size: 'File Size'
};

export default function AnalysisHistory({
  analyses,
  pagination,
  onPageChange,
  onSortChange,
  onViewDetails,
  onExportPDF,
  isLoading = false,
  className = ''
}: AnalysisHistoryProps) {
  const [currentSort, setCurrentSort] = useState({
    field: 'analysis_timestamp',
    direction: 'desc' as 'asc' | 'desc'
  });

  const handleSort = (field: string) => {
    const newDirection = currentSort.field === field && currentSort.direction === 'asc' ? 'desc' : 'asc';
    setCurrentSort({ field, direction: newDirection });
    onSortChange(field, newDirection);
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const formatFileSize = (bytes: number) => {
    const sizes = ['B', 'KB', 'MB', 'GB'];
    if (bytes === 0) return '0 B';
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return `${(bytes / Math.pow(1024, i)).toFixed(1)} ${sizes[i]}`;
  };

  const SortIcon = ({ field }: { field: string }) => {
    if (currentSort.field !== field) {
      return <ChevronDownIcon className="w-4 h-4 text-gray-400" />;
    }
    return currentSort.direction === 'asc' ? 
      <ChevronUpIcon className="w-4 h-4 text-gray-600" /> : 
      <ChevronDownIcon className="w-4 h-4 text-gray-600" />;
  };

  const generatePageNumbers = () => {
    const pages = [];
    const totalPages = Math.ceil(pagination.page);
    const currentPage = pagination.page;
    
    // Always show first page
    pages.push(1);
    
    // Show pages around current page
    for (let i = Math.max(2, currentPage - 2); i <= Math.min(totalPages - 1, currentPage + 2); i++) {
      pages.push(i);
    }
    
    // Always show last page if it's not already included
    if (totalPages > 1 && !pages.includes(totalPages)) {
      pages.push(totalPages);
    }
    
    return pages;
  };

  if (isLoading) {
    return (
      <Card className={className}>
        <CardContent className="text-center space-y-4">
          <Skeleton className="h-8 w-8 rounded-full mx-auto" />
          <Skeleton className="h-4 w-48 mx-auto" />
        </CardContent>
      </Card>
    );
  }

  if (analyses.length === 0) {
    return (
      <Card className={className}>
        <CardContent className="text-center">
          <div className="text-muted-foreground mb-4">
            <svg className="w-12 h-12 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          </div>
          <h3 className="text-lg font-medium text-foreground mb-2">No analyses found</h3>
          <p className="text-muted-foreground">Start by uploading a check image for analysis.</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle>Analysis History</CardTitle>
        <p className="text-sm text-muted-foreground">
          Showing {analyses.length} of {pagination.page * pagination.perPage} analyses
        </p>
      </CardHeader>

      <div className="overflow-x-auto">
        <table className="w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              {Object.entries(SORT_FIELDS).map(([field, label]) => (
                <th
                  key={field}
                  className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                  onClick={() => handleSort(field)}
                >
                  <div className="flex items-center space-x-1">
                    <span>{label}</span>
                    <SortIcon field={field} />
                  </div>
                </th>
              ))}
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Violations
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {analyses.map((analysis) => (
              <tr key={analysis.id} className="hover:bg-gray-50">
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="flex items-center">
                    <div className="flex-shrink-0 h-10 w-10">
                      <div className="h-10 w-10 rounded-lg bg-gray-100 flex items-center justify-center">
                        <svg className="h-6 w-6 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                        </svg>
                      </div>
                    </div>
                    <div className="ml-4">
                      <div className="text-sm font-medium text-gray-900 truncate max-w-xs">
                        {analysis.filename}
                      </div>
                      <div className="text-sm text-gray-500">
                        {formatFileSize(analysis.fileSize)}
                      </div>
                    </div>
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="text-sm text-gray-900">
                    {formatDate(analysis.analysisTimestamp)}
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="flex items-center">
                    <div className="text-sm font-medium text-gray-900 mr-2">
                      {analysis.overallRiskScore}%
                    </div>
                    <div className="w-16 bg-gray-200 rounded-full h-2">
                      <div 
                        className={`h-2 rounded-full ${
                          analysis.overallRiskScore >= 80 ? 'bg-red-600' :
                          analysis.overallRiskScore >= 60 ? 'bg-red-500' :
                          analysis.overallRiskScore >= 30 ? 'bg-yellow-500' :
                          'bg-green-500'
                        }`}
                        style={{ width: `${analysis.overallRiskScore}%` }}
                      ></div>
                    </div>
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <Badge variant={
                    analysis.riskScore.recommendation === 'LOW' ? 'default' :
                    analysis.riskScore.recommendation === 'MEDIUM' ? 'secondary' :
                    'destructive'
                  }>
                    {analysis.riskScore.recommendation}
                  </Badge>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  {formatFileSize(analysis.fileSize)}
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="text-sm">
                    {analysis.violations.length > 0 ? (
                      <div className="space-y-1">
                        {analysis.violations.slice(0, 2).map((violation, index) => (
                          <div key={index} className="flex items-center text-xs text-red-600">
                            <div className="w-1 h-1 bg-red-600 rounded-full mr-2"></div>
                            <span className="truncate max-w-xs">{violation}</span>
                          </div>
                        ))}
                        {analysis.violations.length > 2 && (
                          <div className="text-xs text-gray-500">
                            +{analysis.violations.length - 2} more
                          </div>
                        )}
                      </div>
                    ) : (
                      <span className="text-gray-500">None</span>
                    )}
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                  <div className="flex items-center space-x-2">
                    <button
                      onClick={() => onViewDetails(analysis.id)}
                      className="text-blue-600 hover:text-blue-900 transition-colors"
                      title="View details"
                    >
                      <EyeIcon className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => onExportPDF(analysis.id)}
                      className="text-green-600 hover:text-green-900 transition-colors"
                      title="Export PDF"
                    >
                      <DocumentArrowDownIcon className="w-4 h-4" />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      <div className="px-6 py-4 border-t border-gray-200">
        <div className="flex items-center justify-between">
          <div className="flex-1 flex justify-between sm:hidden">
            <Button
              onClick={() => onPageChange(pagination.page - 1)}
              disabled={pagination.page <= 1}
              variant="outline"
              size="sm"
            >
              Previous
            </Button>
            <Button
              onClick={() => onPageChange(pagination.page + 1)}
              disabled={pagination.page >= Math.ceil(pagination.page)}
              variant="outline"
              size="sm"
            >
              Next
            </Button>
          </div>
          
          <div className="hidden sm:flex-1 sm:flex sm:items-center sm:justify-between">
            <div>
              <p className="text-sm text-gray-700">
                Showing <span className="font-medium">{(pagination.page - 1) * pagination.perPage + 1}</span> to{' '}
                <span className="font-medium">
                  {Math.min(pagination.page * pagination.perPage, pagination.page * pagination.perPage)}
                </span>{' '}
                of <span className="font-medium">{pagination.page * pagination.perPage}</span> results
              </p>
            </div>
            <div>
              <nav className="relative z-0 inline-flex rounded-md shadow-sm -space-x-px">
                <Button
                  onClick={() => onPageChange(pagination.page - 1)}
                  disabled={pagination.page <= 1}
                  variant="outline"
                  size="sm"
                  className="rounded-l-md rounded-r-none"
                >
                  <ChevronUpIcon className="h-5 w-5 rotate-90" />
                </Button>
                
                {generatePageNumbers().map((pageNum, index) => (
                  <Button
                    key={index}
                    onClick={() => onPageChange(pageNum)}
                    variant={pageNum === pagination.page ? "primary" : "outline"}
                    size="sm"
                    className="rounded-none"
                  >
                    {pageNum}
                  </Button>
                ))}
                
                <Button
                  onClick={() => onPageChange(pagination.page + 1)}
                  disabled={pagination.page >= Math.ceil(pagination.page)}
                  variant="outline"
                  size="sm"
                  className="rounded-r-md rounded-l-none"
                >
                  <ChevronDownIcon className="h-5 w-5 -rotate-90" />
                </Button>
              </nav>
            </div>
          </div>
        </div>
      </div>
    </Card>
  );
}