'use client';

import { useState, useCallback, useEffect, useRef } from 'react';
import { Calendar, Filter, X, Search } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import { RISK_THRESHOLDS } from '@/lib/constants';

export interface FilterState {
  dateRange: {
    start: string;
    end: string;
  };
  riskScore: {
    min: number;
    max: number;
  };
  status: string;
  search: string;
}

interface FilterControlsProps {
  filters?: any;
  onFiltersChange: (filters: any) => void;
  className?: string;
  showSearch?: boolean;
  showStatusFilter?: boolean;
  showStatus?: boolean;
  showRiskRange?: boolean;
  showDateRange?: boolean;
  initialFilters?: any;
  isLoading?: boolean;
}

const defaultFilters: FilterState = {
  dateRange: {
    start: '',
    end: '',
  },
  riskScore: {
    min: 0,
    max: 100,
  },
  status: 'all',
  search: '',
};

export function FilterControls({
  filters: externalFilters,
  onFiltersChange,
  className,
  showSearch = true,
  showStatus = true,
  showStatusFilter = false,
  showRiskRange = true,
  showDateRange = true,
  initialFilters = {},
  isLoading = false,
}: FilterControlsProps) {
  const [filters, setFilters] = useState<any>({
    ...defaultFilters,
    ...initialFilters,
    ...externalFilters,
  });
  const [isExpanded, setIsExpanded] = useState(false);
  const isInitialMount = useRef(true);

  // Debounced filter changes
  useEffect(() => {
    // Skip the initial mount to prevent triggering on component creation
    if (isInitialMount.current) {
      isInitialMount.current = false;
      return;
    }
    
    const timeoutId = setTimeout(() => {
      onFiltersChange(filters);
    }, 300);

    return () => clearTimeout(timeoutId);
  }, [filters]);

  const updateFilter = useCallback((key: string, value: any) => {
    setFilters((prev: any) => ({ ...prev, [key]: value }));
  }, []);

  const resetFilters = useCallback(() => {
    setFilters(defaultFilters);
  }, []);

  const hasActiveFilters = useCallback(() => {
    return (
      filters.dateRange.start !== '' ||
      filters.dateRange.end !== '' ||
      filters.riskScore.min !== 0 ||
      filters.riskScore.max !== 100 ||
      filters.status !== 'all' ||
      filters.search !== ''
    );
  }, [filters]);

  const getActiveFilterCount = useCallback(() => {
    let count = 0;
    if (filters.dateRange.start || filters.dateRange.end) count++;
    if (filters.riskScore.min !== 0 || filters.riskScore.max !== 100) count++;
    if (filters.status && filters.status !== 'all') count++;
    if (filters.search) count++;
    return count;
  }, [filters]);

  const formatDateForInput = (date: Date): string => {
    return date.toISOString().split('T')[0];
  };

  const getPresetDateRanges = () => {
    const today = new Date();
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);
    
    const lastWeek = new Date(today);
    lastWeek.setDate(lastWeek.getDate() - 7);
    
    const lastMonth = new Date(today);
    lastMonth.setMonth(lastMonth.getMonth() - 1);
    
    const lastYear = new Date(today);
    lastYear.setFullYear(lastYear.getFullYear() - 1);

    return [
      { label: 'Today', start: formatDateForInput(today), end: formatDateForInput(today) },
      { label: 'Yesterday', start: formatDateForInput(yesterday), end: formatDateForInput(yesterday) },
      { label: 'Last 7 days', start: formatDateForInput(lastWeek), end: formatDateForInput(today) },
      { label: 'Last 30 days', start: formatDateForInput(lastMonth), end: formatDateForInput(today) },
      { label: 'Last year', start: formatDateForInput(lastYear), end: formatDateForInput(today) },
    ];
  };

  return (
    <Card className={cn('w-full', className)}>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center space-x-2">
            <Filter className="h-5 w-5" />
            <span>Filters</span>
            {hasActiveFilters() && (
              <Badge variant="secondary" className="ml-2">
                {getActiveFilterCount()} active
              </Badge>
            )}
          </CardTitle>
          <div className="flex items-center space-x-2">
            {hasActiveFilters() && (
              <Button variant="ghost" size="sm" onClick={resetFilters}>
                <X className="h-4 w-4 mr-1" />
                Clear
              </Button>
            )}
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setIsExpanded(!isExpanded)}
            >
              {isExpanded ? 'Collapse' : 'Expand'}
            </Button>
          </div>
        </div>
      </CardHeader>
      
      <CardContent className="space-y-4">
        {/* Search */}
        {showSearch && (
          <div className="space-y-2">
            <Label>Search</Label>
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
              <Input
                placeholder="Search by filename, analysis ID, or content..."
                value={filters.search}
                onChange={(e) => updateFilter('search', e.target.value)}
                className="pl-10"
              />
            </div>
          </div>
        )}

        {/* Date Range */}
        {showDateRange && (
          <div className="space-y-2">
            <Label>Date Range</Label>
            <div className="grid grid-cols-2 gap-2">
              <div>
                <Input
                  type="date"
                  placeholder="Start date"
                  value={filters.dateRange.start}
                  onChange={(e) => updateFilter('dateRange', {
                    ...filters.dateRange,
                    start: e.target.value
                  })}
                />
              </div>
              <div>
                <Input
                  type="date"
                  placeholder="End date"
                  value={filters.dateRange.end}
                  onChange={(e) => updateFilter('dateRange', {
                    ...filters.dateRange,
                    end: e.target.value
                  })}
                />
              </div>
            </div>
            
            {/* Date Presets */}
            {isExpanded && (
              <div className="flex flex-wrap gap-2 pt-2">
                {getPresetDateRanges().map((preset) => (
                  <Button
                    key={preset.label}
                    variant="outline"
                    size="sm"
                    onClick={() => updateFilter('dateRange', {
                      start: preset.start,
                      end: preset.end
                    })}
                  >
                    {preset.label}
                  </Button>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Risk Score Range */}
        {showRiskRange && (
          <div className="space-y-2">
            <Label>Risk Score Range</Label>
            <div className="grid grid-cols-2 gap-2">
              <div>
                <Input
                  type="number"
                  placeholder="Min score"
                  min="0"
                  max="100"
                  value={filters.riskScore.min}
                  onChange={(e) => updateFilter('riskScore', {
                    ...filters.riskScore,
                    min: parseInt(e.target.value) || 0
                  })}
                />
              </div>
              <div>
                <Input
                  type="number"
                  placeholder="Max score"
                  min="0"
                  max="100"
                  value={filters.riskScore.max}
                  onChange={(e) => updateFilter('riskScore', {
                    ...filters.riskScore,
                    max: parseInt(e.target.value) || 100
                  })}
                />
              </div>
            </div>
            
            {/* Risk Level Presets */}
            {isExpanded && (
              <div className="flex flex-wrap gap-2 pt-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => updateFilter('riskScore', { min: 0, max: RISK_THRESHOLDS.LOW - 1 })}
                >
                  Low Risk (0-24)
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => updateFilter('riskScore', { min: RISK_THRESHOLDS.LOW, max: RISK_THRESHOLDS.MEDIUM - 1 })}
                >
                  Medium Risk (25-49)
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => updateFilter('riskScore', { min: RISK_THRESHOLDS.MEDIUM, max: RISK_THRESHOLDS.HIGH - 1 })}
                >
                  High Risk (50-74)
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => updateFilter('riskScore', { min: RISK_THRESHOLDS.HIGH, max: 100 })}
                >
                  Critical Risk (75-100)
                </Button>
              </div>
            )}
          </div>
        )}

        {/* Status */}
        {showStatus && (
          <div className="space-y-2">
            <Label>Status</Label>
            <Select
              value={filters.status}
              onValueChange={(value) => updateFilter('status', value)}
            >
              <SelectTrigger>
                <SelectValue placeholder="All statuses" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All statuses</SelectItem>
                <SelectItem value="completed">Completed</SelectItem>
                <SelectItem value="processing">Processing</SelectItem>
                <SelectItem value="failed">Failed</SelectItem>
              </SelectContent>
            </Select>
          </div>
        )}

        {/* Active Filters Summary */}
        {hasActiveFilters() && (
          <div className="pt-2 border-t">
            <div className="text-sm text-gray-600 mb-2">Active filters:</div>
            <div className="flex flex-wrap gap-1">
              {filters.search && (
                <Badge variant="outline" className="text-xs">
                  Search: {filters.search}
                  <X 
                    className="h-3 w-3 ml-1 cursor-pointer" 
                    onClick={() => updateFilter('search', '')}
                  />
                </Badge>
              )}
              
              {(filters.dateRange.start || filters.dateRange.end) && (
                <Badge variant="outline" className="text-xs">
                  Date: {filters.dateRange.start || '...'} to {filters.dateRange.end || '...'}
                  <X 
                    className="h-3 w-3 ml-1 cursor-pointer" 
                    onClick={() => updateFilter('dateRange', { start: '', end: '' })}
                  />
                </Badge>
              )}
              
              {(filters.riskScore.min !== 0 || filters.riskScore.max !== 100) && (
                <Badge variant="outline" className="text-xs">
                  Risk: {filters.riskScore.min}-{filters.riskScore.max}
                  <X 
                    className="h-3 w-3 ml-1 cursor-pointer" 
                    onClick={() => updateFilter('riskScore', { min: 0, max: 100 })}
                  />
                </Badge>
              )}
              
              {filters.status && filters.status !== 'all' && (
                <Badge variant="outline" className="text-xs">
                  Status: {filters.status}
                  <X 
                    className="h-3 w-3 ml-1 cursor-pointer" 
                    onClick={() => updateFilter('status', 'all')}
                  />
                </Badge>
              )}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}