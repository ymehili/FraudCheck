// API Response Types matching backend schemas
export interface UserResponse {
  id: string;
  email: string;
  created_at: string;
  updated_at: string;
}

export interface FileUploadResponse {
  file_id: string;
  filename?: string;
  s3_url?: string;
  upload_timestamp?: string;
  message: string;
}

export interface AnalysisResponse {
  analysis_id: string;
  file_id: string;
  timestamp: string;
  processing_time?: number;
  forensics?: ForensicsResult;
  ocr?: OCRResult;
  rules?: RuleEngineResult;
  overall_risk_score: number;
  confidence: number;
}

export interface ForensicsResult {
  edge_score: number;
  compression_score: number;
  font_score: number;
  overall_score: number;
  detected_anomalies: string[];
  edge_inconsistencies: Record<string, any>;
  compression_artifacts: Record<string, any>;
  font_analysis: Record<string, any>;
}

export interface OCRResult {
  payee?: string;
  amount?: string;
  date?: string;
  account_number?: string;
  routing_number?: string;
  check_number?: string;
  memo?: string;
  signature_detected: boolean;
  extraction_confidence: number;
  raw_text?: string;
  field_confidences: Record<string, number>;
}

export interface RuleEngineResult {
  risk_score: number;
  violations: string[];
  passed_rules: string[];
  rule_scores: Record<string, number>;
  confidence_factors: Record<string, number>;
  recommendations: string[];
  overall_confidence?: number;
}

export interface DashboardStats {
  total_analyses: number;
  analyses_today: number;
  analyses_this_week: number;
  analyses_this_month: number;
  analyses_change?: number;
  high_risk_count: number;
  risk_distribution: RiskDistribution | Array<{name: string, value: number, color: string}>;
  average_risk_score: number;
  average_confidence: number;
  average_processing_time?: number;
  most_common_violations: Array<Record<string, any>>;
  trend_data: TrendDataPoint[];
  processing_stats: Record<string, any>;
  recent_analyses?: Array<{
    analysis_id: string;
    risk_score: number;
    created_at: string;
  }>;
}

export interface RiskDistribution {
  low: number;
  medium: number;
  high: number;
  critical: number;
  total: number;
}

export interface TrendDataPoint {
  date: string;
  count: number;
  avg_risk_score: number;
  avg_confidence: number;
}

// Request Types
export interface AnalysisRequest {
  file_id: string;
  analysis_type?: string;
}

export interface FileUploadRequest {
  file: File;
  metadata?: Record<string, any>;
}

// Common API Types
export interface ApiError {
  detail: string;
  status_code: number;
  timestamp: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

// Analysis History Types
export interface AnalysisHistoryItem {
  analysis_id: string;
  file_id: string;
  filename?: string;
  timestamp: string;
  created_at: string;
  overall_risk_score: number;
  confidence: number;
  status: 'completed' | 'processing' | 'failed';
  violations_count: number;
  primary_violations: string[];
  processing_time?: number;
}