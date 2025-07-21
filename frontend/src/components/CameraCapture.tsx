'use client';

import { useRef, useState, useCallback } from 'react';
import Webcam from 'react-webcam';
import { Camera, RotateCcw, Check, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { cn } from '@/lib/utils';
import { CAMERA_CONSTRAINTS, ERROR_MESSAGES } from '@/lib/constants';

interface CameraCaptureProps {
  onCapture: (file: File) => void;
  className?: string;
  disabled?: boolean;
}

export function CameraCapture({ onCapture, className, disabled }: CameraCaptureProps) {
  const webcamRef = useRef<Webcam>(null);
  const [capturedImage, setCapturedImage] = useState<string | null>(null);
  const [isReady, setIsReady] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [facingMode, setFacingMode] = useState<'user' | 'environment'>('environment');

  // Convert base64 to File object
  const dataURLtoFile = useCallback((dataurl: string, filename: string): File => {
    const arr = dataurl.split(',');
    const mimeMatch = arr[0].match(/:(.*?);/);
    const mime = mimeMatch ? mimeMatch[1] : 'image/jpeg';
    const bstr = atob(arr[1]);
    let n = bstr.length;
    const u8arr = new Uint8Array(n);
    while (n--) {
      u8arr[n] = bstr.charCodeAt(n);
    }
    return new File([u8arr], filename, { type: mime });
  }, []);

  // Handle camera capture
  const capturePhoto = useCallback(() => {
    try {
      const imageSrc = webcamRef.current?.getScreenshot();
      if (imageSrc) {
        setCapturedImage(imageSrc);
        setError(null);
      }
    } catch (error) {
      console.error('Camera capture failed:', error);
      setError(ERROR_MESSAGES.CAMERA_NOT_SUPPORTED);
    }
  }, []);

  // Confirm captured image
  const confirmCapture = useCallback(() => {
    if (capturedImage) {
      const file = dataURLtoFile(capturedImage, `camera-capture-${Date.now()}.jpg`);
      onCapture(file);
      setCapturedImage(null);
    }
  }, [capturedImage, dataURLtoFile, onCapture]);

  // Retake photo
  const retakePhoto = useCallback(() => {
    setCapturedImage(null);
    setError(null);
  }, []);

  // Toggle camera (front/back)
  const toggleCamera = useCallback(() => {
    setFacingMode(current => current === 'user' ? 'environment' : 'user');
  }, []);

  // Handle camera ready
  const handleCameraReady = useCallback(() => {
    setIsReady(true);
    setError(null);
  }, []);

  // Handle camera error
  const handleCameraError = useCallback((error: string | DOMException) => {
    console.error('Camera error:', error);
    if (typeof error === 'string') {
      setError(error);
    } else if (error.name === 'NotAllowedError') {
      setError(ERROR_MESSAGES.CAMERA_PERMISSION);
    } else if (error.name === 'NotFoundError' || error.name === 'DevicesNotFoundError') {
      setError(ERROR_MESSAGES.CAMERA_NOT_SUPPORTED);
    } else {
      setError(ERROR_MESSAGES.CAMERA_NOT_SUPPORTED);
    }
    setIsReady(false);
  }, []);

  const videoConstraints = {
    ...CAMERA_CONSTRAINTS.MOBILE_OPTIMIZED,
    facingMode: { exact: facingMode },
  };

  if (disabled) {
    return (
      <Card className={cn('w-full max-w-lg mx-auto', className)}>
        <CardContent className="flex flex-col items-center justify-center p-6 text-center">
          <Camera className="h-12 w-12 text-gray-400 mb-4" />
          <p className="text-gray-500">Camera capture is disabled</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className={cn('w-full max-w-lg mx-auto', className)}>
      <Card>
        <CardContent className="p-6">
          {error && (
            <Alert variant="destructive" className="mb-4">
              <X className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          <div className="relative aspect-video bg-gray-100 rounded-lg overflow-hidden">
            {capturedImage ? (
              // Show captured image
              <img
                src={capturedImage}
                alt="Captured check"
                className="w-full h-full object-cover"
              />
            ) : (
              // Show camera feed
              <Webcam
                ref={webcamRef}
                audio={false}
                screenshotFormat="image/jpeg"
                screenshotQuality={0.9}
                videoConstraints={videoConstraints}
                onUserMedia={handleCameraReady}
                onUserMediaError={handleCameraError}
                className="w-full h-full object-cover"
                style={{ transform: facingMode === 'user' ? 'scaleX(-1)' : 'none' }}
              />
            )}

            {/* Camera overlay guide */}
            {!capturedImage && isReady && (
              <div className="absolute inset-4 border-2 border-white border-dashed rounded-lg flex items-center justify-center">
                <div className="bg-black bg-opacity-50 text-white px-3 py-1 rounded text-sm">
                  Position check within frame
                </div>
              </div>
            )}

            {/* Loading overlay */}
            {!isReady && !error && !capturedImage && (
              <div className="absolute inset-0 flex items-center justify-center bg-gray-100">
                <div className="text-center">
                  <Camera className="h-12 w-12 text-gray-400 mx-auto mb-2 animate-pulse" />
                  <p className="text-gray-500">Initializing camera...</p>
                </div>
              </div>
            )}
          </div>

          {/* Camera controls */}
          <div className="flex justify-center items-center space-x-4 mt-4">
            {capturedImage ? (
              // Captured image controls
              <>
                <Button
                  variant="outline"
                  onClick={retakePhoto}
                  className="flex items-center space-x-2"
                >
                  <RotateCcw className="h-4 w-4" />
                  <span>Retake</span>
                </Button>
                <Button
                  onClick={confirmCapture}
                  className="flex items-center space-x-2"
                >
                  <Check className="h-4 w-4" />
                  <span>Use Photo</span>
                </Button>
              </>
            ) : (
              // Camera controls
              <>
                <Button
                  variant="outline"
                  onClick={toggleCamera}
                  disabled={!isReady}
                  size="sm"
                >
                  <RotateCcw className="h-4 w-4" />
                </Button>
                <Button
                  onClick={capturePhoto}
                  disabled={!isReady}
                  size="lg"
                  className="px-8"
                >
                  <Camera className="h-5 w-5 mr-2" />
                  Capture
                </Button>
              </>
            )}
          </div>

          {/* Instructions */}
          <div className="mt-4 text-sm text-gray-600 text-center">
            {capturedImage ? (
              <p>Review your photo and confirm to proceed, or retake if needed.</p>
            ) : isReady ? (
              <div>
                <p>Position the check within the frame and tap capture.</p>
                <p className="mt-1">Use the flip button to switch between front and rear cameras.</p>
              </div>
            ) : !error ? (
              <p>Please allow camera access to capture check images.</p>
            ) : null}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}