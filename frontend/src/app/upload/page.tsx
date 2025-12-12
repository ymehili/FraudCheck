'use client';

import { useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@clerk/nextjs';
import { Camera, Upload, FileText, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Progress } from '@/components/ui/progress';
import { CameraCapture } from '@/components/CameraCapture';
import { FileUpload } from '@/components/FileUpload';
import { useFileUpload } from '@/hooks/useFileUpload';
import { cn } from '@/lib/utils';
import { ROUTES, ERROR_MESSAGES } from '@/lib/constants';
import { FileUploadResponse } from '@/types/api';
import { AppShell } from '@/components/AppShell';

type UploadMethod = 'camera' | 'file' | null;

export default function UploadPage() {
  const router = useRouter();
  const { getToken } = useAuth();
  const [selectedMethod, setSelectedMethod] = useState<UploadMethod>(null);
  const [analysisProgress, setAnalysisProgress] = useState(0);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisComplete, setAnalysisComplete] = useState(false);

  const { uploadFile, isUploading, error: uploadError } = useFileUpload({
    onSuccess: handleUploadSuccess,
    onError: (error) => {
      console.error('Upload failed:', error);
    },
  });

  async function handleUploadSuccess(response: FileUploadResponse) {
    console.log('File uploaded successfully:', response);
    
    // Start analysis automatically after successful upload
    await startAnalysis(response.file_id);
  }

  const startAnalysis = useCallback(async (fileId: string) => {
    try {
      setIsAnalyzing(true);
      setAnalysisProgress(0);

      const token = await getToken();
      if (!token) {
        throw new Error(ERROR_MESSAGES.UNAUTHORIZED);
      }

      // Start async analysis using the new streaming endpoint
      const analysisResponse = await fetch('/api/analyze/async', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({ 
          file_id: fileId,
          analysis_types: ["forensics", "ocr", "rules"]
        }),
      });

      if (!analysisResponse.ok) {
        const errorData = await analysisResponse.json().catch(() => ({ error: 'Analysis failed' }));
        throw new Error(errorData.message || errorData.error || 'Analysis failed');
      }

      const analysisResult = await analysisResponse.json();
      
      // If analysis already exists, redirect immediately
      if (analysisResult.status === 'completed') {
        setAnalysisProgress(100);
        setIsAnalyzing(false);
        setAnalysisComplete(true);
        
        setTimeout(() => {
          router.push(analysisResult.result_url || `${ROUTES.ANALYSIS}/${analysisResult.result_url?.split('/').pop()}`);
        }, 1000);
        return;
      }

      const taskId = analysisResult.task_id;
      
      // Poll for task progress using the new streaming progress tracking
      const pollProgress = async () => {
        try {
          const statusResponse = await fetch(`/api/tasks/${taskId}`, {
            headers: {
              'Authorization': `Bearer ${token}`,
            },
          });
          
          if (!statusResponse.ok) {
            throw new Error('Failed to get task status');
          }
          
          const statusData = await statusResponse.json();
          
          // Update progress based on task status
          if (statusData.progress !== undefined) {
            setAnalysisProgress(Math.round(statusData.progress * 100));
          }
          
          // Handle different task states
          if (statusData.status === 'success' || statusData.status === 'completed') {
            setAnalysisProgress(100);
            setIsAnalyzing(false);
            setAnalysisComplete(true);
            
            // Get the analysis result ID from the task result
            const resultId = statusData.result_id || statusData.result?.result_id;
            
            setTimeout(() => {
              router.push(`${ROUTES.ANALYSIS}/${resultId}`);
            }, 2000);
            
            return true; // Stop polling
          } else if (statusData.status === 'failure' || statusData.status === 'retry') {
            throw new Error(statusData.error_message || 'Analysis failed');
          }
          
          return false; // Continue polling
        } catch (error) {
          console.error('Error polling task status:', error);
          throw error;
        }
      };
      
      // Start polling every 2 seconds
      const pollInterval = setInterval(async () => {
        try {
          const shouldStop = await pollProgress();
          if (shouldStop) {
            clearInterval(pollInterval);
          }
        } catch (error) {
          clearInterval(pollInterval);
          throw error;
        }
      }, 2000);
      
      // Initial poll
      try {
        const shouldStop = await pollProgress();
        if (shouldStop) {
          clearInterval(pollInterval);
        }
      } catch (error) {
        clearInterval(pollInterval);
        throw error;
      }

    } catch (error) {
      console.error('Analysis failed:', error);
      setIsAnalyzing(false);
      setAnalysisProgress(0);
    }
  }, [getToken, router]);

  const handleFileCapture = useCallback((file: File) => {
    uploadFile(file);
  }, [uploadFile]);

  const handleFileUpload = useCallback((file: File) => {
    uploadFile(file);
  }, [uploadFile]);

  const resetUpload = useCallback(() => {
    setSelectedMethod(null);
    setAnalysisProgress(0);
    setIsAnalyzing(false);
    setAnalysisComplete(false);
  }, []);

  // Show analysis progress
  if (isUploading || isAnalyzing || analysisComplete) {
    return (
      <AppShell contentClassName="max-w-2xl">
          <Card>
            <CardHeader className="text-center">
              <CardTitle className="flex items-center justify-center space-x-2">
                {isUploading && (
                  <>
                    <Upload className="h-6 w-6" />
                    <span>Uploading File</span>
                  </>
                )}
                {isAnalyzing && (
                  <>
                    <Loader2 className="h-6 w-6 animate-spin" />
                    <span>Analyzing Check</span>
                  </>
                )}
                {analysisComplete && (
                  <>
                    <FileText className="h-6 w-6 text-green-600" />
                    <span>Analysis Complete</span>
                  </>
                )}
              </CardTitle>
              <CardDescription>
                {isUploading && 'Please wait while we upload your file...'}
                {isAnalyzing && 'Our AI is analyzing your check for fraud indicators...'}
                {analysisComplete && 'Analysis completed successfully! Redirecting to results...'}
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {isUploading && (
                <div className="text-center">
                  <div className="w-16 h-16 mx-auto mb-4 border-4 border-primary/20 border-t-primary rounded-full animate-spin"></div>
                  <p className="text-muted-foreground">Uploading your file securely...</p>
                </div>
              )}
              
              {(isAnalyzing || analysisComplete) && (
                <div className="space-y-4">
                  <div className="text-center">
                    <div className="text-3xl font-bold text-blue-600 mb-2">
                      {analysisProgress}%
                    </div>
                    <Progress value={analysisProgress} className="w-full" />
                  </div>
                  
                  {analysisProgress < 100 && (
                    <div className="text-sm text-muted-foreground space-y-2">
                      {analysisProgress < 30 && <p>Processing image quality…</p>}
                      {analysisProgress >= 30 && analysisProgress < 60 && <p>Performing forensic analysis…</p>}
                      {analysisProgress >= 60 && analysisProgress < 90 && <p>Extracting text with OCR…</p>}
                      {analysisProgress >= 90 && <p>Applying fraud detection rules…</p>}
                    </div>
                  )}
                  
                  {analysisComplete && (
                    <Alert>
                      <FileText className="h-4 w-4" />
                      <AlertDescription>
                        Analysis completed! You&apos;ll be redirected to the results page shortly.
                      </AlertDescription>
                    </Alert>
                  )}
                </div>
              )}

              <div className="flex justify-center">
                <Button variant="outline" onClick={resetUpload}>
                  Start New Analysis
                </Button>
              </div>
            </CardContent>
          </Card>
      </AppShell>
    );
  }

  return (
    <AppShell contentClassName="max-w-4xl">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-semibold tracking-tight text-foreground mb-4">
            Upload Check for Analysis
          </h1>
          <p className="text-lg text-muted-foreground">
            Choose how you&apos;d like to provide your check image for fraud detection analysis
          </p>
        </div>

        {/* Error display */}
        {uploadError && (
          <Alert variant="destructive" className="mb-6">
            <AlertDescription>{uploadError}</AlertDescription>
          </Alert>
        )}

        {!selectedMethod ? (
          /* Method selection */
          <div className="grid md:grid-cols-2 gap-6 max-w-2xl mx-auto">
            <Card 
              className={cn(
                "cursor-pointer border-2 transition-all",
                "hover:border-primary/60 card-hover"
              )}
              onClick={() => setSelectedMethod('camera')}
            >
              <CardHeader className="text-center">
                <div className="w-16 h-16 mx-auto mb-4 bg-blue-100 rounded-full flex items-center justify-center">
                  <Camera className="h-8 w-8 text-blue-600" />
                </div>
                <CardTitle>Camera Capture</CardTitle>
                <CardDescription>
                  Take a photo of your check using your device&apos;s camera
                </CardDescription>
              </CardHeader>
              <CardContent>
                <ul className="text-sm text-muted-foreground space-y-1">
                  <li>• Quick and convenient</li>
                  <li>• Real-time capture guidance</li>
                  <li>• Optimal for mobile devices</li>
                </ul>
              </CardContent>
            </Card>

            <Card 
              className={cn(
                "cursor-pointer border-2 transition-all",
                "hover:border-primary/60 card-hover"
              )}
              onClick={() => setSelectedMethod('file')}
            >
              <CardHeader className="text-center">
                <div className="w-16 h-16 mx-auto mb-4 bg-green-100 rounded-full flex items-center justify-center">
                  <Upload className="h-8 w-8 text-green-600" />
                </div>
                <CardTitle>File Upload</CardTitle>
                <CardDescription>
                  Upload an existing image or PDF file from your device
                </CardDescription>
              </CardHeader>
              <CardContent>
                <ul className="text-sm text-muted-foreground space-y-1">
                  <li>• Support for JPG, PNG, PDF</li>
                  <li>• Drag and drop interface</li>
                  <li>• Up to 10MB file size</li>
                </ul>
              </CardContent>
            </Card>
          </div>
        ) : (
          /* Selected method */
          <div className="max-w-2xl mx-auto">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-semibold">
                {selectedMethod === 'camera' ? 'Capture Check Photo' : 'Upload Check File'}
              </h2>
              <Button variant="outline" onClick={() => setSelectedMethod(null)}>
                Change Method
              </Button>
            </div>

            {selectedMethod === 'camera' && (
              <CameraCapture onCapture={handleFileCapture} />
            )}

            {selectedMethod === 'file' && (
              <FileUpload onUpload={handleFileUpload} />
            )}
          </div>
        )}

        {/* Instructions */}
        <div className="mt-12 rounded-xl border bg-card/60 p-6">
          <h3 className="text-lg font-medium text-foreground mb-4">Upload Guidelines</h3>
          <div className="grid md:grid-cols-2 gap-4 text-sm text-muted-foreground">
            <div>
              <h4 className="font-medium mb-2">For best results:</h4>
              <ul className="space-y-1">
                <li>• Ensure good lighting</li>
                <li>• Keep the check flat and straight</li>
                <li>• Include all edges of the check</li>
                <li>• Avoid shadows and glare</li>
              </ul>
            </div>
            <div>
              <h4 className="font-medium mb-2">Supported formats:</h4>
              <ul className="space-y-1">
                <li>• JPEG/JPG images</li>
                <li>• PNG images</li>
                <li>• PDF documents</li>
                <li>• Maximum 10MB file size</li>
              </ul>
            </div>
          </div>
        </div>
    </AppShell>
  );
}