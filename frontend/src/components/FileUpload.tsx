'use client';

import { useState, useCallback, useRef } from 'react';
import { Upload, X, File, Image as ImageIcon, AlertCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Progress } from '@/components/ui/progress';
import { cn, formatFileSize } from '@/lib/utils';
import {
  SUPPORTED_FILE_TYPES,
  MAX_FILE_SIZE,
  FILE_UPLOAD_ACCEPT,
  ERROR_MESSAGES,
} from '@/lib/constants';

interface FileUploadProps {
  onUpload: (file: File) => void;
  onUploadProgress?: (progress: number) => void;
  className?: string;
  disabled?: boolean;
  accept?: string;
  maxSize?: number;
  multiple?: boolean;
}

export function FileUpload({
  onUpload,
  onUploadProgress,
  className,
  disabled = false,
  accept = FILE_UPLOAD_ACCEPT,
  maxSize = MAX_FILE_SIZE,
  multiple = false,
}: FileUploadProps) {
  const [dragActive, setDragActive] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [isUploading, setIsUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // File validation
  const validateFile = useCallback((file: File): boolean => {
    setError(null);

    // Check file type
    if (!SUPPORTED_FILE_TYPES.includes(file.type as string)) {
      setError(`${ERROR_MESSAGES.INVALID_FILE_TYPE}. Supported formats: JPG, PNG, PDF`);
      return false;
    }

    // Check file size
    if (file.size > maxSize) {
      setError(`${ERROR_MESSAGES.FILE_TOO_LARGE}. Maximum size: ${formatFileSize(maxSize)}`);
      return false;
    }

    return true;
  }, [maxSize]);

  // Handle file selection
  const handleFiles = useCallback(async (files: FileList) => {
    if (files.length === 0) return;

    const file = files[0]; // Take first file if multiple not allowed
    if (!validateFile(file)) return;

    setSelectedFile(file);
    setError(null);
    setIsUploading(true);
    setUploadProgress(0);

    try {
      // Simulate upload progress if callback provided
      if (onUploadProgress) {
        const progressInterval = setInterval(() => {
          setUploadProgress((prev) => {
            if (prev >= 90) {
              clearInterval(progressInterval);
              return 90;
            }
            return prev + 10;
          });
        }, 100);
      }

      // Call the upload handler
      await onUpload(file);
      
      setUploadProgress(100);
      setTimeout(() => {
        setIsUploading(false);
        setUploadProgress(0);
        setSelectedFile(null);
      }, 1000);
    } catch (error) {
      console.error('Upload failed:', error);
      setError(ERROR_MESSAGES.UPLOAD_FAILED);
      setIsUploading(false);
      setUploadProgress(0);
    }
  }, [onUpload, onUploadProgress, validateFile]);

  // Drag handlers
  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      setDragActive(false);

      if (disabled || isUploading) return;

      const { files } = e.dataTransfer;
      if (files && files.length > 0) {
        handleFiles(files);
      }
    },
    [disabled, isUploading, handleFiles]
  );

  // File input change handler
  const handleInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const { files } = e.target;
      if (files && files.length > 0) {
        handleFiles(files);
      }
      // Reset input value to allow selecting the same file again
      e.target.value = '';
    },
    [handleFiles]
  );

  // Click to select file
  const openFileSelector = useCallback(() => {
    if (!disabled && !isUploading) {
      fileInputRef.current?.click();
    }
  }, [disabled, isUploading]);

  // Remove selected file
  const removeFile = useCallback(() => {
    setSelectedFile(null);
    setError(null);
    setUploadProgress(0);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  }, []);

  // Get file icon
  const getFileIcon = useCallback((file: File) => {
    if (file.type.startsWith('image/')) {
      return <ImageIcon className="h-8 w-8 text-blue-500" />;
    }
    return <File className="h-8 w-8 text-gray-500" />;
  }, []);

  return (
    <div className={cn('w-full max-w-lg mx-auto', className)}>
      <Card
        className={cn(
          'border-2 border-dashed transition-colors',
          dragActive && !disabled ? 'border-blue-500 bg-blue-50' : 'border-gray-300',
          disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer hover:border-gray-400'
        )}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        onClick={openFileSelector}
      >
        <CardContent className="flex flex-col items-center justify-center p-6 text-center">
          {/* Hidden file input */}
          <input
            ref={fileInputRef}
            type="file"
            accept={accept}
            multiple={multiple}
            onChange={handleInputChange}
            className="hidden"
            disabled={disabled}
          />

          {selectedFile && !isUploading ? (
            /* Selected file display */
            <div className="w-full">
              <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                <div className="flex items-center space-x-3">
                  {getFileIcon(selectedFile)}
                  <div className="text-left">
                    <p className="font-medium text-gray-900">{selectedFile.name}</p>
                    <p className="text-sm text-gray-500">
                      {formatFileSize(selectedFile.size)}
                    </p>
                  </div>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={(e) => {
                    e.stopPropagation();
                    removeFile();
                  }}
                >
                  <X className="h-4 w-4" />
                </Button>
              </div>
            </div>
          ) : isUploading ? (
            /* Upload progress */
            <div className="w-full">
              <Upload className="h-12 w-12 text-blue-500 mx-auto mb-4" />
              <p className="text-lg font-medium text-gray-900 mb-2">Uploading...</p>
              <p className="text-sm text-gray-600 mb-4">{selectedFile?.name}</p>
              <Progress value={uploadProgress} className="w-full" />
              <p className="text-sm text-gray-500 mt-2">{uploadProgress}% complete</p>
            </div>
          ) : (
            /* Upload area */
            <div>
              <Upload className="h-12 w-12 text-gray-400 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">
                {dragActive ? 'Drop your file here' : 'Upload a check image or PDF'}
              </h3>
              <p className="text-sm text-gray-600 mb-4">
                Drag and drop your file here, or click to browse
              </p>
              <Button type="button" variant="outline" disabled={disabled}>
                Choose File
              </Button>
              <div className="mt-4 text-xs text-gray-500">
                <p>Supported formats: JPG, PNG, PDF</p>
                <p>Maximum file size: {formatFileSize(maxSize)}</p>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Error display */}
      {error && (
        <Alert variant="destructive" className="mt-4">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}
    </div>
  );
}