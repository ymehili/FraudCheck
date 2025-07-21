import cv2
import numpy as np
import os
import asyncio
import warnings
from typing import Dict, List, Any
from skimage import feature, measure
from skimage.color import rgb2gray
import logging

# Suppress numpy warnings for division by zero and invalid values
warnings.filterwarnings('ignore', category=RuntimeWarning, module='numpy')

from ..schemas.analysis import ForensicsResult

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
                font_analysis=font_analysis
            )
            
        except Exception as e:
            logger.error(f"Forensics analysis failed for {image_path}: {str(e)}")
            raise
    
    async def _detect_edge_inconsistencies(self, image: np.ndarray) -> Dict[str, Any]:
        """
        Detect edge inconsistencies that might indicate tampering.
        
        Args:
            image: RGB image array
            
        Returns:
            Dictionary with edge analysis results
        """
        try:
            # Convert to grayscale for edge detection
            gray = rgb2gray(image)
            
            # Apply Canny edge detection
            edges = feature.canny(gray, sigma=1.0, low_threshold=0.1, high_threshold=0.2)
            
            # Analyze edge continuity
            edge_continuity = self._analyze_edge_continuity(edges)
            
            # Detect edge sharpness variations
            edge_sharpness = self._analyze_edge_sharpness(gray)
            
            # Check for duplicate or cloned regions
            cloned_regions = self._detect_cloned_regions(gray)
            
            # Calculate edge inconsistency score
            continuity_score = edge_continuity.get('score', 0.0)
            sharpness_score = edge_sharpness.get('score', 0.0)
            cloning_score = cloned_regions.get('score', 0.0)
            
            edge_score = (continuity_score + sharpness_score + cloning_score) / 3.0
            
            return {
                'score': edge_score,
                'continuity': edge_continuity,
                'sharpness': edge_sharpness,
                'cloned_regions': cloned_regions,
                'edge_density': float(np.sum(edges) / edges.size),
                'edge_map_shape': edges.shape
            }
            
        except Exception as e:
            logger.error(f"Edge detection failed: {str(e)}")
            return {'score': 0.0, 'error': str(e)}
    
    async def _analyze_compression_artifacts(self, image: np.ndarray) -> Dict[str, Any]:
        """
        Analyze compression artifacts that might indicate tampering.
        
        Args:
            image: RGB image array
            
        Returns:
            Dictionary with compression analysis results
        """
        try:
            # Convert to grayscale
            gray = rgb2gray(image)
            
            # Analyze JPEG compression artifacts
            jpeg_artifacts = self._detect_jpeg_artifacts(gray)
            
            # Analyze compression inconsistencies
            compression_inconsistencies = self._detect_compression_inconsistencies(image)
            
            # Check for re-compression patterns
            recompression_patterns = self._detect_recompression_patterns(gray)
            
            # Calculate compression artifact score
            jpeg_score = jpeg_artifacts.get('score', 0.0)
            inconsistency_score = compression_inconsistencies.get('score', 0.0)
            recompression_score = recompression_patterns.get('score', 0.0)
            
            compression_score = (jpeg_score + inconsistency_score + recompression_score) / 3.0
            
            return {
                'score': compression_score,
                'jpeg_artifacts': jpeg_artifacts,
                'inconsistencies': compression_inconsistencies,
                'recompression_patterns': recompression_patterns,
                'block_artifacts': self._analyze_block_artifacts(gray)
            }
            
        except Exception as e:
            logger.error(f"Compression analysis failed: {str(e)}")
            return {'score': 0.0, 'error': str(e)}
    
    async def _analyze_font_consistency(self, image: np.ndarray) -> Dict[str, Any]:
        """
        Analyze font and text consistency for potential tampering.
        
        Args:
            image: RGB image array
            
        Returns:
            Dictionary with font analysis results
        """
        try:
            # Convert to grayscale
            gray = rgb2gray(image)
            
            # Detect text regions
            text_regions = self._detect_text_regions(gray)
            
            # Analyze font characteristics
            font_characteristics = self._analyze_font_characteristics(gray, text_regions)
            
            # Check for font inconsistencies
            font_inconsistencies = self._detect_font_inconsistencies(font_characteristics)
            
            # Analyze text alignment and spacing
            text_alignment = self._analyze_text_alignment(gray, text_regions)
            
            # Calculate font consistency score
            char_score = font_characteristics.get('consistency_score', 0.0)
            alignment_score = text_alignment.get('score', 0.0)
            inconsistency_penalty = font_inconsistencies.get('penalty', 0.0)
            
            font_score = max(0.0, (char_score + alignment_score) / 2.0 - inconsistency_penalty)
            
            return {
                'score': font_score,
                'text_regions': text_regions,
                'font_characteristics': font_characteristics,
                'inconsistencies': font_inconsistencies,
                'alignment_analysis': text_alignment
            }
            
        except Exception as e:
            logger.error(f"Font analysis failed: {str(e)}")
            return {'score': 0.0, 'error': str(e)}
    
    def _analyze_edge_continuity(self, edges: np.ndarray) -> Dict[str, Any]:
        """Analyze edge continuity for potential tampering indicators."""
        try:
            # Find connected components in edges
            labeled_edges = measure.label(edges)
            regions = measure.regionprops(labeled_edges)
            
            # Calculate edge continuity metrics
            total_regions = len(regions)
            avg_region_size = np.mean([region.area for region in regions]) if regions else 0
            
            # Detect broken edges that might indicate tampering
            broken_edges = sum(1 for region in regions if region.area < 10)
            
            # Calculate continuity score
            continuity_ratio = 1.0 - (broken_edges / max(total_regions, 1))
            
            return {
                'score': continuity_ratio,
                'total_regions': total_regions,
                'avg_region_size': float(avg_region_size),
                'broken_edges': broken_edges,
                'continuity_ratio': continuity_ratio
            }
            
        except Exception as e:
            logger.error(f"Edge continuity analysis failed: {str(e)}")
            return {'score': 0.0, 'error': str(e)}
    
    def _analyze_edge_sharpness(self, gray: np.ndarray) -> Dict[str, Any]:
        """Analyze edge sharpness variations."""
        try:
            # Apply Laplacian filter to detect sharpness
            laplacian = cv2.Laplacian(gray, cv2.CV_64F)
            sharpness_variance = np.var(laplacian)
            
            # Normalize sharpness score
            sharpness_score = min(1.0, sharpness_variance / 1000.0)
            
            return {
                'score': sharpness_score,
                'variance': float(sharpness_variance),
                'mean_sharpness': float(np.mean(np.abs(laplacian)))
            }
            
        except Exception as e:
            logger.error(f"Edge sharpness analysis failed: {str(e)}")
            return {'score': 0.0, 'error': str(e)}
    
    def _detect_cloned_regions(self, gray: np.ndarray) -> Dict[str, Any]:
        """Detect potentially cloned or duplicated regions."""
        try:
            # Simple correlation-based cloning detection
            h, w = gray.shape
            
            # Skip expensive cloning detection for large images to prevent hanging
            if h * w > 1000000:  # More than 1MP
                logger.info("Skipping cloning detection for large image to prevent timeout")
                return {
                    'score': 0.0,
                    'high_correlations': 0,
                    'total_comparisons': 0,
                    'max_correlation': 0.0,
                    'regions': [],
                    'skipped': True
                }
            
            block_size = 32
            correlations = []
            
            # Sample blocks and compare (limited for performance)
            step_size = max(block_size, min(64, block_size * 2))  # Larger steps for performance
            for i in range(0, h - block_size, step_size):
                for j in range(0, w - block_size, step_size):
                    block = gray[i:i+block_size, j:j+block_size]
                    
                    # Compare with other blocks (limited for performance)
                    comparison_count = 0
                    max_comparisons_per_block = 10  # Limit comparisons per block
                    
                    for ii in range(i + block_size, h - block_size, step_size):
                        for jj in range(0, w - block_size, step_size):
                            if comparison_count >= max_comparisons_per_block:
                                break
                            other_block = gray[ii:ii+block_size, jj:jj+block_size]
                            correlation = np.corrcoef(block.flat, other_block.flat)[0, 1]
                            if not np.isnan(correlation):
                                correlations.append(correlation)
                            comparison_count += 1
                        if comparison_count >= max_comparisons_per_block:
                            break
            
            # High correlation might indicate cloning
            high_correlations = [c for c in correlations if c > 0.95]
            cloning_score = len(high_correlations) / max(len(correlations), 1)
            
            return {
                'score': cloning_score,
                'high_correlations': len(high_correlations),
                'total_comparisons': len(correlations),
                'max_correlation': float(max(correlations)) if correlations else 0.0
            }
            
        except Exception as e:
            logger.error(f"Cloning detection failed: {str(e)}")
            return {'score': 0.0, 'error': str(e)}
    
    def _detect_jpeg_artifacts(self, gray: np.ndarray) -> Dict[str, Any]:
        """Detect JPEG compression artifacts."""
        try:
            # Apply DCT to detect blocking artifacts
            h, w = gray.shape
            block_size = 8
            artifacts = []
            
            for i in range(0, h - block_size, block_size):
                for j in range(0, w - block_size, block_size):
                    block = gray[i:i+block_size, j:j+block_size]
                    
                    # Check for DCT coefficient quantization patterns
                    dct_block = cv2.dct(block.astype(np.float32))
                    
                    # Analyze high-frequency components
                    high_freq = dct_block[4:, 4:]
                    artifact_measure = np.std(high_freq)
                    artifacts.append(artifact_measure)
            
            # Calculate artifact score
            avg_artifact = np.mean(artifacts) if artifacts else 0.0
            artifact_score = min(1.0, avg_artifact / 10.0)
            
            return {
                'score': artifact_score,
                'avg_artifact_level': float(avg_artifact),
                'artifact_variance': float(np.var(artifacts)) if artifacts else 0.0,
                'blocks_analyzed': len(artifacts)
            }
            
        except Exception as e:
            logger.error(f"JPEG artifact detection failed: {str(e)}")
            return {'score': 0.0, 'error': str(e)}
    
    def _detect_compression_inconsistencies(self, image: np.ndarray) -> Dict[str, Any]:
        """Detect compression quality inconsistencies."""
        try:
            # Analyze compression quality across different regions
            h, w, _ = image.shape
            region_size = 64
            quality_measures = []
            
            for i in range(0, h - region_size, region_size):
                for j in range(0, w - region_size, region_size):
                    region = image[i:i+region_size, j:j+region_size]
                    
                    # Calculate local quality measure
                    gray_region = rgb2gray(region)
                    quality = np.var(gray_region)
                    quality_measures.append(quality)
            
            # Check for inconsistencies
            quality_std = np.std(quality_measures) if quality_measures else 0.0
            inconsistency_score = min(1.0, quality_std / 100.0)
            
            return {
                'score': inconsistency_score,
                'quality_variance': float(quality_std),
                'regions_analyzed': len(quality_measures),
                'avg_quality': float(np.mean(quality_measures)) if quality_measures else 0.0
            }
            
        except Exception as e:
            logger.error(f"Compression inconsistency detection failed: {str(e)}")
            return {'score': 0.0, 'error': str(e)}
    
    def _detect_recompression_patterns(self, gray: np.ndarray) -> Dict[str, Any]:
        """Detect patterns indicating multiple compression passes."""
        try:
            # Analyze frequency domain for recompression indicators
            f_transform = np.fft.fft2(gray)
            f_magnitude = np.abs(f_transform)
            
            # Look for periodic patterns that might indicate recompression
            h, w = f_magnitude.shape
            center_h, center_w = h // 2, w // 2
            
            # Analyze frequency distribution
            freq_profile = f_magnitude[center_h-20:center_h+20, center_w-20:center_w+20]
            recompression_indicator = np.std(freq_profile)
            
            recompression_score = min(1.0, recompression_indicator / 10000.0)
            
            return {
                'score': recompression_score,
                'frequency_std': float(recompression_indicator),
                'analysis_region_shape': freq_profile.shape
            }
            
        except Exception as e:
            logger.error(f"Recompression pattern detection failed: {str(e)}")
            return {'score': 0.0, 'error': str(e)}
    
    def _analyze_block_artifacts(self, gray: np.ndarray) -> Dict[str, Any]:
        """Analyze block-based compression artifacts."""
        try:
            # Detect blocking artifacts using gradient analysis
            grad_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
            grad_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
            
            # Calculate gradient magnitude
            grad_magnitude = np.sqrt(grad_x**2 + grad_y**2)
            
            # Analyze 8x8 block boundaries
            block_boundaries = []
            h, w = gray.shape
            
            for i in range(8, h, 8):
                boundary_strength = np.mean(grad_magnitude[i-1:i+1, :])
                block_boundaries.append(boundary_strength)
            
            for j in range(8, w, 8):
                boundary_strength = np.mean(grad_magnitude[:, j-1:j+1])
                block_boundaries.append(boundary_strength)
            
            # Calculate block artifact score
            avg_boundary_strength = np.mean(block_boundaries) if block_boundaries else 0.0
            block_artifact_score = min(1.0, avg_boundary_strength / 50.0)
            
            return {
                'score': block_artifact_score,
                'avg_boundary_strength': float(avg_boundary_strength),
                'boundaries_analyzed': len(block_boundaries)
            }
            
        except Exception as e:
            logger.error(f"Block artifact analysis failed: {str(e)}")
            return {'score': 0.0, 'error': str(e)}
    
    def _detect_text_regions(self, gray: np.ndarray) -> List[Dict[str, Any]]:
        """Detect text regions in the image."""
        try:
            # Apply morphological operations to detect text
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
            
            # Threshold the image
            _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # Apply morphological operations
            morph = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
            
            # Find contours
            contours, _ = cv2.findContours(morph, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # Filter contours that might be text
            text_regions = []
            for contour in contours:
                area = cv2.contourArea(contour)
                if area > 50:  # Minimum area for text
                    x, y, w, h = cv2.boundingRect(contour)
                    aspect_ratio = w / float(h)
                    
                    # Text typically has certain aspect ratio constraints
                    if 0.1 < aspect_ratio < 10.0:
                        text_regions.append({
                            'bbox': [int(x), int(y), int(w), int(h)],
                            'area': float(area),
                            'aspect_ratio': float(aspect_ratio)
                        })
            
            return text_regions
            
        except Exception as e:
            logger.error(f"Text region detection failed: {str(e)}")
            return []
    
    def _analyze_font_characteristics(self, gray: np.ndarray, text_regions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze font characteristics in detected text regions."""
        try:
            if not text_regions:
                return {'consistency_score': 0.0, 'characteristics': []}
            
            characteristics: List[Dict[str, Any]] = []
            
            for region in text_regions:
                x, y, w, h = region['bbox']
                
                # Extract text region
                text_roi = gray[y:y+h, x:x+w]
                
                # Analyze font characteristics
                char_analysis = {
                    'region_id': len(characteristics),
                    'stroke_width': self._estimate_stroke_width(text_roi),
                    'text_density': float(np.mean(text_roi < 0.5)),
                    'uniformity': float(np.std(text_roi)),
                    'bbox': region['bbox']
                }
                
                characteristics.append(char_analysis)
            
            # Calculate consistency score
            if len(characteristics) > 1:
                stroke_widths = [c['stroke_width'] for c in characteristics]
                densities = [c['text_density'] for c in characteristics]
                
                stroke_consistency = 1.0 - (np.std(stroke_widths) / max(np.mean(stroke_widths), 0.1))
                density_consistency = 1.0 - (np.std(densities) / max(np.mean(densities), 0.1))
                
                consistency_score = (stroke_consistency + density_consistency) / 2.0
            else:
                consistency_score = 1.0
            
            return {
                'consistency_score': max(0.0, min(1.0, consistency_score)),
                'characteristics': characteristics,
                'regions_analyzed': len(characteristics)
            }
            
        except Exception as e:
            logger.error(f"Font characteristics analysis failed: {str(e)}")
            return {'consistency_score': 0.0, 'error': str(e)}
    
    def _estimate_stroke_width(self, text_roi: np.ndarray) -> float:
        """Estimate stroke width of text in a region."""
        try:
            # Apply distance transform to estimate stroke width
            binary = (text_roi < 0.5).astype(np.uint8) * 255
            dist_transform = cv2.distanceTransform(binary, cv2.DIST_L2, 5)
            
            # Estimate stroke width from distance transform
            stroke_width = np.mean(dist_transform[dist_transform > 0]) * 2 if np.any(dist_transform > 0) else 1.0
            
            return float(stroke_width)
            
        except Exception as e:
            logger.error(f"Stroke width estimation failed: {str(e)}")
            return 1.0
    
    def _detect_font_inconsistencies(self, font_characteristics: Dict[str, Any]) -> Dict[str, Any]:
        """Detect inconsistencies in font characteristics."""
        try:
            characteristics = font_characteristics.get('characteristics', [])
            
            if len(characteristics) < 2:
                return {'penalty': 0.0, 'inconsistencies': []}
            
            # Analyze stroke width variations
            stroke_widths = [c['stroke_width'] for c in characteristics]
            stroke_cv = np.std(stroke_widths) / max(np.mean(stroke_widths), 0.1)
            
            # Analyze density variations
            densities = [c['text_density'] for c in characteristics]
            density_cv = np.std(densities) / max(np.mean(densities), 0.1)
            
            # Calculate penalty for inconsistencies
            inconsistency_penalty = min(1.0, (stroke_cv + density_cv) / 2.0)
            
            inconsistencies = []
            if stroke_cv > 0.3:
                inconsistencies.append('High stroke width variation')
            if density_cv > 0.3:
                inconsistencies.append('High text density variation')
            
            return {
                'penalty': inconsistency_penalty,
                'inconsistencies': inconsistencies,
                'stroke_cv': float(stroke_cv),
                'density_cv': float(density_cv)
            }
            
        except Exception as e:
            logger.error(f"Font inconsistency detection failed: {str(e)}")
            return {'penalty': 0.0, 'error': str(e)}
    
    def _analyze_text_alignment(self, gray: np.ndarray, text_regions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze text alignment and spacing."""
        try:
            if len(text_regions) < 2:
                return {'score': 1.0, 'alignment_analysis': 'Insufficient regions'}
            
            # Extract y-coordinates of text regions
            y_coords = [region['bbox'][1] for region in text_regions]
            
            # Analyze alignment
            y_std = np.std(y_coords)
            alignment_score = max(0.0, 1.0 - (y_std / 100.0))  # Normalize by expected variation
            
            # Analyze spacing
            if len(text_regions) > 2:
                sorted_regions = sorted(text_regions, key=lambda r: r['bbox'][1])
                spacings = []
                
                for i in range(1, len(sorted_regions)):
                    prev_bottom = sorted_regions[i-1]['bbox'][1] + sorted_regions[i-1]['bbox'][3]
                    curr_top = sorted_regions[i]['bbox'][1]
                    spacing = curr_top - prev_bottom
                    spacings.append(spacing)
                
                spacing_std = np.std(spacings) if spacings else 0.0
                spacing_score = max(0.0, 1.0 - (spacing_std / 50.0))
            else:
                spacing_score = 1.0
            
            overall_score = (alignment_score + spacing_score) / 2.0
            
            return {
                'score': overall_score,
                'alignment_score': alignment_score,
                'spacing_score': spacing_score,
                'y_std': float(y_std),
                'spacing_std': float(spacing_std) if 'spacing_std' in locals() else 0.0
            }
            
        except Exception as e:
            logger.error(f"Text alignment analysis failed: {str(e)}")
            return {'score': 0.0, 'error': str(e)}
    
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