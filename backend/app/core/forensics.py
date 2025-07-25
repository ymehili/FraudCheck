import cv2
import numpy as np
import os
import asyncio
import warnings
from typing import Dict, List, Any
import logging

from ..schemas.analysis import ForensicsResult, AnalysisStatusEnum
from .executor_manager import get_forensics_executor
from .forensics_worker import (
    detect_edge_inconsistencies_worker,
    analyze_compression_artifacts_worker,
    analyze_font_consistency_worker
)
from .forensics_exceptions import (
    ForensicsAnalysisError,
    ForensicsWarning,
    ImageProcessingError,
    FeatureDetectionError,
    CompressionAnalysisError
)

# Suppress numpy warnings for division by zero and invalid values
warnings.filterwarnings('ignore', category=RuntimeWarning, module='numpy')

logger = logging.getLogger(__name__)


class ForensicsEngine:
    """
    Image forensics engine for check fraud detection.
    
    Analyzes images for:
    - Edge inconsistencies
    - Compression artifacts
    - Font and text consistency
    - Image tampering indicators
    """
    
    def __init__(self):
        self.edge_threshold_low = 50
        self.edge_threshold_high = 150
        self.compression_block_size = 8
        self.font_analysis_regions = []
        
    async def analyze_image(self, image_path: str) -> ForensicsResult:
        """
        Perform comprehensive forensics analysis on an image.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            ForensicsResult with detailed analysis results
        """
        try:
            # Validate input
            if not os.path.exists(image_path):
                raise FileNotFoundError(f"Image not found: {image_path}")
            
            # Load image
            image = cv2.imread(image_path)
            if image is None:
                raise ValueError(f"Could not load image: {image_path}")
            
            # Convert BGR to RGB for consistent processing
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            # Check image size and resize if too large (optimization for hanging)
            height, width = image_rgb.shape[:2]
            max_dimension = 2048  # Limit to 2K resolution for performance
            
            if max(height, width) > max_dimension:
                logger.info(f"Resizing large image from {width}x{height} for performance")
                scale_factor = max_dimension / max(height, width)
                new_width = int(width * scale_factor)
                new_height = int(height * scale_factor)
                image_rgb = cv2.resize(image_rgb, (new_width, new_height), interpolation=cv2.INTER_AREA)
            
            # Run analysis components in parallel
            tasks = [
                self._detect_edge_inconsistencies(image_rgb),
                self._analyze_compression_artifacts(image_rgb),
                self._analyze_font_consistency(image_rgb)
            ]
            
            edge_analysis, compression_analysis, font_analysis = await asyncio.gather(*tasks)
            
            # Calculate overall scores
            edge_score = edge_analysis.get('score', 0.0)
            compression_score = compression_analysis.get('score', 0.0)
            font_score = font_analysis.get('score', 0.0)
            
            # Calculate overall forensics score (weighted average)
            overall_score = (edge_score * 0.4 + compression_score * 0.3 + font_score * 0.3)
            
            # Compile detected anomalies
            anomalies = self._compile_anomalies(edge_analysis, compression_analysis, font_analysis)
            
            # Extract enhanced forensics data
            ela_analysis = compression_analysis.get('ela_analysis')
            copy_move_regions = edge_analysis.get('cloned_regions', {}).get('copy_move_regions', [])
            noise_analysis = edge_analysis.get('noise_analysis')
            
            # Cleanup resources
            del image, image_rgb
            
            return ForensicsResult(
                edge_score=edge_score,
                compression_score=compression_score,
                font_score=font_score,
                overall_score=overall_score,
                detected_anomalies=anomalies,
                edge_inconsistencies=edge_analysis,
                compression_artifacts=compression_analysis,
                font_analysis=font_analysis,
                analysis_status=AnalysisStatusEnum.SUCCESS,
                error_details=None,
                ela_analysis=ela_analysis,
                copy_move_regions=copy_move_regions,
                noise_analysis=noise_analysis
            )
            
        except (ForensicsAnalysisError, CompressionAnalysisError, ImageProcessingError, 
                FeatureDetectionError) as e:
            logger.error(f"Forensics analysis failed for {image_path}: {str(e)}")
            
            # Return high-risk result for critical failures instead of masking as safe
            return ForensicsResult(
                edge_score=1.0,
                compression_score=1.0,
                font_score=1.0,
                overall_score=1.0,  # Maximum risk for failures
                detected_anomalies=["Critical analysis failure - high risk"],
                edge_inconsistencies={"error": "Analysis failed"},
                compression_artifacts={"error": "Analysis failed"},
                font_analysis={"error": "Analysis failed"},
                analysis_status=AnalysisStatusEnum.CRITICAL_FAILURE,
                error_details=str(e),
                ela_analysis=None,
                copy_move_regions=None,
                noise_analysis=None
            )
            
        except ForensicsWarning as e:
            logger.warning(f"Forensics analysis completed with warnings for {image_path}: {str(e)}")
            
            # Attempt to get partial results with reduced confidence
            try:
                # Re-load image for partial recovery attempt
                image = cv2.imread(image_path)
                if image is None:
                    raise ValueError(f"Could not load image: {image_path}")
                image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                
                edge_analysis, compression_analysis, font_analysis = await asyncio.gather(
                    self._detect_edge_inconsistencies(image_rgb),
                    self._analyze_compression_artifacts(image_rgb),
                    self._analyze_font_consistency(image_rgb),
                    return_exceptions=True
                )
                
                # Use available results, with penalties for failed components
                edge_score = edge_analysis.get('score', 0.8) if isinstance(edge_analysis, dict) else 0.8
                compression_score = compression_analysis.get('score', 0.8) if isinstance(compression_analysis, dict) else 0.8
                font_score = font_analysis.get('score', 0.8) if isinstance(font_analysis, dict) else 0.8
                
                overall_score = max(0.7, (edge_score + compression_score + font_score) / 3.0)
                anomalies = ["Partial analysis failure - elevated risk"]
                
                return ForensicsResult(
                    edge_score=edge_score,
                    compression_score=compression_score,
                    font_score=font_score,
                    overall_score=overall_score,
                    detected_anomalies=anomalies,
                    edge_inconsistencies=edge_analysis if isinstance(edge_analysis, dict) else {"error": "Failed"},
                    compression_artifacts=compression_analysis if isinstance(compression_analysis, dict) else {"error": "Failed"},
                    font_analysis=font_analysis if isinstance(font_analysis, dict) else {"error": "Failed"},
                    analysis_status=AnalysisStatusEnum.PARTIAL_FAILURE,
                    error_details=str(e),
                    ela_analysis=compression_analysis.get('ela_analysis') if isinstance(compression_analysis, dict) else None,
                    copy_move_regions=edge_analysis.get('cloned_regions', {}).get('copy_move_regions', []) if isinstance(edge_analysis, dict) else None,
                    noise_analysis=edge_analysis.get('noise_analysis') if isinstance(edge_analysis, dict) else None
                )
                
            except Exception:
                # If partial recovery fails, return critical failure
                return ForensicsResult(
                    edge_score=1.0,
                    compression_score=1.0,
                    font_score=1.0,
                    overall_score=1.0,
                    detected_anomalies=["Critical analysis failure - high risk"],
                    edge_inconsistencies={"error": "Analysis failed"},
                    compression_artifacts={"error": "Analysis failed"},
                    font_analysis={"error": "Analysis failed"},
                    analysis_status=AnalysisStatusEnum.CRITICAL_FAILURE,
                    error_details=str(e),
                    ela_analysis=None,
                    copy_move_regions=None,
                    noise_analysis=None
                )
                
        except Exception as e:
            logger.error(f"Unexpected error in forensics analysis for {image_path}: {str(e)}")
            
            # Return high-risk result for unexpected failures
            return ForensicsResult(
                edge_score=1.0,
                compression_score=1.0,
                font_score=1.0,
                overall_score=1.0,
                detected_anomalies=["Unexpected analysis failure - high risk"],
                edge_inconsistencies={"error": "Unexpected failure"},
                compression_artifacts={"error": "Unexpected failure"},
                font_analysis={"error": "Unexpected failure"},
                analysis_status=AnalysisStatusEnum.CRITICAL_FAILURE,
                error_details=f"Unexpected error: {str(e)}",
                ela_analysis=None,
                copy_move_regions=None,
                noise_analysis=None
            )
    
    async def _detect_edge_inconsistencies(self, image: np.ndarray) -> Dict[str, Any]:
        """
        Detect edge inconsistencies that might indicate tampering.
        
        Args:
            image: RGB image array
            
        Returns:
            Dictionary with edge analysis results
        """
        try:
            loop = asyncio.get_running_loop()
            executor = get_forensics_executor()
            
            # CRITICAL: Convert image to bytes for process communication
            image_bytes = image.tobytes()
            image_shape = image.shape
            
            # PATTERN: Use run_in_executor with worker function
            result = await loop.run_in_executor(
                executor,
                detect_edge_inconsistencies_worker,
                image_bytes,
                image_shape
            )
            
            return result
            
        except (ForensicsAnalysisError, ImageProcessingError, FeatureDetectionError) as e:
            logger.error(f"Edge detection failed: {str(e)}")
            raise ForensicsAnalysisError(f"Edge detection critical failure: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error in edge detection: {str(e)}")
            raise ForensicsAnalysisError(f"Edge detection unexpected error: {str(e)}")
    
    async def _analyze_compression_artifacts(self, image: np.ndarray) -> Dict[str, Any]:
        """
        Analyze compression artifacts that might indicate tampering.
        
        Args:
            image: RGB image array
            
        Returns:
            Dictionary with compression analysis results
        """
        try:
            loop = asyncio.get_running_loop()
            executor = get_forensics_executor()
            
            # CRITICAL: Convert image to bytes for process communication
            image_bytes = image.tobytes()
            image_shape = image.shape
            
            # PATTERN: Use run_in_executor with worker function
            result = await loop.run_in_executor(
                executor,
                analyze_compression_artifacts_worker,
                image_bytes,
                image_shape
            )
            
            return result
            
        except (CompressionAnalysisError, ImageProcessingError) as e:
            logger.error(f"Compression analysis failed: {str(e)}")
            raise CompressionAnalysisError(f"Compression analysis critical failure: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error in compression analysis: {str(e)}")
            raise CompressionAnalysisError(f"Compression analysis unexpected error: {str(e)}")
    
    async def _analyze_font_consistency(self, image: np.ndarray) -> Dict[str, Any]:
        """
        Analyze font and text consistency for potential tampering.
        
        Args:
            image: RGB image array
            
        Returns:
            Dictionary with font analysis results
        """
        try:
            loop = asyncio.get_running_loop()
            executor = get_forensics_executor()
            
            # CRITICAL: Convert image to bytes for process communication
            image_bytes = image.tobytes()
            image_shape = image.shape
            
            # PATTERN: Use run_in_executor with worker function
            result = await loop.run_in_executor(
                executor,
                analyze_font_consistency_worker,
                image_bytes,
                image_shape
            )
            
            return result
            
        except ForensicsAnalysisError as e:
            logger.error(f"Font analysis failed: {str(e)}")
            raise ForensicsAnalysisError(f"Font analysis critical failure: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error in font analysis: {str(e)}")
            raise ForensicsAnalysisError(f"Font analysis unexpected error: {str(e)}")
    
    
    def _compile_anomalies(self, edge_analysis: Dict[str, Any], 
                          compression_analysis: Dict[str, Any], 
                          font_analysis: Dict[str, Any]) -> List[str]:
        """Compile detected anomalies into a list."""
        anomalies = []
        
        # Edge anomalies
        if edge_analysis.get('score', 0.0) < 0.3:
            anomalies.append('Poor edge continuity detected')
        
        # Compression anomalies
        if compression_analysis.get('score', 0.0) > 0.7:
            anomalies.append('High compression artifacts detected')
        
        # Font anomalies
        font_inconsistencies = font_analysis.get('inconsistencies', {}).get('inconsistencies', [])
        anomalies.extend(font_inconsistencies)
        
        # Cloning detection
        cloned_regions = edge_analysis.get('cloned_regions', {})
        if cloned_regions.get('score', 0.0) > 0.5:
            anomalies.append('Potential cloned regions detected')
        
        return anomalies