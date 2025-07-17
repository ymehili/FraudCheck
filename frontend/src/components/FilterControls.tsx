"use client";

import { useState, useEffect } from 'react';
import { DashboardFilter } from '@/types';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import Button from '@/components/ui/Button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

interface FilterControlsProps {
  filters: DashboardFilter;
  onFiltersChange: (filters: DashboardFilter) => void;
  onReset: () => void;
  className?: string;
}

const TIME_RANGE_OPTIONS = [
  { value: '', label: 'All Time' },
  { value: 'last_7_days', label: 'Last 7 Days' },
  { value: 'last_30_days', label: 'Last 30 Days' },
  { value: 'last_90_days', label: 'Last 90 Days' },
  { value: 'last_year', label: 'Last Year' },
  { value: 'custom', label: 'Custom Range' }
];

const RISK_LEVELS: { value: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'; label: string; color: string; }[] = [
  { value: 'LOW', label: 'Low Risk', color: 'bg-green-100 text-green-800' },
  { value: 'MEDIUM', label: 'Medium Risk', color: 'bg-yellow-100 text-yellow-800' },
  { value: 'HIGH', label: 'High Risk', color: 'bg-red-100 text-red-800' },
  { value: 'CRITICAL', label: 'Critical Risk', color: 'bg-red-200 text-red-900' }
];

const FILE_TYPES = [
  { value: 'image/jpeg', label: 'JPEG Images' },
  { value: 'image/png', label: 'PNG Images' },
  { value: 'application/pdf', label: 'PDF Documents' }
];

