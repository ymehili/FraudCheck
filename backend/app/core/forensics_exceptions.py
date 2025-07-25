"""
Custom exceptions for forensics analysis.

These exceptions follow the pattern established in SecurityValidationError
from utils/security_validation.py and provide clear error signaling for
forensics analysis failures.
"""

import logging

logger = logging.getLogger(__name__)


class ForensicsAnalysisError(Exception):
    """
    Exception raised when forensics analysis encounters unrecoverable error.
    
    This exception should be raised when analysis cannot proceed due to:
    - Invalid image data that cannot be processed
    - Critical algorithm failures
    - Resource constraints that prevent analysis completion
    
    When this exception is raised, the system should signal high risk (1.0)
    instead of returning 0.0 which masks the failure as "safe".
    """
    pass


class ForensicsWarning(Exception):
    """
    Exception raised for partial failures in forensics analysis.
    
    This exception should be raised when:
    - Some analysis components fail but others succeed
    - Analysis completes with reduced confidence
    - Non-critical errors that don't prevent overall assessment
    
    When this exception is raised, the system should:
    - Set analysis_status to "partial_failure"
    - Use available results with appropriate confidence reduction
    - Log warning details for investigation
    """
    pass


class ImageProcessingError(ForensicsAnalysisError):
    """
    Exception raised for image processing failures.
    
    Specific to image manipulation and processing errors such as:
    - Image format conversion failures
    - OpenCV processing errors
    - Memory issues with large images
    """
    pass


class FeatureDetectionError(ForensicsAnalysisError):
    """
    Exception raised for feature detection failures.
    
    Specific to computer vision feature detection issues such as:
    - AKAZE/SIFT detector failures
    - Keypoint matching errors
    - Geometric validation failures
    """
    pass


class CompressionAnalysisError(ForensicsAnalysisError):
    """
    Exception raised for compression analysis failures.
    
    Specific to compression artifact detection issues such as:
    - JPEG DCT analysis failures
    - ELA processing errors
    - Frequency domain analysis failures
    """
    pass