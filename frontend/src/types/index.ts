export interface User {
  id: string;
  email: string;
  created_at: string;
  updated_at: string;
}

export interface FileRecord {
  id: string;
  user_id: string;
  filename: string;
  s3_key: string;
  s3_url: string;
  file_size: number;
  mime_type: string;
  upload_timestamp: string;
}

export interface FileUploadResponse {
  file_id: string;
  s3_url: string;
  upload_timestamp: string;
  message: string;
}

export interface FileListResponse {
  files: FileRecord[];
  total: number;
  page: number;
  per_page: number;
}

export interface AnalysisResults {
  risk_score: number;
  detected_issues: string[];
  confidence: number;
  recommendations: string[];
  analysis_timestamp: string;
}

export interface CheckAnalysisReport {
  file_id: string;
  filename: string;
  upload_date: string;
  file_size: string;
  analysis_results?: AnalysisResults;
}

export interface APIError {
  detail: string;
  status_code: number;
}

export interface UploadProgress {
  loaded: number;
  total: number;
  percentage: number;
}

export type UploadStatus = 'idle' | 'uploading' | 'success' | 'error';

export type FileType = 'image/jpeg' | 'image/png' | 'application/pdf';

export interface CameraConstraints {
  width: number;
  height: number;
  facingMode: 'user' | 'environment';
}

export interface NotificationProps {
  type: 'success' | 'error' | 'warning' | 'info';
  title: string;
  message: string;
  duration?: number;
}

export interface PaginationProps {
  currentPage: number;
  totalPages: number;
  pageSize: number;
  totalItems: number;
  onPageChange: (page: number) => void;
}

export interface FilterOptions {
  dateRange?: {
    from: string;
    to: string;
  };
  fileType?: FileType[];
  riskScore?: {
    min: number;
    max: number;
  };
}

export interface SortOptions {
  field: 'upload_timestamp' | 'filename' | 'file_size' | 'risk_score';
  direction: 'asc' | 'desc';
}