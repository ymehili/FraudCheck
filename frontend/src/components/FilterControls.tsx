"use client";

import { useState, useEffect } from 'react';
import { DashboardFilter } from '@/types';

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
    <div className={`bg-white rounded-lg shadow-sm border ${className}`}>
      <div className="px-6 py-4 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold text-gray-900">Filter Analyses</h3>
          <div className="flex items-center space-x-2">
            {hasActiveFilters() && (
              <button
                onClick={onReset}
                className="text-sm text-gray-500 hover:text-gray-700 transition-colors"
              >
                Reset All
              </button>
            )}
            <button
              onClick={() => setIsExpanded(!isExpanded)}
              className="text-sm text-blue-600 hover:text-blue-700 transition-colors"
            >
              {isExpanded ? 'Hide Filters' : 'Show Filters'}
            </button>
          </div>
        </div>
      </div>

      {isExpanded && (
        <div className="p-6 space-y-6">
          {/* Time Range Filter */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Time Range
            </label>
            <select
              value={localFilters.timeRange || ''}
              onChange={(e) => handleFilterChange('timeRange', e.target.value as 'last_7_days' | 'last_30_days' | 'last_90_days' | 'last_year' | 'custom' || undefined)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
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
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Start Date
                </label>
                <input
                  type="date"
                  value={localFilters.customDateRange?.start ? formatDate(localFilters.customDateRange.start) : ''}
                  onChange={(e) => handleDateRangeChange('start', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  End Date
                </label>
                <input
                  type="date"
                  value={localFilters.customDateRange?.end ? formatDate(localFilters.customDateRange.end) : ''}
                  onChange={(e) => handleDateRangeChange('end', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
              </div>
            </div>
          )}

          {/* Risk Score Range */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Risk Score Range
            </label>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs text-gray-500 mb-1">Minimum</label>
                <input
                  type="number"
                  min="0"
                  max="100"
                  placeholder="0"
                  value={localFilters.riskScoreRange?.min || ''}
                  onChange={(e) => handleRiskScoreChange('min', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-500 mb-1">Maximum</label>
                <input
                  type="number"
                  min="0"
                  max="100"
                  placeholder="100"
                  value={localFilters.riskScoreRange?.max || ''}
                  onChange={(e) => handleRiskScoreChange('max', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
              </div>
            </div>
          </div>

          {/* Risk Levels */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Risk Levels
            </label>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
              {RISK_LEVELS.map(level => (
                <button
                  key={level.value}
                  onClick={() => handleRiskLevelToggle(level.value)}
                  className={`px-3 py-2 text-sm font-medium rounded-md transition-colors ${
                    localFilters.riskLevels?.includes(level.value)
                      ? level.color
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
                >
                  {level.label}
                </button>
              ))}
            </div>
          </div>

          {/* File Types */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              File Types
            </label>
            <div className="space-y-2">
              {FILE_TYPES.map(type => (
                <label key={type.value} className="flex items-center">
                  <input
                    type="checkbox"
                    checked={localFilters.fileTypes?.includes(type.value) || false}
                    onChange={() => handleFileTypeToggle(type.value)}
                    className="h-4 w-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                  />
                  <span className="ml-2 text-sm text-gray-700">{type.label}</span>
                </label>
              ))}
            </div>
          </div>

          {/* Violations Filter */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Violations
            </label>
            <div className="space-y-2">
              <label className="flex items-center">
                <input
                  type="radio"
                  name="violations"
                  checked={localFilters.hasViolations === undefined}
                  onChange={() => handleFilterChange('hasViolations', undefined)}
                  className="h-4 w-4 text-blue-600 border-gray-300 focus:ring-blue-500"
                />
                <span className="ml-2 text-sm text-gray-700">All</span>
              </label>
              <label className="flex items-center">
                <input
                  type="radio"
                  name="violations"
                  checked={localFilters.hasViolations === true}
                  onChange={() => handleFilterChange('hasViolations', true)}
                  className="h-4 w-4 text-blue-600 border-gray-300 focus:ring-blue-500"
                />
                <span className="ml-2 text-sm text-gray-700">Has Violations</span>
              </label>
              <label className="flex items-center">
                <input
                  type="radio"
                  name="violations"
                  checked={localFilters.hasViolations === false}
                  onChange={() => handleFilterChange('hasViolations', false)}
                  className="h-4 w-4 text-blue-600 border-gray-300 focus:ring-blue-500"
                />
                <span className="ml-2 text-sm text-gray-700">No Violations</span>
              </label>
            </div>
          </div>

          {/* Confidence Threshold */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Minimum Confidence Level
            </label>
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
              <span className="text-sm text-gray-600 w-12">
                {localFilters.minConfidence ? Math.round(localFilters.minConfidence * 100) : 0}%
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Active Filters Summary */}
      {hasActiveFilters() && (
        <div className="px-6 py-4 bg-gray-50 border-t border-gray-200">
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-700">
              {Object.keys(localFilters).filter(key => localFilters[key as keyof DashboardFilter] !== undefined).length} filter(s) active
            </span>
            <button
              onClick={onReset}
              className="text-sm text-blue-600 hover:text-blue-700 transition-colors"
            >
              Clear All
            </button>
          </div>
        </div>
      )}
    </div>
  );
}