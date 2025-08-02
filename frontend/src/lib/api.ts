'use client';

import {
  UserResponse,
  FileUploadResponse,
  AnalysisResponse,
  DashboardStats,
  AnalysisHistoryItem,
  PaginatedResponse,
  AnalysisRequest,
  FileUploadRequest,
} from '@/types/api';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';

class ApiClientError extends Error {
  status: number;
  
  constructor(message: string, status: number) {
    super(message);
    this.name = 'ApiClientError';
    this.status = status;
  }
}

export class ApiClient {
  private baseURL: string;
  
  constructor(baseURL: string = API_BASE_URL) {
    this.baseURL = baseURL;
  }
  
  private async request<T>(
    endpoint: string,
    options: RequestInit = {},
    token?: string | null
  ): Promise<T> {
    const url = `${this.baseURL}${endpoint}`;
    
    const headers: Record<string, string> = {
      ...(options.headers as Record<string, string>),
    };
    
    // Add authorization header if token provided
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    
    // Add Content-Type for JSON requests (unless it's FormData)
    if (options.body && !(options.body instanceof FormData)) {
      headers['Content-Type'] = 'application/json';
    }
    
    try {
      const response = await fetch(url, {
        ...options,
        headers,
      });
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Unknown error occurred' }));
        throw new ApiClientError(
          errorData.detail || `HTTP ${response.status}: ${response.statusText}`,
          response.status
        );
      }
      
      // Handle empty responses
      if (response.status === 204) {
        return {} as T;
      }
      
      return await response.json();
    } catch (error) {
      if (error instanceof ApiClientError) {
        throw error;
      }
      throw new ApiClientError(`Network error: ${error instanceof Error ? error.message : 'Unknown error'}`, 0);
    }
  }
  
  // Authentication endpoints
  async getCurrentUser(token: string): Promise<UserResponse> {
    return this.request<UserResponse>('/api/v1/auth/me', { method: 'GET' }, token);
  }
  
  async validateToken(token: string): Promise<{ valid: boolean; user?: UserResponse }> {
    try {
      const user = await this.getCurrentUser(token);
      return { valid: true, user };
    } catch (error) {
      return { valid: false };
    }
  }
  
  // File upload endpoints
  async uploadFile(file: File, token: string): Promise<FileUploadResponse> {
    const formData = new FormData();
    formData.append('file', file);
    
    return this.request<FileUploadResponse>(
      '/api/v1/files/upload',
      {
        method: 'POST',
        body: formData,
      },
      token
    );
  }
  
  async getFile(fileId: string, token: string): Promise<{ file_id: string; filename: string; s3_url: string }> {
    return this.request<{ file_id: string; filename: string; s3_url: string }>(
      `/api/v1/files/${fileId}`,
      { method: 'GET' },
      token
    );
  }
  
  async deleteFile(fileId: string, token: string): Promise<{ message: string }> {
    return this.request<{ message: string }>(
      `/api/v1/files/${fileId}`,
      { method: 'DELETE' },
      token
    );
  }
  
  // Analysis endpoints
  async analyzeFile(fileId: string, token: string): Promise<AnalysisResponse> {
    return this.request<AnalysisResponse>(
      '/api/v1/analyze/',
      {
        method: 'POST',
        body: JSON.stringify({ 
          file_id: fileId,
          analysis_types: ["forensics", "ocr", "rules"]
        }),
      },
      token
    );
  }
  
  async getAnalysis(analysisId: string, token: string): Promise<AnalysisResponse> {
    return this.request<AnalysisResponse>(
      `/api/v1/analyze/${analysisId}`,
      { method: 'GET' },
      token
    );
  }
  
  async getAnalysisByFileId(fileId: string, token: string): Promise<AnalysisResponse> {
    return this.request<AnalysisResponse>(
      `/api/v1/analyze/file/${fileId}`,
      { method: 'GET' },
      token
    );
  }
  
  async getAnalysisHistory(
    token: string,
    page: number = 1,
    size: number = 50,
    filters?: {
      start_date?: string;
      end_date?: string;
      min_risk_score?: number;
      max_risk_score?: number;
      status?: string;
    }
  ): Promise<PaginatedResponse<AnalysisHistoryItem>> {
    const params = new URLSearchParams({
      page: page.toString(),
      size: size.toString(),
    });
    
    if (filters) {
      Object.entries(filters).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== '') {
          params.append(key, value.toString());
        }
      });
    }
    
    
    return this.request<PaginatedResponse<AnalysisHistoryItem>>(
      `/api/v1/dashboard/history?${params}`,
      { method: 'GET' },
      token
    );
  }
  
  // Dashboard endpoints
  async getDashboardStats(
    token: string,
    filters?: {
      start_date?: string;
      end_date?: string;
      risk_threshold?: number;
    }
  ): Promise<DashboardStats> {
    const params = new URLSearchParams();
    
    if (filters) {
      Object.entries(filters).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          params.append(key, value.toString());
        }
      });
    }
    
    const queryString = params.toString();
    const endpoint = queryString ? `/api/v1/dashboard/stats?${queryString}` : '/api/v1/dashboard/stats';
    
    return this.request<DashboardStats>(endpoint, { method: 'GET' }, token);
  }
  
  // Scoring endpoints
  async getRiskScore(analysisId: string, token: string): Promise<{ risk_score: number; factors: Record<string, number> }> {
    return this.request<{ risk_score: number; factors: Record<string, number> }>(
      `/api/v1/scoring/${analysisId}`,
      { method: 'GET' },
      token
    );
  }
  
  async updateRiskThresholds(
    thresholds: Record<string, number>,
    token: string
  ): Promise<{ message: string }> {
    return this.request<{ message: string }>(
      '/api/v1/scoring/thresholds',
      {
        method: 'PUT',
        body: JSON.stringify(thresholds),
      },
      token
    );
  }
}

// Create singleton instance
export const apiClient = new ApiClient();

// Convenience functions that work with hooks
export const api = {
  getCurrentUser: (token: string) => apiClient.getCurrentUser(token),
  validateToken: (token: string) => apiClient.validateToken(token),
  uploadFile: (file: File, token: string) => apiClient.uploadFile(file, token),
  getFile: (fileId: string, token: string) => apiClient.getFile(fileId, token),
  deleteFile: (fileId: string, token: string) => apiClient.deleteFile(fileId, token),
  analyzeFile: (fileId: string, token: string) => apiClient.analyzeFile(fileId, token),
  getAnalysis: (analysisId: string, token: string) => apiClient.getAnalysis(analysisId, token),
  getAnalysisByFileId: (fileId: string, token: string) => apiClient.getAnalysisByFileId(fileId, token),
  getAnalysisHistory: (
    token: string,
    page?: number,
    size?: number,
    filters?: { start_date?: string; end_date?: string; min_risk_score?: number; max_risk_score?: number; status?: string }
  ) => apiClient.getAnalysisHistory(token, page, size, filters),
  getDashboardStats: (token: string, filters?: { start_date?: string; end_date?: string; risk_threshold?: number }) => apiClient.getDashboardStats(token, filters),
  getRiskScore: (analysisId: string, token: string) => apiClient.getRiskScore(analysisId, token),
  updateRiskThresholds: (thresholds: Record<string, number>, token: string) => 
    apiClient.updateRiskThresholds(thresholds, token),
};

export default apiClient;