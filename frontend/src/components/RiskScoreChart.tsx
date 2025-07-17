"use client";

import { useEffect, useRef, useState } from 'react';
import {
  Chart as ChartJS,
  ArcElement,
  Tooltip,
  Legend,
  ChartOptions,
  ChartData,
  Plugin,
  TooltipItem
} from 'chart.js';
import { RiskScore } from '@/types';

// Register Chart.js components
ChartJS.register(ArcElement, Tooltip, Legend);

interface RiskScoreChartProps {
  riskScore: RiskScore;
  size?: 'small' | 'medium' | 'large';
  showLegend?: boolean;
  showTooltip?: boolean;
  className?: string;
}

const RISK_COLORS = {
  LOW: '#10B981',      // Green
  MEDIUM: '#F59E0B',   // Yellow
  HIGH: '#EF4444',     // Red
  CRITICAL: '#DC2626'  // Dark Red
};

const CATEGORY_COLORS = {
  forensics: '#EF4444',  // Red
  ocr: '#F59E0B',       // Yellow
  rules: '#3B82F6'      // Blue
};

const SIZE_CONFIG = {
  small: { width: 200, height: 200 },
  medium: { width: 300, height: 300 },
  large: { width: 400, height: 400 }
};

export default function RiskScoreChart({ 
  riskScore, 
  size = 'medium', 
  showLegend = true, 
  showTooltip = true,
  className = ''
}: RiskScoreChartProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const chartRef = useRef<ChartJS<'doughnut'> | null>(null);
  const [isClient, setIsClient] = useState(false);

  // Ensure we only render on client side
  useEffect(() => {
    setIsClient(true);
  }, []);

  useEffect(() => {
    if (!isClient || !canvasRef.current) return;

    const ctx = canvasRef.current.getContext('2d');
    if (!ctx) return;

    // Destroy existing chart
    if (chartRef.current) {
      chartRef.current.destroy();
    }

    // Calculate overall risk level color
    const getRiskColor = (score: number): string => {
      if (score >= 80) return RISK_COLORS.CRITICAL;
      if (score >= 60) return RISK_COLORS.HIGH;
      if (score >= 30) return RISK_COLORS.MEDIUM;
      return RISK_COLORS.LOW;
    };

    // Create center text plugin
    const centerTextPlugin: Plugin<'doughnut'> = {
      id: 'centerText',
      beforeDraw: (chart: ChartJS<'doughnut'>) => {
        const { ctx, chartArea } = chart;
        if (!chartArea) return;

        const centerX = (chartArea.left + chartArea.right) / 2;
        const centerY = (chartArea.top + chartArea.bottom) / 2;

        ctx.save();
        
        // Draw overall risk score
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.font = 'bold 36px system-ui';
        ctx.fillStyle = getRiskColor(riskScore.overallScore);
        ctx.fillText(riskScore.overallScore.toString(), centerX, centerY - 10);
        
        // Draw risk level
        ctx.font = '14px system-ui';
        ctx.fillStyle = '#6B7280';
        ctx.fillText(riskScore.recommendation, centerX, centerY + 20);
        
        ctx.restore();
      }
    };

    // Prepare chart data
    const chartData: ChartData<'doughnut'> = {
      labels: ['Forensics', 'OCR', 'Rules'],
      datasets: [{
        data: [
          riskScore.categoryScores.forensics,
          riskScore.categoryScores.ocr,
          riskScore.categoryScores.rules
        ],
        backgroundColor: [
          CATEGORY_COLORS.forensics,
          CATEGORY_COLORS.ocr,
          CATEGORY_COLORS.rules
        ],
        borderColor: [
          CATEGORY_COLORS.forensics,
          CATEGORY_COLORS.ocr,
          CATEGORY_COLORS.rules
        ],
        borderWidth: 2,
        hoverOffset: 4,
        // cutout: '60%' // Chart.js type compatibility - use borderRadius instead
      }]
    };

    // Chart configuration
    const config: ChartOptions<'doughnut'> = {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          display: showLegend,
          position: 'bottom',
          labels: {
            padding: 20,
            usePointStyle: true,
            font: {
              size: 12
            }
          }
        },
        tooltip: {
          enabled: showTooltip,
          backgroundColor: 'rgba(0, 0, 0, 0.8)',
          titleColor: '#fff',
          bodyColor: '#fff',
          borderColor: '#374151',
          borderWidth: 1,
          callbacks: {
            label: (context: TooltipItem<'doughnut'>) => {
              const label = context.label || '';
              const value = context.parsed || 0;
              return `${label}: ${value}%`;
            }
          }
        }
      },
      elements: {
        arc: {
          borderWidth: 2,
          borderColor: '#fff'
        }
      },
      animation: {
        animateRotate: true,
        animateScale: false,
        duration: 1000,
        easing: 'easeOutQuart'
      }
    };

    // Create chart
    chartRef.current = new ChartJS(ctx, {
      type: 'doughnut',
      data: chartData,
      options: config,
      plugins: [centerTextPlugin]
    });

    // Cleanup function
    return () => {
      if (chartRef.current) {
        chartRef.current.destroy();
        chartRef.current = null;
      }
    };
  }, [isClient, riskScore, showLegend, showTooltip]);

  if (!isClient) {
    return (
      <div className={`flex items-center justify-center bg-gray-100 rounded-lg ${className}`}>
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className={`bg-white rounded-lg shadow-sm border p-6 ${className}`}>
      <div className="mb-4">
        <h3 className="text-lg font-semibold text-gray-900 mb-2">Risk Score Breakdown</h3>
        <div className="flex items-center space-x-4 text-sm text-gray-600">
          <div className="flex items-center">
            <div className="w-3 h-3 bg-green-500 rounded-full mr-2"></div>
            <span>Low (0-29)</span>
          </div>
          <div className="flex items-center">
            <div className="w-3 h-3 bg-yellow-500 rounded-full mr-2"></div>
            <span>Medium (30-59)</span>
          </div>
          <div className="flex items-center">
            <div className="w-3 h-3 bg-red-500 rounded-full mr-2"></div>
            <span>High (60-79)</span>
          </div>
          <div className="flex items-center">
            <div className="w-3 h-3 bg-red-600 rounded-full mr-2"></div>
            <span>Critical (80+)</span>
          </div>
        </div>
      </div>

      <div 
        className="relative" 
        style={{ 
          width: SIZE_CONFIG[size].width, 
          height: SIZE_CONFIG[size].height 
        }}
      >
        <canvas
          ref={canvasRef}
          style={{ 
            width: '100%', 
            height: '100%' 
          }}
        />
      </div>

      {/* Risk factors section */}
      {riskScore.riskFactors.length > 0 && (
        <div className="mt-6">
          <h4 className="text-sm font-medium text-gray-900 mb-3">Risk Factors</h4>
          <div className="space-y-2">
            {riskScore.riskFactors.slice(0, 3).map((factor, index) => (
              <div key={index} className="flex items-start text-sm">
                <div className="w-2 h-2 bg-red-500 rounded-full mt-1.5 mr-2 flex-shrink-0"></div>
                <span className="text-gray-700">{factor}</span>
              </div>
            ))}
            {riskScore.riskFactors.length > 3 && (
              <div className="text-sm text-gray-500">
                +{riskScore.riskFactors.length - 3} more risk factors
              </div>
            )}
          </div>
        </div>
      )}

      {/* Confidence level */}
      <div className="mt-6 pt-4 border-t border-gray-200">
        <div className="flex items-center justify-between text-sm">
          <span className="text-gray-600">Confidence Level</span>
          <span className="font-medium text-gray-900">
            {Math.round(riskScore.confidenceLevel * 100)}%
          </span>
        </div>
        <div className="mt-2 w-full bg-gray-200 rounded-full h-2">
          <div 
            className="bg-blue-600 h-2 rounded-full transition-all duration-300"
            style={{ width: `${riskScore.confidenceLevel * 100}%` }}
          ></div>
        </div>
      </div>

      {/* Category scores breakdown */}
      <div className="mt-6 grid grid-cols-3 gap-4">
        <div className="text-center">
          <div className="text-sm text-gray-600">Forensics</div>
          <div className="text-lg font-semibold text-red-600">
            {riskScore.categoryScores.forensics}%
          </div>
        </div>
        <div className="text-center">
          <div className="text-sm text-gray-600">OCR</div>
          <div className="text-lg font-semibold text-yellow-600">
            {riskScore.categoryScores.ocr}%
          </div>
        </div>
        <div className="text-center">
          <div className="text-sm text-gray-600">Rules</div>
          <div className="text-lg font-semibold text-blue-600">
            {riskScore.categoryScores.rules}%
          </div>
        </div>
      </div>
    </div>
  );
}