'use client';

import { useState, useCallback } from 'react';
import { useAuth } from '@clerk/nextjs';
import { api } from '@/lib/api';
import { FileUploadResponse } from '@/types/api';
import { ERROR_MESSAGES, SUCCESS_MESSAGES } from '@/lib/constants';

interface UploadProgress {
  progress: number;
  loaded: number;
  total: number;
}

interface UseFileUploadOptions {
  onSuccess?: (response: FileUploadResponse) => void;
  onError?: (error: string) => void;
  onProgress?: (progress: UploadProgress) => void;
  maxRetries?: number;
}

interface UseFileUploadReturn {
  uploadFile: (file: File) => Promise<FileUploadResponse | null>;
  isUploading: boolean;
  progress: number;
  error: string | null;
  uploadedFile: FileUploadResponse | null;
  reset: () => void;
  retry: () => void;
}

export function useFileUpload(options: UseFileUploadOptions = {}): UseFileUploadReturn {
  const { getToken } = useAuth();
  const [isUploading, setIsUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [uploadedFile, setUploadedFile] = useState<FileUploadResponse | null>(null);
  const [lastFile, setLastFile] = useState<File | null>(null);
  const [retryCount, setRetryCount] = useState(0);

  const {
    onSuccess,
    onError,
    onProgress,
    maxRetries = 3,
  } = options;

  // Reset state
  const reset = useCallback(() => {
    setIsUploading(false);
    setProgress(0);
    setError(null);
    setUploadedFile(null);
    setLastFile(null);
    setRetryCount(0);
  }, []);

  // Upload file with progress tracking
  const uploadFile = useCallback(async (file: File): Promise<FileUploadResponse | null> => {
    try {
      setIsUploading(true);
      setProgress(0);
      setError(null);
      setLastFile(file);

      // Get authentication token
      const token = await getToken();
      if (!token) {
        throw new Error(ERROR_MESSAGES.UNAUTHORIZED);
      }

      // Simulate progress for better UX
      const progressInterval = setInterval(() => {
        setProgress((prev) => {
          if (prev >= 90) {
            clearInterval(progressInterval);
            return 90;
          }
          return prev + Math.random() * 20;
        });
      }, 200);

      // Call progress callback if provided
      if (onProgress) {
        onProgress({
          progress: 0,
          loaded: 0,
          total: file.size,
        });
      }

      // Upload the file
      const response = await api.uploadFile(file, token);

      // Complete progress
      clearInterval(progressInterval);
      setProgress(100);

      // Update state
      setUploadedFile(response);
      setIsUploading(false);
      setRetryCount(0);

      // Call success callback
      if (onSuccess) {
        onSuccess(response);
      }

      return response;
    } catch (error) {
      setIsUploading(false);
      setProgress(0);

      let errorMessage: string = ERROR_MESSAGES.UPLOAD_FAILED;
      
      if (error instanceof Error) {
        if (error.message.includes('unauthorized') || error.message.includes('401')) {
          errorMessage = ERROR_MESSAGES.UNAUTHORIZED;
        } else if (error.message.includes('network') || error.message.includes('fetch')) {
          errorMessage = ERROR_MESSAGES.NETWORK_ERROR;
        } else if (error.message.includes('server') || error.message.includes('500')) {
          errorMessage = ERROR_MESSAGES.SERVER_ERROR;
        } else {
          errorMessage = error.message;
        }
      }

      setError(errorMessage);

      // Call error callback
      if (onError) {
        onError(errorMessage);
      }

      console.error('File upload failed:', error);
      return null;
    }
  }, [getToken, onSuccess, onError, onProgress]);

  // Retry upload with exponential backoff
  const retry = useCallback(async () => {
    if (!lastFile || retryCount >= maxRetries) {
      setError('Maximum retry attempts reached');
      return;
    }

    const delay = Math.pow(2, retryCount) * 1000; // Exponential backoff
    setRetryCount(prev => prev + 1);

    setTimeout(() => {
      uploadFile(lastFile);
    }, delay);
  }, [lastFile, retryCount, maxRetries, uploadFile]);

  return {
    uploadFile,
    isUploading,
    progress,
    error,
    uploadedFile,
    reset,
    retry,
  };
}

// Batch upload hook for multiple files
export function useBatchFileUpload(options: UseFileUploadOptions = {}) {
  const [uploads, setUploads] = useState<Map<string, UseFileUploadReturn>>(new Map());
  const [totalProgress, setTotalProgress] = useState(0);
  const [isAnyUploading, setIsAnyUploading] = useState(false);

  const addUpload = useCallback((file: File) => {
    const fileId = `${file.name}-${file.size}-${file.lastModified}`;
    const uploadHook = useFileUpload({
      ...options,
      onSuccess: (response) => {
        options.onSuccess?.(response);
        updateTotalProgress();
      },
      onError: (error) => {
        options.onError?.(error);
        updateTotalProgress();
      },
    });

    setUploads(prev => new Map(prev.set(fileId, uploadHook)));
    uploadHook.uploadFile(file);

    return fileId;
  }, [options]);

  const updateTotalProgress = useCallback(() => {
    let totalProgress = 0;
    let uploading = false;

    uploads.forEach(upload => {
      totalProgress += upload.progress;
      if (upload.isUploading) uploading = true;
    });

    setTotalProgress(uploads.size > 0 ? totalProgress / uploads.size : 0);
    setIsAnyUploading(uploading);
  }, [uploads]);

  const removeUpload = useCallback((fileId: string) => {
    setUploads(prev => {
      const newMap = new Map(prev);
      newMap.delete(fileId);
      return newMap;
    });
  }, []);

  const resetAll = useCallback(() => {
    uploads.forEach(upload => upload.reset());
    setUploads(new Map());
    setTotalProgress(0);
    setIsAnyUploading(false);
  }, [uploads]);

  return {
    uploads: Array.from(uploads.entries()),
    addUpload,
    removeUpload,
    resetAll,
    totalProgress,
    isAnyUploading,
  };
}