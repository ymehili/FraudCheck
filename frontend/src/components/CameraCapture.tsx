"use client";

import { useRef, useState, useCallback } from 'react';
import Webcam from 'react-webcam';

interface CameraCaptureProps {
  onCapture: (imageFile: File) => void;
  onError?: (error: string) => void;
}

const CameraCapture: React.FC<CameraCaptureProps> = ({ onCapture, onError }) => {
  const webcamRef = useRef<Webcam>(null);
  const [isCameraActive, setIsCameraActive] = useState(false);
  const [capturedImage, setCapturedImage] = useState<string | null>(null);
  const [isCapturing, setIsCapturing] = useState(false);

  // Mobile-friendly camera constraints
  const videoConstraints = {
    width: 1280,
    height: 720,
    facingMode: "environment" // Use rear camera on mobile
  };

  const startCamera = useCallback(() => {
    setIsCameraActive(true);
    setCapturedImage(null);
  }, []);

  const stopCamera = useCallback(() => {
    setIsCameraActive(false);
  }, []);

  const dataURLtoFile = (dataurl: string, filename: string): File => {
    const arr = dataurl.split(',');
    const mime = arr[0].match(/:(.*?);/)?.[1] || 'image/jpeg';
    const bstr = atob(arr[1]);
    let n = bstr.length;
    const u8arr = new Uint8Array(n);
    while (n--) {
      u8arr[n] = bstr.charCodeAt(n);
    }
    return new File([u8arr], filename, { type: mime });
  };

  const capture = useCallback(() => {
    if (!webcamRef.current) {
      onError?.("Camera not available");
      return;
    }

    setIsCapturing(true);
    
    try {
      const imageSrc = webcamRef.current.getScreenshot();
      if (imageSrc) {
        setCapturedImage(imageSrc);
        
        // Convert base64 to File
        const file = dataURLtoFile(imageSrc, `check-${Date.now()}.jpg`);
        onCapture(file);
      } else {
        onError?.("Failed to capture image");
      }
    } catch (error) {
      onError?.(`Error capturing image: ${error instanceof Error ? error.message : 'Unknown error'}`);
    } finally {
      setIsCapturing(false);
    }
  }, [onCapture, onError]);

  const retakePhoto = useCallback(() => {
    setCapturedImage(null);
  }, []);

  const handleUserMediaError = useCallback((error: string | DOMException) => {
    console.error('Camera error:', error);
    onError?.(`Failed to access camera: ${error.toString()}. Please ensure camera permissions are granted.`);
    setIsCameraActive(false);
  }, [onError]);

  if (!isCameraActive) {
    return (
      <div className="flex flex-col items-center justify-center p-8 bg-gray-50 rounded-lg border-2 border-dashed border-gray-300">
        <div className="text-center">
          <svg
            className="mx-auto h-12 w-12 text-gray-400"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 48 48"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M28 8H12a4 4 0 00-4 4v20m32-12v8m0 0v8a4 4 0 01-4 4H12a4 4 0 01-4-4v-4m32-4l-3.172-3.172a4 4 0 00-5.656 0L28 28M8 32l9.172-9.172a4 4 0 015.656 0L28 28m0 0l4 4m4-24h8m-4-4v8m-12 4h.02"
            />
          </svg>
          <h3 className="mt-2 text-sm font-medium text-gray-900">Camera Capture</h3>
          <p className="mt-1 text-sm text-gray-500">
            Use your camera to capture a check image
          </p>
        </div>
        <button
          onClick={startCamera}
          className="mt-4 inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
        >
          <svg className="mr-2 h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z" />
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 13a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
          Start Camera
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="relative bg-black rounded-lg overflow-hidden">
        {capturedImage ? (
          <img
            src={capturedImage}
            alt="Captured check"
            className="w-full h-auto max-h-96 object-contain"
          />
        ) : (
          <Webcam
            ref={webcamRef}
            audio={false}
            height={720}
            width={1280}
            screenshotFormat="image/jpeg"
            videoConstraints={videoConstraints}
            onUserMediaError={handleUserMediaError}
            className="w-full h-auto max-h-96 object-contain"
          />
        )}
        
        {/* Camera overlay for check positioning */}
        {!capturedImage && (
          <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
            <div className="border-2 border-white border-dashed rounded-lg w-3/4 h-3/4 flex items-center justify-center">
              <div className="text-white text-center">
                <p className="text-sm">Position check within frame</p>
              </div>
            </div>
          </div>
        )}
      </div>

      <div className="flex justify-center space-x-4">
        {capturedImage ? (
          <>
            <button
              onClick={retakePhoto}
              className="inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
            >
              <svg className="mr-2 h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              Retake
            </button>
            <button
              onClick={stopCamera}
              className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500"
            >
              <svg className="mr-2 h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
              Use This Photo
            </button>
          </>
        ) : (
          <>
            <button
              onClick={capture}
              disabled={isCapturing}
              className="inline-flex items-center px-6 py-3 border border-transparent text-base font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isCapturing ? (
                <svg className="animate-spin mr-2 h-5 w-5" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
              ) : (
                <svg className="mr-2 h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 13a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
              )}
              {isCapturing ? 'Capturing...' : 'Capture Photo'}
            </button>
            <button
              onClick={stopCamera}
              className="inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
            >
              Cancel
            </button>
          </>
        )}
      </div>
    </div>
  );
};

export default CameraCapture;