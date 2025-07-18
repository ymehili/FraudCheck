"use client";

import { useState, useEffect } from 'react';
import { useAuth } from '@clerk/nextjs';
import { useRouter } from 'next/navigation';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import Button from '@/components/ui/Button';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';

interface ForensicsResult {
  edge_score: number;
  compression_score: number;
  font_score: number;
  overall_score: number;
  detected_anomalies: string[];
  edge_inconsistencies: Record<string, unknown>;
  compression_artifacts: Record<string, unknown>;
  font_analysis: Record<string, unknown>;
}

interface OCRResult {
  payee?: string;
  amount?: string;
  date?: string;
  account_number?: string;
  routing_number?: string;
  check_number?: string;
  memo?: string;
  signature_detected: boolean;
  extraction_confidence: number;
  field_confidences: Record<string, number>;
}

interface RuleEngineResult {
  risk_score: number;
  violations: string[];
  passed_rules: string[];
  rule_scores: Record<string, number>;
  confidence_factors: Record<string, number>;
  recommendations: string[];
}

interface AnalysisResult {
  analysis_id: string;
  file_id: string;
  timestamp: string;
  forensics: ForensicsResult;
  ocr: OCRResult;
  rules: RuleEngineResult;
  overall_risk_score: number;
  confidence: number;
}

function getRiskLevel(score: number): { label: string; variant: 'default' | 'secondary' | 'destructive' } {
  if (score < 30) return { label: 'Low Risk', variant: 'default' };
  if (score < 70) return { label: 'Medium Risk', variant: 'secondary' };
  return { label: 'High Risk', variant: 'destructive' };
}

