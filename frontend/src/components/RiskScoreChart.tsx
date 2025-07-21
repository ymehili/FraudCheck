'use client';

import { useMemo } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { cn, getRiskLevel, getRiskBadgeColor, formatNumber } from '@/lib/utils';
import { RiskDistribution } from '@/types/api';

interface RiskScoreChartProps {
  riskDistribution?: RiskDistribution;
  data?: RiskDistribution | Array<{name: string, value: number, color: string}>;
  averageRiskScore?: number;
  className?: string;
  title?: string;
  showDetails?: boolean;
  showLegend?: boolean;
}

export function RiskScoreChart({ 
  riskDistribution,
  data,
  averageRiskScore = 0,
  className,
  title = "Risk Score Distribution",
  showDetails = true,
  showLegend = false
}: RiskScoreChartProps) {
  const chartData = useMemo(() => {
    // Use data prop first, then riskDistribution
    const sourceData = data || riskDistribution;
    
    if (!sourceData) {
      return [];
    }
    
    // If it's already in the expected array format, return it
    if (Array.isArray(sourceData)) {
      return sourceData;
    }
    
    // Convert RiskDistribution to chart format
    const { low, medium, high, critical, total } = sourceData;
    
    return [
      {
        label: 'Low Risk',
        value: low,
        percentage: total > 0 ? (low / total) * 100 : 0,
        color: 'bg-green-500',
        lightColor: 'bg-green-100',
        textColor: 'text-green-700',
      },
      {
        label: 'Medium Risk',
        value: medium,
        percentage: total > 0 ? (medium / total) * 100 : 0,
        color: 'bg-yellow-500',
        lightColor: 'bg-yellow-100',
        textColor: 'text-yellow-700',
      },
      {
        label: 'High Risk',
        value: high,
        percentage: total > 0 ? (high / total) * 100 : 0,
        color: 'bg-orange-500',
        lightColor: 'bg-orange-100',
        textColor: 'text-orange-700',
      },
      {
        label: 'Critical Risk',
        value: critical,
        percentage: total > 0 ? (critical / total) * 100 : 0,
        color: 'bg-red-500',
        lightColor: 'bg-red-100',
        textColor: 'text-red-700',
      },
    ];
  }, [data, riskDistribution]);

  const averageRiskLevel = getRiskLevel(averageRiskScore);
  const sourceData = data || riskDistribution;
  const total = Array.isArray(sourceData) ? sourceData.reduce((sum, item) => sum + item.value, 0) : sourceData?.total || 0;

  return (
    <Card className={cn('w-full', className)}>
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          {title}
          {averageRiskScore > 0 && (
            <Badge className={getRiskBadgeColor(averageRiskScore)}>
              Avg: {Math.round(averageRiskScore)}
            </Badge>
          )}
        </CardTitle>
        <CardDescription>
          Distribution of risk scores across {formatNumber(total)} analyses
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Bar Chart */}
        <div className="space-y-3">
          {chartData.map((item, index) => {
            const label = 'label' in item ? item.label : item.name;
            const value = item.value;
            const percentage = 'percentage' in item ? item.percentage : 
              total > 0 ? (value / total) * 100 : 0;
            
            return (
              <div key={index} className="space-y-1">
                <div className="flex justify-between items-center text-sm">
                  <span className="font-medium">{label}</span>
                  <span className="text-gray-600">
                    {value} ({Math.round(percentage)}%)
                  </span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-3 overflow-hidden">
                  <div
                    className={cn('h-full transition-all duration-500 ease-out', 
                      'color' in item ? item.color : 'bg-blue-500')}
                    style={{ width: `${percentage}%` }}
                  />
                </div>
              </div>
            );
          })}
        </div>

        {/* Summary Stats */}
        {showDetails && (
          <div className="grid grid-cols-2 gap-4 pt-4 border-t">
            <div className="text-center">
              <div className="text-2xl font-bold text-gray-900">
                {formatNumber(total)}
              </div>
              <div className="text-sm text-gray-600">Total Analyses</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-gray-900">
                {Math.round(averageRiskScore)}
              </div>
              <div className="text-sm text-gray-600">Average Score</div>
            </div>
          </div>
        )}

        {/* Risk Level Indicator */}
        <div className={cn(
          'p-3 rounded-lg border text-center',
          averageRiskLevel === 'low' && 'bg-green-50 border-green-200',
          averageRiskLevel === 'medium' && 'bg-yellow-50 border-yellow-200',
          averageRiskLevel === 'high' && 'bg-orange-50 border-orange-200',
          averageRiskLevel === 'critical' && 'bg-red-50 border-red-200'
        )}>
          <div className={cn(
            'text-sm font-medium capitalize',
            averageRiskLevel === 'low' && 'text-green-800',
            averageRiskLevel === 'medium' && 'text-yellow-800',
            averageRiskLevel === 'high' && 'text-orange-800',
            averageRiskLevel === 'critical' && 'text-red-800'
          )}>
            Overall Risk Level: {averageRiskLevel}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

// Simplified version for smaller displays
export function RiskScoreDonut({ 
  riskDistribution, 
  averageRiskScore, 
  size = 120,
  className 
}: {
  riskDistribution: RiskDistribution;
  averageRiskScore: number;
  size?: number;
  className?: string;
}) {
  const { low, medium, high, critical, total } = riskDistribution;
  
  if (total === 0) {
    return (
      <div className={cn('flex items-center justify-center', className)} style={{ height: size, width: size }}>
        <div className="text-center text-gray-500">
          <div className="text-sm">No data</div>
        </div>
      </div>
    );
  }

  const radius = (size - 20) / 2;
  const strokeWidth = 20;
  const normalizedRadius = radius - strokeWidth * 2;
  const circumference = normalizedRadius * 2 * Math.PI;

  const lowPercentage = (low / total) * 100;
  const mediumPercentage = (medium / total) * 100;
  const highPercentage = (high / total) * 100;
  const criticalPercentage = (critical / total) * 100;

  const lowOffset = circumference - (lowPercentage / 100) * circumference;
  const mediumOffset = lowOffset - (mediumPercentage / 100) * circumference;
  const highOffset = mediumOffset - (highPercentage / 100) * circumference;

  return (
    <div className={cn('relative', className)} style={{ height: size, width: size }}>
      <svg height={size} width={size} className="transform -rotate-90">
        {/* Background circle */}
        <circle
          stroke="#e5e7eb"
          fill="transparent"
          strokeWidth={strokeWidth}
          r={normalizedRadius}
          cx={size / 2}
          cy={size / 2}
        />
        
        {/* Low risk segment */}
        {low > 0 && (
          <circle
            stroke="#10b981"
            fill="transparent"
            strokeWidth={strokeWidth}
            strokeDasharray={`${circumference} ${circumference}`}
            strokeDashoffset={lowOffset}
            strokeLinecap="round"
            r={normalizedRadius}
            cx={size / 2}
            cy={size / 2}
            className="transition-all duration-300"
          />
        )}
        
        {/* Medium risk segment */}
        {medium > 0 && (
          <circle
            stroke="#f59e0b"
            fill="transparent"
            strokeWidth={strokeWidth}
            strokeDasharray={`${(mediumPercentage / 100) * circumference} ${circumference}`}
            strokeDashoffset={mediumOffset}
            strokeLinecap="round"
            r={normalizedRadius}
            cx={size / 2}
            cy={size / 2}
            className="transition-all duration-300"
          />
        )}
        
        {/* High risk segment */}
        {high > 0 && (
          <circle
            stroke="#f97316"
            fill="transparent"
            strokeWidth={strokeWidth}
            strokeDasharray={`${(highPercentage / 100) * circumference} ${circumference}`}
            strokeDashoffset={highOffset}
            strokeLinecap="round"
            r={normalizedRadius}
            cx={size / 2}
            cy={size / 2}
            className="transition-all duration-300"
          />
        )}
        
        {/* Critical risk segment */}
        {critical > 0 && (
          <circle
            stroke="#ef4444"
            fill="transparent"
            strokeWidth={strokeWidth}
            strokeDasharray={`${(criticalPercentage / 100) * circumference} ${circumference}`}
            strokeDashoffset={highOffset - (criticalPercentage / 100) * circumference}
            strokeLinecap="round"
            r={normalizedRadius}
            cx={size / 2}
            cy={size / 2}
            className="transition-all duration-300"
          />
        )}
      </svg>
      
      {/* Center text */}
      <div className="absolute inset-0 flex items-center justify-center">
        <div className="text-center">
          <div className="text-lg font-bold">{Math.round(averageRiskScore)}</div>
          <div className="text-xs text-gray-600">Avg Risk</div>
        </div>
      </div>
    </div>
  );
}