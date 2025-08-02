// File upload constants
export const SUPPORTED_FILE_TYPES = [
  'image/jpeg',
  'image/jpg',
  'image/png',
  'application/pdf',
] as const;

export const SUPPORTED_IMAGE_TYPES = [
  'image/jpeg',
  'image/jpg',
  'image/png',
] as const;

export const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB
export const MAX_IMAGE_SIZE = 5 * 1024 * 1024; // 5MB

export const FILE_UPLOAD_ACCEPT = '.jpg,.jpeg,.png,.pdf';
export const IMAGE_UPLOAD_ACCEPT = '.jpg,.jpeg,.png';

// Risk score constants
export const RISK_THRESHOLDS = {
  LOW: 30,
  MEDIUM: 60,
  HIGH: 80,
  CRITICAL: 90,
} as const;

export const RISK_COLORS = {
  LOW: 'green',
  MEDIUM: 'yellow',
  HIGH: 'orange',
  CRITICAL: 'red',
} as const;

// API endpoint constants
export const API_ENDPOINTS = {
  AUTH: {
    ME: '/api/v1/auth/me',
    VALIDATE: '/api/v1/auth/validate',
  },
  FILES: {
    UPLOAD: '/api/v1/files/upload',
    GET: '/api/v1/files',
    DELETE: '/api/v1/files',
  },
  ANALYZE: {
    FILE: '/api/v1/analyze/file',
    RESULTS: '/api/v1/analyze/results',
    HISTORY: '/api/v1/analyze/history',
  },
  DASHBOARD: {
    STATS: '/api/v1/dashboard/stats',
  },
  SCORING: {
    BASE: '/api/v1/scoring',
    THRESHOLDS: '/api/v1/scoring/thresholds',
  },
} as const;

// Pagination constants
export const PAGINATION = {
  DEFAULT_PAGE_SIZE: 20,
  MAX_PAGE_SIZE: 100,
  MIN_PAGE_SIZE: 5,
} as const;

// Analysis constants
export const ANALYSIS_STATUS = {
  PENDING: 'pending',
  PROCESSING: 'processing',
  COMPLETED: 'completed',
  FAILED: 'failed',
} as const;

export const ANALYSIS_TYPES = {
  FULL: 'full',
  QUICK: 'quick',
  FORENSICS_ONLY: 'forensics_only',
  OCR_ONLY: 'ocr_only',
} as const;

// UI constants
export const BREAKPOINTS = {
  SM: 640,
  MD: 768,
  LG: 1024,
  XL: 1280,
  '2XL': 1536,
} as const;

export const ANIMATION_DURATION = {
  FAST: 150,
  DEFAULT: 300,
  SLOW: 500,
} as const;

// Camera capture constants
export const CAMERA_CONSTRAINTS = {
  DEFAULT: {
    width: 1280,
    height: 720,
    facingMode: 'environment', // Use rear camera on mobile
  },
  HIGH_RES: {
    width: 1920,
    height: 1080,
    facingMode: 'environment',
  },
  MOBILE_OPTIMIZED: {
    width: { ideal: 1280, max: 1920 },
    height: { ideal: 720, max: 1080 },
    facingMode: { exact: 'environment' },
  },
} as const;

// Error messages
export const ERROR_MESSAGES = {
  FILE_TOO_LARGE: 'File size exceeds the maximum allowed limit',
  INVALID_FILE_TYPE: 'File type is not supported',
  UPLOAD_FAILED: 'Failed to upload file. Please try again.',
  ANALYSIS_FAILED: 'Analysis failed. Please try again.',
  NETWORK_ERROR: 'Network error. Please check your connection.',
  UNAUTHORIZED: 'You are not authorized to perform this action',
  SERVER_ERROR: 'Server error. Please try again later.',
  CAMERA_PERMISSION: 'Camera permission is required to capture images',
  CAMERA_NOT_SUPPORTED: 'Camera is not supported on this device',
} as const;

// Success messages
export const SUCCESS_MESSAGES = {
  FILE_UPLOADED: 'File uploaded successfully',
  ANALYSIS_COMPLETED: 'Analysis completed successfully',
  ANALYSIS_STARTED: 'Analysis started. Results will be available shortly.',
  FILE_DELETED: 'File deleted successfully',
  SETTINGS_SAVED: 'Settings saved successfully',
} as const;

// Local storage keys
export const STORAGE_KEYS = {
  USER_PREFERENCES: 'checkguard_user_preferences',
  RECENT_ANALYSES: 'checkguard_recent_analyses',
  DASHBOARD_FILTERS: 'checkguard_dashboard_filters',
  THEME: 'checkguard_theme',
} as const;

// Route constants
export const ROUTES = {
  HOME: '/',
  DASHBOARD: '/dashboard',
  UPLOAD: '/upload',
  ANALYSIS: '/analysis',
  HISTORY: '/history',
  SETTINGS: '/settings',
  PROFILE: '/profile',
} as const;

// Chart colors for data visualization
export const CHART_COLORS = {
  PRIMARY: '#3b82f6', // blue-500
  SUCCESS: '#10b981', // green-500
  WARNING: '#f59e0b', // yellow-500
  DANGER: '#ef4444', // red-500
  INFO: '#6366f1', // indigo-500
  SECONDARY: '#6b7280', // gray-500
} as const;

// Date format constants
export const DATE_FORMATS = {
  SHORT: 'MMM d, yyyy',
  LONG: 'MMMM d, yyyy',
  WITH_TIME: 'MMM d, yyyy h:mm a',
  ISO: 'yyyy-MM-dd',
  TIME_ONLY: 'h:mm a',
} as const;

// Feature flags (for progressive rollout)
export const FEATURES = {
  PDF_REPORTS: true,
  CAMERA_CAPTURE: true,
  REAL_TIME_ANALYSIS: true,
  ADVANCED_FILTERS: true,
  BULK_UPLOAD: false, // Coming soon
  MOBILE_APP: false, // Coming soon
} as const;