export default function FilterControls({
  filters,
  onFiltersChange,
  onReset,
  className = ''
}: FilterControlsProps) {
  const [localFilters, setLocalFilters] = useState<DashboardFilter>(filters);
  const [isExpanded, setIsExpanded] = useState(false);

  // Update local filters when props change
  useEffect(() => {
    setLocalFilters(filters);
  }, [filters]);

  const handleFilterChange = (key: keyof DashboardFilter, value: DashboardFilter[keyof DashboardFilter]) => {
    const newFilters = { ...localFilters, [key]: value };
    setLocalFilters(newFilters);
    onFiltersChange(newFilters);
  };

  const handleRiskScoreChange = (type: 'min' | 'max', value: string) => {
    const numValue = parseInt(value);
    const newRange = {
      ...localFilters.riskScoreRange,
      [type]: isNaN(numValue) ? undefined : numValue
    };
    
    // Remove the range if both values are undefined
    if (newRange.min === undefined && newRange.max === undefined) {
      handleFilterChange('riskScoreRange', undefined);
    } else if (newRange.min !== undefined && newRange.max !== undefined) {
      handleFilterChange('riskScoreRange', { min: newRange.min, max: newRange.max });
    } else {
      handleFilterChange('riskScoreRange', undefined);
    }
  };

  const handleDateRangeChange = (type: 'start' | 'end', value: string) => {
    const newRange = {
      ...localFilters.customDateRange,
      [type]: value
    };
    
    // Remove the range if both values are empty
    if (!newRange.start && !newRange.end) {
      handleFilterChange('customDateRange', undefined);
    } else if (newRange.start && newRange.end) {
      handleFilterChange('customDateRange', { start: newRange.start, end: newRange.end });
    } else {
      handleFilterChange('customDateRange', undefined);
    }
  };

  const handleRiskLevelToggle = (level: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL') => {
    const currentLevels = localFilters.riskLevels || [];
    const newLevels = currentLevels.includes(level)
      ? currentLevels.filter(l => l !== level)
      : [...currentLevels, level];
    
    handleFilterChange('riskLevels', newLevels.length === 0 ? undefined : newLevels);
  };

  const handleFileTypeToggle = (fileType: string) => {
    const currentTypes = localFilters.fileTypes || [];
    const newTypes = currentTypes.includes(fileType)
      ? currentTypes.filter(t => t !== fileType)
      : [...currentTypes, fileType];
    
    handleFilterChange('fileTypes', newTypes.length === 0 ? undefined : newTypes);
  };

  const hasActiveFilters = () => {
    return localFilters.timeRange ||
           localFilters.customDateRange ||
           localFilters.riskScoreRange ||
           localFilters.riskLevels?.length ||
           localFilters.fileTypes?.length ||
           localFilters.hasViolations !== undefined ||
           localFilters.minConfidence !== undefined;
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toISOString().split('T')[0];
  };

  return (
    <Card className={className}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle>Filter Analyses</CardTitle>
          <div className="flex items-center space-x-2">
            {hasActiveFilters() && (
              <Button
                onClick={onReset}
                variant="ghost"
                size="sm"
              >
                Reset All
              </Button>
            )}
            <Button
              onClick={() => setIsExpanded(!isExpanded)}
              variant="ghost"
              size="sm"
            >
              {isExpanded ? 'Hide Filters' : 'Show Filters'}
            </Button>
          </div>
        </div>
      </CardHeader>

      {isExpanded && (
        <CardContent className="space-y-6">
          {/* Time Range Filter */}
          <div>
            <Label htmlFor="time-range" className="text-sm font-medium">
              Time Range
            </Label>
            <select
              id="time-range"
              value={localFilters.timeRange || ''}
              onChange={(e) => handleFilterChange('timeRange', e.target.value as 'last_7_days' | 'last_30_days' | 'last_90_days' | 'last_year' | 'custom' || undefined)}
              className="w-full px-3 py-2 border border-input rounded-md focus:outline-none focus:ring-2 focus:ring-ring focus:border-ring"
            >
              {TIME_RANGE_OPTIONS.map(option => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>

          {/* Custom Date Range */}
          {localFilters.timeRange === 'custom' && (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <Label htmlFor="start-date" className="text-sm font-medium">
                  Start Date
                </Label>
                <Input
                  id="start-date"
                  type="date"
                  value={localFilters.customDateRange?.start ? formatDate(localFilters.customDateRange.start) : ''}
                  onChange={(e) => handleDateRangeChange('start', e.target.value)}
                />
              </div>
              <div>
                <Label htmlFor="end-date" className="text-sm font-medium">
                  End Date
                </Label>
                <Input
                  id="end-date"
                  type="date"
                  value={localFilters.customDateRange?.end ? formatDate(localFilters.customDateRange.end) : ''}
                  onChange={(e) => handleDateRangeChange('end', e.target.value)}
                />
              </div>
            </div>
          )}

          {/* Risk Score Range */}
          <div>
            <Label className="text-sm font-medium">
              Risk Score Range
            </Label>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <Label htmlFor="min-score" className="text-xs text-muted-foreground">Minimum</Label>
                <Input
                  id="min-score"
                  type="number"
                  min="0"
                  max="100"
                  placeholder="0"
                  value={localFilters.riskScoreRange?.min || ''}
                  onChange={(e) => handleRiskScoreChange('min', e.target.value)}
                />
              </div>
              <div>
                <Label htmlFor="max-score" className="text-xs text-muted-foreground">Maximum</Label>
                <Input
                  id="max-score"
                  type="number"
                  min="0"
                  max="100"
                  placeholder="100"
                  value={localFilters.riskScoreRange?.max || ''}
                  onChange={(e) => handleRiskScoreChange('max', e.target.value)}
                />
              </div>
            </div>
          </div>

          {/* Risk Levels */}
          <div>
            <Label className="text-sm font-medium">
              Risk Levels
            </Label>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
              {RISK_LEVELS.map(level => (
                <Button
                  key={level.value}
                  onClick={() => handleRiskLevelToggle(level.value)}
                  variant={localFilters.riskLevels?.includes(level.value) ? "primary" : "outline"}
                  size="sm"
                  className={
                    localFilters.riskLevels?.includes(level.value)
                      ? level.color
                      : ''
                  }
                >
                  {level.label}
                </Button>
              ))}
            </div>
          </div>

          {/* File Types */}
          <div>
            <Label className="text-sm font-medium">
              File Types
            </Label>
            <div className="space-y-2">
              {FILE_TYPES.map(type => (
                <Label key={type.value} className="flex items-center">
                  <input
                    type="checkbox"
                    checked={localFilters.fileTypes?.includes(type.value) || false}
                    onChange={() => handleFileTypeToggle(type.value)}
                    className="h-4 w-4 text-primary border-input rounded focus:ring-ring"
                  />
                  <span className="ml-2 text-sm text-foreground">{type.label}</span>
                </Label>
              ))}
            </div>
          </div>

          {/* Violations Filter */}
          <div>
            <Label className="text-sm font-medium">
              Violations
            </Label>
            <div className="space-y-2">
              <Label className="flex items-center">
                <input
                  type="radio"
                  name="violations"
                  checked={localFilters.hasViolations === undefined}
                  onChange={() => handleFilterChange('hasViolations', undefined)}
                  className="h-4 w-4 text-primary border-input focus:ring-ring"
                />
                <span className="ml-2 text-sm text-foreground">All</span>
              </Label>
              <Label className="flex items-center">
                <input
                  type="radio"
                  name="violations"
                  checked={localFilters.hasViolations === true}
                  onChange={() => handleFilterChange('hasViolations', true)}
                  className="h-4 w-4 text-primary border-input focus:ring-ring"
                />
                <span className="ml-2 text-sm text-foreground">Has Violations</span>
              </Label>
              <Label className="flex items-center">
                <input
                  type="radio"
                  name="violations"
                  checked={localFilters.hasViolations === false}
                  onChange={() => handleFilterChange('hasViolations', false)}
                  className="h-4 w-4 text-primary border-input focus:ring-ring"
                />
                <span className="ml-2 text-sm text-foreground">No Violations</span>
              </Label>
            </div>
          </div>

          {/* Confidence Threshold */}
          <div>
            <Label className="text-sm font-medium">
              Minimum Confidence Level
            </Label>
            <div className="flex items-center space-x-4">
              <input
                type="range"
                min="0"
                max="100"
                step="5"
                value={localFilters.minConfidence ? localFilters.minConfidence * 100 : 0}
                onChange={(e) => {
                  const value = parseInt(e.target.value);
                  handleFilterChange('minConfidence', value === 0 ? undefined : value / 100);
                }}
                className="flex-1"
              />
              <span className="text-sm text-muted-foreground w-12">
                {localFilters.minConfidence ? Math.round(localFilters.minConfidence * 100) : 0}%
              </span>
            </div>
          </div>
        </CardContent>
      )}

      {/* Active Filters Summary */}
      {hasActiveFilters() && (
        <CardContent className="bg-muted/50 border-t">
          <div className="flex items-center justify-between">
            <span className="text-sm text-foreground">
              {Object.keys(localFilters).filter(key => localFilters[key as keyof DashboardFilter] !== undefined).length} filter(s) active
            </span>
            <Button
              onClick={onReset}
              variant="ghost"
              size="sm"
            >
              Clear All
            </Button>
          </div>
        </CardContent>
      )}
    </Card>
  );
}