export default function AnalysisResultPage() {
  const { getToken } = useAuth();
  const router = useRouter();
  const params = useParams();
  const analysisId = params.id as string;

  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchAnalysis = async () => {
      try {
        setIsLoading(true);
        setError(null);

        const token = await getToken();
        if (!token) {
          throw new Error('Authentication token not available');
        }

        // First try to get the analysis by ID
        const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/analyze/${analysisId}`, {
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        });

        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || 'Failed to fetch analysis');
        }

        const result = await response.json();
        setAnalysis(result);

      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch analysis');
      } finally {
        setIsLoading(false);
      }
    };

    if (analysisId) {
      fetchAnalysis();
    }
  }, [analysisId, getToken]);

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50">
        <header className="bg-white shadow-sm border-b">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between items-center h-16">
              <div className="flex items-center">
                <Link href="/" className="text-2xl font-bold text-gray-900">
                  CheckGuard AI
                </Link>
              </div>
              <div className="flex items-center space-x-4">
                <Link
                  href="/upload"
                  className="text-gray-600 hover:text-gray-900 px-3 py-2 rounded-md text-sm font-medium"
                >
                  ← Back to Upload
                </Link>
              </div>
            </div>
          </div>
        </header>

        <main className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <Alert variant="destructive">
            <AlertDescription>
              {error}
            </AlertDescription>
          </Alert>
        </main>
      </div>
    );
  }

  if (!analysis) {
    return (
      <div className="min-h-screen bg-gray-50">
        <main className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <Alert variant="destructive">
            <AlertDescription>
              Analysis not found
            </AlertDescription>
          </Alert>
        </main>
      </div>
    );
  }

  const riskLevel = getRiskLevel(analysis.overall_risk_score);

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center">
              <Link href="/" className="text-2xl font-bold text-gray-900">
                CheckGuard AI
              </Link>
            </div>
            <div className="flex items-center space-x-4">
              <Link
                href="/upload"
                className="text-gray-600 hover:text-gray-900 px-3 py-2 rounded-md text-sm font-medium"
              >
                New Analysis
              </Link>
              <Link
                href="/history"
                className="text-gray-600 hover:text-gray-900 px-3 py-2 rounded-md text-sm font-medium"
              >
                History
              </Link>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">Analysis Results</h1>
          <p className="text-gray-600">
            Analysis completed on {new Date(analysis.timestamp).toLocaleString()}
          </p>
        </div>

        {/* Overall Risk Score */}
        <Card className="mb-8">
          <CardHeader>
            <CardTitle className="flex items-center justify-between">
              <span>Overall Risk Assessment</span>
              <Badge variant={riskLevel.variant} className="text-lg px-4 py-2">
                {riskLevel.label}
              </Badge>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between mb-4">
              <span className="text-2xl font-bold">Risk Score: {analysis.overall_risk_score.toFixed(1)}/100</span>
              <span className="text-lg text-gray-600">Confidence: {(analysis.confidence * 100).toFixed(1)}%</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-4">
              <div 
                className={`h-4 rounded-full ${
                  analysis.overall_risk_score < 30 ? 'bg-green-500' : 
                  analysis.overall_risk_score < 70 ? 'bg-yellow-500' : 'bg-red-500'
                }`}
                style={{ width: `${analysis.overall_risk_score}%` }}
              ></div>
            </div>
          </CardContent>
        </Card>

        {/* Rule Violations */}
        {analysis.rules.violations.length > 0 && (
          <Card className="mb-8">
            <CardHeader>
              <CardTitle className="text-red-600">Rule Violations</CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="space-y-2">
                {analysis.rules.violations.map((violation, index) => (
                  <li key={index} className="flex items-start">
                    <svg className="h-5 w-5 text-red-500 mr-2 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.732-.833-2.5 0L4.268 18.5c-.77.833.192 2.5 1.732 2.5z" />
                    </svg>
                    <span className="text-red-800">{violation}</span>
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>
        )}

        {/* Recommendations */}
        {analysis.rules.recommendations.length > 0 && (
          <Card className="mb-8">
            <CardHeader>
              <CardTitle className="text-blue-600">Recommendations</CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="space-y-2">
                {analysis.rules.recommendations.map((recommendation, index) => (
                  <li key={index} className="flex items-start">
                    <svg className="h-5 w-5 text-blue-500 mr-2 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <span className="text-blue-800">{recommendation}</span>
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* OCR Results */}
          <Card>
            <CardHeader>
              <CardTitle>Extracted Fields</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="flex justify-between items-center">
                  <span className="font-medium">Confidence:</span>
                  <span>{(analysis.ocr.extraction_confidence * 100).toFixed(1)}%</span>
                </div>
                
                {analysis.ocr.payee && (
                  <div className="flex justify-between items-center">
                    <span className="font-medium">Payee:</span>
                    <span>{analysis.ocr.payee}</span>
                  </div>
                )}
                
                {analysis.ocr.amount && (
                  <div className="flex justify-between items-center">
                    <span className="font-medium">Amount:</span>
                    <span className="font-mono">${analysis.ocr.amount}</span>
                  </div>
                )}
                
                {analysis.ocr.date && (
                  <div className="flex justify-between items-center">
                    <span className="font-medium">Date:</span>
                    <span>{analysis.ocr.date}</span>
                  </div>
                )}
                
                {analysis.ocr.check_number && (
                  <div className="flex justify-between items-center">
                    <span className="font-medium">Check Number:</span>
                    <span>{analysis.ocr.check_number}</span>
                  </div>
                )}
                
                {analysis.ocr.account_number && (
                  <div className="flex justify-between items-center">
                    <span className="font-medium">Account Number:</span>
                    <span className="font-mono">***{analysis.ocr.account_number.slice(-4)}</span>
                  </div>
                )}
                
                {analysis.ocr.routing_number && (
                  <div className="flex justify-between items-center">
                    <span className="font-medium">Routing Number:</span>
                    <span className="font-mono">***{analysis.ocr.routing_number.slice(-4)}</span>
                  </div>
                )}
                
                {analysis.ocr.memo && (
                  <div className="flex justify-between items-center">
                    <span className="font-medium">Memo:</span>
                    <span>{analysis.ocr.memo}</span>
                  </div>
                )}
                
                <div className="flex justify-between items-center">
                  <span className="font-medium">Signature Detected:</span>
                  <Badge variant={analysis.ocr.signature_detected ? 'default' : 'secondary'}>
                    {analysis.ocr.signature_detected ? 'Yes' : 'No'}
                  </Badge>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Forensics Results */}
          <Card>
            <CardHeader>
              <CardTitle>Forensics Analysis</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="flex justify-between items-center">
                  <span className="font-medium">Overall Score:</span>
                  <span>{analysis.forensics.overall_score.toFixed(1)}/100</span>
                </div>
                
                <div className="flex justify-between items-center">
                  <span className="font-medium">Edge Analysis:</span>
                  <span>{analysis.forensics.edge_score.toFixed(1)}/100</span>
                </div>
                
                <div className="flex justify-between items-center">
                  <span className="font-medium">Compression Analysis:</span>
                  <span>{analysis.forensics.compression_score.toFixed(1)}/100</span>
                </div>
                
                <div className="flex justify-between items-center">
                  <span className="font-medium">Font Analysis:</span>
                  <span>{analysis.forensics.font_score.toFixed(1)}/100</span>
                </div>
                
                {analysis.forensics.detected_anomalies.length > 0 && (
                  <div>
                    <span className="font-medium">Detected Anomalies:</span>
                    <ul className="mt-2 space-y-1">
                      {analysis.forensics.detected_anomalies.map((anomaly, index) => (
                        <li key={index} className="text-sm text-gray-600 ml-4">
                          • {anomaly}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Actions */}
        <div className="mt-8 flex space-x-4">
          <Button onClick={() => router.push('/upload')} variant="primary">
            Analyze Another Check
          </Button>
          <Button onClick={() => router.push('/history')} variant="outline">
            View History
          </Button>
        </div>
      </main>
    </div>
  );
}