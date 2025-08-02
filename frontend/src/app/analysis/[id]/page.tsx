'use client';

import { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useAuth } from '@clerk/nextjs';
import { NavigationBar } from '@/components/NavigationBar';
import { PDFGenerator } from '@/components/PDFGenerator';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Skeleton } from '@/components/ui/skeleton';
import { Progress } from '@/components/ui/progress';
import { 
  ArrowLeft,
  FileText,
  AlertTriangle,
  CheckCircle,
  Camera,
  Fingerprint,
  Type,
  Calculator,
  Clock,
  User,
  DollarSign,
  Calendar,
  Hash
} from 'lucide-react';
import { api } from '@/lib/api';
import { AnalysisResponse } from '@/types/api';
import { formatDate, getRiskLevel, getRiskColor, cn, formatRiskScore, formatConfidence, formatScore } from '@/lib/utils';
import { ROUTES } from '@/lib/constants';
import Link from 'next/link';

export default function AnalysisResultPage() {
  const params = useParams();
  const router = useRouter();
  const { getToken } = useAuth();
  const [analysis, setAnalysis] = useState<AnalysisResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const analysisId = params.id as string;

  const fetchAnalysisResult = async () => {
    try {
      setIsLoading(true);
      setError(null);

      const token = await getToken();
      if (!token) {
        throw new Error('Authentication token not available');
      }

      const analysisData = await api.getAnalysis(analysisId, token);
      setAnalysis(analysisData);
    } catch (error) {
      console.error('Failed to fetch analysis result:', error);
      setError(error instanceof Error ? error.message : 'Failed to load analysis result');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (analysisId) {
      fetchAnalysisResult();
    }
  }, [analysisId]);

  const handleDownloadReport = async () => {
    // PDF generation is now handled by the PDFGenerator component
    console.log('Download report for analysis:', analysisId);
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
              <div className="mt-4 space-x-2">
                <Button variant="outline" size="sm" onClick={fetchAnalysisResult}>
                  Try Again
                </Button>
                <Link href={ROUTES.HISTORY}>
                  <Button variant="outline" size="sm">
                    Back to History
                  </Button>
                </Link>
              </div>
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
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center space-x-4">
            <Button 
              variant="outline" 
              size="sm" 
              onClick={() => router.back()}
            >
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back
            </Button>
            <div>
              <h1 className="text-3xl font-bold text-gray-900">
                Analysis Results
              </h1>
              {isLoading ? (
                <Skeleton className="h-6 w-40 mt-1" />
              ) : analysis ? (
                <p className="text-lg text-gray-600">
                  Analysis ID: #{analysisId.slice(-8)} • {formatDate(analysis.timestamp)}
                </p>
              ) : null}
            </div>
          </div>
          <div className="flex space-x-2">
            {analysis && (
              <PDFGenerator 
                analysis={analysis}
                fileName={`check-analysis-${analysisId.slice(-8)}.pdf`}
              />
            )}
          </div>
        </div>

        {isLoading ? (
          /* Loading State */
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2 space-y-6">
              <Card>
                <CardHeader>
                  <Skeleton className="h-6 w-40" />
                  <Skeleton className="h-4 w-60" />
                </CardHeader>
                <CardContent className="space-y-4">
                  <Skeleton className="h-32 w-full" />
                </CardContent>
              </Card>
              
              <Card>
                <CardHeader>
                  <Skeleton className="h-6 w-32" />
                </CardHeader>
                <CardContent className="space-y-4">
                  {[...Array(4)].map((_, i) => (
                    <div key={i} className="space-y-2">
                      <Skeleton className="h-4 w-24" />
                      <Skeleton className="h-4 w-full" />
                    </div>
                  ))}
                </CardContent>
              </Card>
            </div>
            
            <div className="space-y-6">
              <Card>
                <CardHeader>
                  <Skeleton className="h-6 w-32" />
                </CardHeader>
                <CardContent>
                  <Skeleton className="h-24 w-24 rounded-full mx-auto mb-4" />
                  <Skeleton className="h-8 w-16 mx-auto" />
                </CardContent>
              </Card>
            </div>
          </div>
        ) : analysis ? (
          /* Analysis Results */
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Main Content */}
            <div className="lg:col-span-2 space-y-6">
              {/* Risk Assessment Overview */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center space-x-2">
                    <Calculator className="h-5 w-5" />
                    <span>Risk Assessment Overview</span>
                  </CardTitle>
                  <CardDescription>
                    Summary of fraud detection analysis and key findings
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className={cn(
                    "rounded-lg p-6 border-2",
                    getRiskLevel(analysis.overall_risk_score) === 'critical' ? "border-red-200 bg-red-50" :
                    getRiskLevel(analysis.overall_risk_score) === 'high' ? "border-orange-200 bg-orange-50" :
                    getRiskLevel(analysis.overall_risk_score) === 'medium' ? "border-yellow-200 bg-yellow-50" :
                    "border-green-200 bg-green-50"
                  )}>
                    <div className="flex items-center justify-between mb-4">
                      <div>
                        <h3 className="text-lg font-semibold text-gray-900">
                          Risk Level: {getRiskLevel(analysis.overall_risk_score)}
                        </h3>
                        <p className="text-sm text-gray-600">
                          Based on comprehensive fraud detection analysis
                        </p>
                      </div>
                      <div className={cn("text-4xl font-bold", getRiskColor(analysis.overall_risk_score))}>
                        {formatRiskScore(analysis.overall_risk_score)}
                      </div>
                    </div>
                    <Progress 
                      value={analysis.overall_risk_score} 
                      className="h-3"
                    />
                  </div>

                  {/* Key Findings */}
                  {analysis.rules?.violations && analysis.rules.violations.length > 0 && (
                    <div className="mt-6">
                      <h4 className="font-medium text-gray-900 mb-3">Key Findings:</h4>
                      <div className="space-y-2">
                        {analysis.rules.violations.slice(0, 3).map((violation, index) => (
                          <div key={index} className="flex items-center space-x-2 text-sm">
                            <AlertTriangle className="h-4 w-4 text-yellow-500" />
                            <span>{violation}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* Forensic Analysis */}
              {analysis.forensics && (
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center space-x-2">
                      <Fingerprint className="h-5 w-5" />
                      <span>Forensic Analysis</span>
                    </CardTitle>
                    <CardDescription>
                      Image forensics and technical analysis results
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-6">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div>
                        <h4 className="font-medium text-gray-900 mb-2">Forensics Scores</h4>
                        <div className="space-y-1 text-sm">
                          <div className="flex justify-between">
                            <span>Edge Score:</span>
                            <span>{analysis.forensics.edge_score ? formatScore(analysis.forensics.edge_score) : 'N/A'}</span>
                          </div>
                          <div className="flex justify-between">
                            <span>Compression Score:</span>
                            <span>{analysis.forensics.compression_score ? formatScore(analysis.forensics.compression_score) : 'N/A'}</span>
                          </div>
                          <div className="flex justify-between">
                            <span>Font Score:</span>
                            <span>{analysis.forensics.font_score ? formatScore(analysis.forensics.font_score) : 'N/A'}</span>
                          </div>
                        </div>
                      </div>

                      <div>
                        <h4 className="font-medium text-gray-900 mb-2">Detected Anomalies</h4>
                        <div className="space-y-1 text-sm">
                          {analysis.forensics.detected_anomalies.length > 0 ? (
                            analysis.forensics.detected_anomalies.map((anomaly, index) => (
                              <div key={index} className="flex items-center space-x-2">
                                <span className="text-red-500">⚠️</span>
                                <span>{anomaly}</span>
                              </div>
                            ))
                          ) : (
                            <div className="flex items-center space-x-2">
                              <span className="text-green-500">✅</span>
                              <span>No anomalies detected</span>
                            </div>
                          )}
                        </div>
                      </div>
                    </div>

                    <div>
                      <h4 className="font-medium text-gray-900 mb-2">Overall Forensics Score</h4>
                      <Progress 
                        value={analysis.forensics.overall_score * 100} 
                        className="h-2"
                      />
                      <p className="text-xs text-gray-500 mt-1">
                        {formatRiskScore(analysis.forensics.overall_score)}
                      </p>
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* OCR Results */}
              {analysis.ocr && (
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center space-x-2">
                      <Type className="h-5 w-5" />
                      <span>Extracted Information</span>
                    </CardTitle>
                    <CardDescription>
                      Text and data extracted from the check using OCR
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                      <div className="space-y-4">
                        <div>
                          <label className="text-sm font-medium text-gray-500 flex items-center">
                            <User className="h-4 w-4 mr-1" />
                            Payee
                          </label>
                          <p className="text-gray-900">{analysis.ocr.payee || 'Not detected'}</p>
                        </div>

                        <div>
                          <label className="text-sm font-medium text-gray-500 flex items-center">
                            <DollarSign className="h-4 w-4 mr-1" />
                            Amount
                          </label>
                          <p className="text-gray-900">
                            {analysis.ocr.amount || 'Not detected'}
                          </p>
                        </div>

                        <div>
                          <label className="text-sm font-medium text-gray-500 flex items-center">
                            <Calendar className="h-4 w-4 mr-1" />
                            Date
                          </label>
                          <p className="text-gray-900">{analysis.ocr.date || 'Not detected'}</p>
                        </div>
                      </div>

                      <div className="space-y-4">
                        <div>
                          <label className="text-sm font-medium text-gray-500 flex items-center">
                            <Hash className="h-4 w-4 mr-1" />
                            Check Number
                          </label>
                          <p className="text-gray-900 font-mono">{analysis.ocr.check_number || 'Not detected'}</p>
                        </div>

                        <div>
                          <label className="text-sm font-medium text-gray-500 flex items-center">
                            <Hash className="h-4 w-4 mr-1" />
                            Account Number
                          </label>
                          <p className="text-gray-900 font-mono">{analysis.ocr.account_number || 'Not detected'}</p>
                        </div>

                        <div>
                          <label className="text-sm font-medium text-gray-500 flex items-center">
                            <Hash className="h-4 w-4 mr-1" />
                            Routing Number
                          </label>
                          <p className="text-gray-900 font-mono">{analysis.ocr.routing_number || 'Not detected'}</p>
                        </div>
                      </div>
                    </div>

                    {analysis.ocr.field_confidences && (
                      <div className="mt-6">
                        <h4 className="font-medium text-gray-900 mb-3">OCR Field Confidence</h4>
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                          {Object.entries(analysis.ocr.field_confidences).map(([field, score]) => (
                            <div key={field} className="text-center">
                              <div className="text-sm font-medium text-gray-500 capitalize">
                                {field.replace('_', ' ')}
                              </div>
                              <div className="text-lg font-bold">
                                {formatConfidence(score)}
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </CardContent>
                </Card>
              )}

              {/* Rule Engine Details */}
              {analysis.rules && (
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center space-x-2">
                      <CheckCircle className="h-5 w-5" />
                      <span>Fraud Detection Rules</span>
                    </CardTitle>
                    <CardDescription>
                      Detailed breakdown of fraud detection rule analysis
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    {analysis.rules.violations && analysis.rules.violations.length > 0 ? (
                      <div className="space-y-4">
                        <h4 className="font-medium text-red-600">Rule Violations ({analysis.rules.violations.length})</h4>
                        {analysis.rules.violations.map((violation, index) => (
                          <div key={index} className="border border-red-200 rounded-lg p-4 bg-red-50">
                            <div className="flex items-start justify-between">
                              <div className="flex-1">
                                <p className="text-sm text-gray-600">{violation}</p>
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="text-center py-8">
                        <CheckCircle className="h-12 w-12 text-green-500 mx-auto mb-4" />
                        <p className="text-lg font-medium text-gray-900">No Rule Violations</p>
                        <p className="text-gray-500">All fraud detection checks passed successfully</p>
                      </div>
                    )}

                    {(analysis.rules.violations || analysis.rules.passed_rules) && (
                      <div className="mt-6 pt-4 border-t border-gray-200">
                        <div className="grid grid-cols-3 gap-4 text-center">
                          <div>
                            <div className="text-2xl font-bold text-gray-900">
                              {(analysis.rules.violations?.length || 0) + (analysis.rules.passed_rules?.length || 0)}
                            </div>
                            <div className="text-sm text-gray-500">Total Rules</div>
                          </div>
                          <div>
                            <div className="text-2xl font-bold text-red-600">
                              {analysis.rules.violations?.length || 0}
                            </div>
                            <div className="text-sm text-gray-500">Violations</div>
                          </div>
                          <div>
                            <div className="text-2xl font-bold text-green-600">
                              {analysis.rules.passed_rules?.length || 0}
                            </div>
                            <div className="text-sm text-gray-500">Passed</div>
                          </div>
                        </div>
                      </div>
                    )}
                  </CardContent>
                </Card>
              )}
            </div>

            {/* Sidebar */}
            <div className="space-y-6">
              {/* Risk Score Summary */}
              <Card>
                <CardHeader>
                  <CardTitle>Risk Score</CardTitle>
                  <CardDescription>
                    Overall fraud risk assessment
                  </CardDescription>
                </CardHeader>
                <CardContent className="text-center">
                  <div className={cn(
                    "w-24 h-24 rounded-full mx-auto mb-4 flex items-center justify-center text-2xl font-bold border-4",
                    getRiskLevel(analysis.overall_risk_score) === 'critical' ? "border-red-600 bg-red-50 text-red-600" :
                    getRiskLevel(analysis.overall_risk_score) === 'high' ? "border-orange-500 bg-orange-50 text-orange-600" :
                    getRiskLevel(analysis.overall_risk_score) === 'medium' ? "border-yellow-500 bg-yellow-50 text-yellow-600" :
                    "border-green-500 bg-green-50 text-green-600"
                  )}>
                    {formatRiskScore(analysis.overall_risk_score)}
                  </div>
                  <Badge 
                    variant={
                      getRiskLevel(analysis.overall_risk_score) === 'critical' ? "destructive" :
                      getRiskLevel(analysis.overall_risk_score) === 'high' ? "destructive" :
                      getRiskLevel(analysis.overall_risk_score) === 'medium' ? "default" :
                      "secondary"
                    }
                    className="mb-2"
                  >
                    {getRiskLevel(analysis.overall_risk_score)}
                  </Badge>
                  <p className="text-sm text-gray-600">
                    Out of 100 possible points
                  </p>
                </CardContent>
              </Card>

              {/* Analysis Info */}
              <Card>
                <CardHeader>
                  <CardTitle>Analysis Information</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div className="flex items-center text-sm">
                    <Calendar className="h-4 w-4 mr-2 text-gray-400" />
                    <span className="text-gray-600">Created:</span>
                    <span className="ml-auto">{formatDate(analysis.timestamp)}</span>
                  </div>
                  
                  <div className="flex items-center text-sm">
                    <Clock className="h-4 w-4 mr-2 text-gray-400" />
                    <span className="text-gray-600">Processing Time:</span>
                    <span className="ml-auto">
                      {analysis.processing_time ? `${analysis.processing_time.toFixed(1)}s` : 'N/A'}
                    </span>
                  </div>

                  <div className="flex items-center text-sm">
                    <FileText className="h-4 w-4 mr-2 text-gray-400" />
                    <span className="text-gray-600">File ID:</span>
                    <span className="ml-auto font-mono text-xs">
                      {analysis.file_id.slice(-8)}
                    </span>
                  </div>

                  <div className="flex items-center text-sm">
                    <Hash className="h-4 w-4 mr-2 text-gray-400" />
                    <span className="text-gray-600">Analysis ID:</span>
                    <span className="ml-auto font-mono text-xs">
                      {analysisId.slice(-8)}
                    </span>
                  </div>
                </CardContent>
              </Card>

              {/* Quick Actions */}
              <Card>
                <CardHeader>
                  <CardTitle>Actions</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <PDFGenerator 
                    analysis={analysis}
                    fileName={`check-analysis-${analysisId.slice(-8)}.pdf`}
                    className="w-full"
                  />
                  
                  <Link href={ROUTES.UPLOAD} className="block">
                    <Button className="w-full justify-start" variant="outline">
                      <Camera className="h-4 w-4 mr-2" />
                      New Analysis
                    </Button>
                  </Link>
                  
                  <Link href={ROUTES.HISTORY} className="block">
                    <Button className="w-full justify-start" variant="outline">
                      <FileText className="h-4 w-4 mr-2" />
                      View History
                    </Button>
                  </Link>
                </CardContent>
              </Card>
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}