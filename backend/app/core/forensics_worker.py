"""
Worker functions for forensics analysis using ProcessPoolExecutor.

These functions are designed to be executed in separate processes to avoid
blocking the asyncio event loop during CPU-intensive operations.
"""

import logging
from typing import Dict, List, Any

from .forensics_exceptions import (
    ForensicsAnalysisError,
    ImageProcessingError,
    FeatureDetectionError,
    CompressionAnalysisError
)

logger = logging.getLogger(__name__)


def detect_edge_inconsistencies_worker(image_data: bytes, image_shape: tuple) -> Dict[str, Any]:
    """
    Worker function for edge inconsistency detection.
    
    Args:
        image_data: Image data as bytes for process communication
        image_shape: Shape tuple (height, width, channels) to reconstruct image
        
    Returns:
        Dictionary with edge analysis results or error information
    """
    try:
        # All imports must be inside function for multiprocessing
        import numpy as np
        from skimage import feature
        from skimage.color import rgb2gray
        
        # Reconstruct image from bytes
        image = np.frombuffer(image_data, dtype=np.uint8).reshape(image_shape)
        
        # Convert to grayscale for edge detection
        gray = rgb2gray(image)
        
        # Apply Canny edge detection
        edges = feature.canny(gray, sigma=1.0, low_threshold=0.1, high_threshold=0.2)
        
        # Analyze edge continuity
        edge_continuity = _analyze_edge_continuity_worker(edges)
        
        # Detect edge sharpness variations
        edge_sharpness = _analyze_edge_sharpness_worker(gray)
        
        # Check for duplicate or cloned regions
        cloned_regions = _detect_cloned_regions_worker(gray)
        
        # Analyze noise patterns for tampering indicators
        noise_analysis = _analyze_noise_patterns_worker(image_data, image_shape)
        
        # Calculate edge inconsistency score including noise analysis
        continuity_score = edge_continuity.get('score', 0.0)
        sharpness_score = edge_sharpness.get('score', 0.0)
        cloning_score = cloned_regions.get('score', 0.0)
        noise_score = noise_analysis.get('score', 0.0)
        
        edge_score = (continuity_score + sharpness_score + cloning_score + noise_score) / 4.0
        
        return {
            'score': edge_score,
            'continuity': edge_continuity,
            'sharpness': edge_sharpness,
            'cloned_regions': cloned_regions,
            'noise_analysis': noise_analysis,
            'edge_density': float(np.sum(edges) / edges.size),
            'edge_map_shape': edges.shape
        }
        
    except Exception as e:
        logger.error(f"Edge detection worker failed: {str(e)}")
        raise ForensicsAnalysisError(f"Edge detection error: {str(e)}")


def analyze_compression_artifacts_worker(image_data: bytes, image_shape: tuple) -> Dict[str, Any]:
    """
    Worker function for compression artifact analysis.
    
    Args:
        image_data: Image data as bytes for process communication
        image_shape: Shape tuple (height, width, channels) to reconstruct image
        
    Returns:
        Dictionary with compression analysis results or error information
    """
    try:
        # All imports must be inside function for multiprocessing
        import numpy as np
        from skimage.color import rgb2gray
        
        # Reconstruct image from bytes
        image = np.frombuffer(image_data, dtype=np.uint8).reshape(image_shape)
        
        # Convert to grayscale
        gray = rgb2gray(image)
        
        # Analyze JPEG compression artifacts
        jpeg_artifacts = _detect_jpeg_artifacts_worker(gray)
        
        # Perform Error Level Analysis (ELA) for compression inconsistencies
        ela_analysis = _perform_error_level_analysis_worker(image_data, image_shape)
        
        # Check for re-compression patterns
        recompression_patterns = _detect_recompression_patterns_worker(gray)
        
        # Calculate compression artifact score
        jpeg_score = jpeg_artifacts.get('score', 0.0)
        ela_score = ela_analysis.get('score', 0.0)
        recompression_score = recompression_patterns.get('score', 0.0)
        
        compression_score = (jpeg_score + ela_score + recompression_score) / 3.0
        
        return {
            'score': compression_score,
            'jpeg_artifacts': jpeg_artifacts,
            'ela_analysis': ela_analysis,
            'recompression_patterns': recompression_patterns,
            'block_artifacts': _analyze_block_artifacts_worker(gray)
        }
        
    except Exception as e:
        logger.error(f"Compression analysis worker failed: {str(e)}")
        raise CompressionAnalysisError(f"Compression analysis error: {str(e)}")


def analyze_font_consistency_worker(image_data: bytes, image_shape: tuple) -> Dict[str, Any]:
    """
    Worker function for font consistency analysis.
    
    Args:
        image_data: Image data as bytes for process communication
        image_shape: Shape tuple (height, width, channels) to reconstruct image
        
    Returns:
        Dictionary with font analysis results or error information
    """
    try:
        # All imports must be inside function for multiprocessing
        import numpy as np
        from skimage.color import rgb2gray
        
        # Reconstruct image from bytes
        image = np.frombuffer(image_data, dtype=np.uint8).reshape(image_shape)
        
        # Convert to grayscale
        gray = rgb2gray(image)
        
        # Detect text regions
        text_regions = _detect_text_regions_worker(gray)
        
        # Analyze font characteristics
        font_characteristics = _analyze_font_characteristics_worker(gray, text_regions)
        
        # Check for font inconsistencies
        font_inconsistencies = _detect_font_inconsistencies_worker(font_characteristics)
        
        # Analyze text alignment and spacing
        text_alignment = _analyze_text_alignment_worker(gray, text_regions)
        
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
        logger.error(f"Font analysis worker failed: {str(e)}")
        raise ForensicsAnalysisError(f"Font analysis error: {str(e)}")


def _perform_error_level_analysis_worker(image_data: bytes, image_shape: tuple) -> Dict[str, Any]:
    """
    Detect compression artifacts using Error Level Analysis.
    ELA reveals areas of different compression levels indicating potential tampering.
    
    Args:
        image_data: Image data as bytes for process communication
        image_shape: Shape tuple (height, width, channels) to reconstruct image
        
    Returns:
        Dictionary with ELA analysis results
        
    Raises:
        CompressionAnalysisError: If ELA analysis fails
    """
    try:
        import cv2
        import numpy as np
        
        # Reconstruct image from bytes
        image = np.frombuffer(image_data, dtype=np.uint8).reshape(image_shape)
        
        # Ensure image is in BGR format for OpenCV
        if len(image.shape) == 3 and image.shape[2] == 3:
            # Convert RGB to BGR if needed (OpenCV uses BGR)
            image_bgr = cv2.cvtColor(image, cv2.COLOR_RGB2BGR) if image_shape[2] == 3 else image
        else:
            raise ImageProcessingError("Image must be 3-channel RGB/BGR format for ELA analysis")
        
        # Convert to JPEG bytes for recompression at 85% quality
        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 85]
        success, buffer = cv2.imencode('.jpg', image_bgr, encode_param)
        
        if not success:
            raise CompressionAnalysisError("Failed to encode image for JPEG recompression")
        
        # Decode the recompressed image
        recompressed = cv2.imdecode(buffer, cv2.IMREAD_COLOR)
        
        if recompressed is None:
            raise CompressionAnalysisError("Failed to decode recompressed image")
        
        # Calculate difference (Error Level)
        if image_bgr.shape == recompressed.shape:
            difference = cv2.absdiff(image_bgr, recompressed)
            gray_diff = cv2.cvtColor(difference, cv2.COLOR_BGR2GRAY)
            
            # Enhance differences for analysis
            enhanced = cv2.equalizeHist(gray_diff)
            
            # Statistical analysis of error levels
            mean_error = float(np.mean(enhanced))
            std_error = float(np.std(enhanced))
            max_error = float(np.max(enhanced))
            
            # Identify suspicious regions with high error levels
            suspicious_regions = _identify_suspicious_regions_worker(enhanced)
            
            # Calculate ELA score based on error variance and intensity
            # High variance indicates inconsistent compression (potential tampering)
            ela_score = min(1.0, (std_error / 50.0) + (max_error / 255.0))
            
            return {
                'score': float(ela_score),
                'mean_error_level': mean_error,
                'error_variance': std_error,
                'max_error_level': max_error,
                'suspicious_regions': suspicious_regions,
                'analysis_method': 'Error Level Analysis (ELA)',
                'recompression_quality': 85
            }
        else:
            raise CompressionAnalysisError(
                f"Image recompression failed - dimension mismatch: "
                f"original {image_bgr.shape} vs recompressed {recompressed.shape}"
            )
            
    except (ImageProcessingError, CompressionAnalysisError):
        raise
    except Exception as e:
        logger.error(f"ELA analysis failed: {str(e)}")
        raise CompressionAnalysisError(f"ELA analysis error: {str(e)}")


def _identify_suspicious_regions_worker(enhanced_diff) -> List[Dict[str, Any]]:
    """
    Identify regions with suspicious compression inconsistencies.
    
    Args:
        enhanced_diff: Enhanced difference image from ELA
        
    Returns:
        List of suspicious regions with their characteristics
    """
    try:
        import cv2
        import numpy as np
        
        # Threshold to find high-error regions
        threshold_value = np.percentile(enhanced_diff, 90)  # Top 10% of error levels
        _, thresh = cv2.threshold(enhanced_diff, threshold_value, 255, cv2.THRESH_BINARY)
        
        # Find contours of suspicious regions
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        suspicious_regions = []
        for i, contour in enumerate(contours):
            area = cv2.contourArea(contour)
            if area > 100:  # Filter out noise
                x, y, w, h = cv2.boundingRect(contour)
                
                # Calculate region error statistics
                region_diff = enhanced_diff[y:y+h, x:x+w]
                region_mean = float(np.mean(region_diff))
                region_max = float(np.max(region_diff))
                
                suspicious_regions.append({
                    'region_id': i,
                    'bbox': [int(x), int(y), int(w), int(h)],
                    'area': float(area),
                    'mean_error': region_mean,
                    'max_error': region_max,
                    'suspicion_score': min(1.0, region_max / 255.0)
                })
        
        return suspicious_regions
        
    except Exception as e:
        logger.warning(f"Failed to identify suspicious regions: {str(e)}")
        return []


def _analyze_edge_continuity_worker(edges) -> Dict[str, Any]:
    """Analyze edge continuity for potential tampering indicators."""
    try: 
        import numpy as np
        from skimage import measure
        
        # Find connected components in edges
        labeled_edges = measure.label(edges)
        regions = measure.regionprops(labeled_edges)
        
        # Calculate edge continuity metrics
        total_regions = len(regions)
        avg_region_size = float(np.mean([region.area for region in regions])) if regions else 0.0
        
        # Detect broken edges that might indicate tampering
        broken_edges = sum(1 for region in regions if region.area < 10)
        
        # Calculate continuity score
        continuity_ratio = 1.0 - (broken_edges / max(total_regions, 1))
        
        return {
            'score': float(continuity_ratio),
            'total_regions': int(total_regions),
            'avg_region_size': float(avg_region_size),
            'broken_edges': int(broken_edges),
            'continuity_ratio': float(continuity_ratio)
        }
        
    except Exception as e:
        logger.error(f"Edge continuity analysis worker failed: {str(e)}")
        raise ImageProcessingError(f"Edge continuity analysis error: {str(e)}")


def _analyze_edge_sharpness_worker(gray) -> Dict[str, Any]:
    """Analyze edge sharpness variations."""
    try:
        import cv2
        import numpy as np
        
        # Apply Laplacian filter to detect sharpness
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        sharpness_variance = float(np.var(laplacian))
        
        # Normalize sharpness score
        sharpness_score = min(1.0, sharpness_variance / 1000.0)
        
        return {
            'score': float(sharpness_score),
            'variance': float(sharpness_variance),
            'mean_sharpness': float(np.mean(np.abs(laplacian)))
        }
        
    except Exception as e:
        logger.error(f"Edge sharpness analysis worker failed: {str(e)}")
        raise ImageProcessingError(f"Edge sharpness analysis error: {str(e)}")


def _detect_cloned_regions_worker(gray) -> Dict[str, Any]:
    """
    Detect copy-move forgery using AKAZE features and RANSAC.
    No size limits - uses tiling for large images.
    
    Args:
        gray: Grayscale image array
        
    Returns:
        Dictionary with copy-move detection results
        
    Raises:
        FeatureDetectionError: If feature detection fails
    """
    try:
        import cv2
        import numpy as np
        from .forensics_exceptions import FeatureDetectionError
        
        h, w = gray.shape
        
        # Use tiling for large images instead of skipping analysis
        if h * w > 2000000:  # 2MP threshold for tiling
            return _tile_based_copy_move_detection_worker(gray)
        
        # Convert to uint8 if needed
        if gray.dtype != np.uint8:
            gray = (gray * 255).astype(np.uint8)
            
        # AKAZE feature detection (more robust than SIFT/SURF)
        detector = cv2.AKAZE_create()
        keypoints, descriptors = detector.detectAndCompute(gray, None)
        
        if descriptors is None or len(descriptors) < 10:
            return {
                'score': 0.0, 
                'regions': [], 
                'keypoints_found': 0,
                'analysis_method': 'AKAZE feature detection'
            }
        
        # Match features to themselves to find duplicates
        matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
        matches = matcher.knnMatch(descriptors, descriptors, k=3)
        
        # Filter self-matches and find suspicious clusters
        suspicious_matches = []
        for m in matches:
            if len(m) >= 2:
                # Skip self-match (distance 0)
                if m[0].distance == 0 and len(m) > 1:
                    if m[1].distance < 50:  # Threshold for similar features
                        suspicious_matches.append(m[1])
        
        # Use RANSAC to find geometric consistency
        if len(suspicious_matches) > 4:
            src_pts = np.float32([keypoints[m.queryIdx].pt for m in suspicious_matches])
            dst_pts = np.float32([keypoints[m.trainIdx].pt for m in suspicious_matches])
            
            # Find homography (geometric transformation)
            homography, mask = cv2.findHomography(
                src_pts, dst_pts, cv2.RANSAC, 5.0
            )
            
            if mask is not None:
                inliers = np.sum(mask)
                cloning_score = min(1.0, inliers / 20.0)  # Normalize to 0-1
                
                # Extract copy-move regions from inlier matches
                copy_move_regions = _extract_copy_move_regions_worker(
                    src_pts[mask.ravel() == 1], 
                    dst_pts[mask.ravel() == 1]
                )
                
                return {
                    'score': float(cloning_score),
                    'suspicious_matches': int(len(suspicious_matches)),
                    'geometric_inliers': int(inliers),
                    'total_keypoints': int(len(keypoints)),
                    'copy_move_regions': copy_move_regions,
                    'analysis_method': 'AKAZE + RANSAC'
                }
            else:
                return {
                    'score': 0.0,
                    'regions': [],
                    'keypoints_found': len(keypoints),
                    'analysis_method': 'AKAZE feature detection'
                }
        else:
            return {
                'score': 0.0, 
                'regions': [], 
                'keypoints_found': len(keypoints),
                'analysis_method': 'AKAZE feature detection'
            }
            
    except Exception as e:
        logger.error(f"Copy-move detection failed: {str(e)}")
        raise FeatureDetectionError(f"Copy-move detection error: {str(e)}")


def _tile_based_copy_move_detection_worker(gray) -> Dict[str, Any]:
    """
    Perform copy-move detection on large images using tiling strategy.
    
    Args:
        gray: Large grayscale image array
        
    Returns:
        Dictionary with aggregated copy-move detection results
    """
    try:
        import numpy as np
        
        h, w = gray.shape
        tile_size = 1024  # Process in 1024x1024 tiles
        overlap = 128     # Overlap to avoid missing features at boundaries
        
        all_scores = []
        all_regions = []
        total_keypoints = 0
        
        logger.info(f"Processing large image ({w}x{h}) using tiling strategy")
        
        # Process overlapping tiles
        for y in range(0, h - tile_size + 1, tile_size - overlap):
            for x in range(0, w - tile_size + 1, tile_size - overlap):
                # Extract tile with bounds checking
                y_end = min(y + tile_size, h)
                x_end = min(x + tile_size, w)
                tile = gray[y:y_end, x:x_end]
                
                # Process tile if it's large enough
                if tile.shape[0] > 200 and tile.shape[1] > 200:
                    tile_result = _detect_cloned_regions_worker(tile)
                    
                    tile_score = tile_result.get('score', 0.0)
                    all_scores.append(tile_score)
                    total_keypoints += tile_result.get('total_keypoints', 0)
                    
                    # Adjust region coordinates to global image coordinates
                    tile_regions = tile_result.get('copy_move_regions', [])
                    for region in tile_regions:
                        region['global_bbox'] = [
                            region['bbox'][0] + x,
                            region['bbox'][1] + y,
                            region['bbox'][2],
                            region['bbox'][3]
                        ]
                        all_regions.append(region)
        
        # Aggregate results
        if all_scores:
            max_score = max(all_scores)
            avg_score = np.mean(all_scores)
            final_score = (max_score + avg_score) / 2.0  # Balance max and average
        else:
            final_score = 0.0
        
        return {
            'score': float(final_score),
            'tiles_processed': len(all_scores),
            'copy_move_regions': all_regions,
            'total_keypoints': total_keypoints,
            'analysis_method': 'Tiled AKAZE + RANSAC',
            'tile_size': tile_size,
            'max_tile_score': float(max(all_scores)) if all_scores else 0.0
        }
        
    except Exception as e:
        logger.error(f"Tiled copy-move detection failed: {str(e)}")
        raise FeatureDetectionError(f"Tiled copy-move detection error: {str(e)}")


def _extract_copy_move_regions_worker(src_pts, dst_pts) -> List[Dict[str, Any]]:
    """
    Extract copy-move regions from matched keypoints.
    
    Args:
        src_pts: Source keypoints from inlier matches
        dst_pts: Destination keypoints from inlier matches
        
    Returns:
        List of copy-move region descriptions
    """
    try:
        import numpy as np
        import cv2
        
        if len(src_pts) < 4:
            return []
        
        regions = []
        
        # Group nearby points into regions
        for i, (src_pt, dst_pt) in enumerate(zip(src_pts, dst_pts)):
            # Calculate displacement vector
            displacement = dst_pt - src_pt
            displacement_magnitude = np.linalg.norm(displacement)
            
            # Only consider significant displacements (avoid noise)
            if displacement_magnitude > 10:
                # Create bounding box around the point cluster
                nearby_src = []
                nearby_dst = []
                
                for j, (other_src, other_dst) in enumerate(zip(src_pts, dst_pts)):
                    if np.linalg.norm(src_pt - other_src) < 50:  # Nearby threshold
                        nearby_src.append(other_src)
                        nearby_dst.append(other_dst)
                
                if len(nearby_src) >= 3:  # Minimum points for a region
                    # Calculate bounding boxes
                    src_bbox = cv2.boundingRect(np.array(nearby_src, dtype=np.float32))
                    dst_bbox = cv2.boundingRect(np.array(nearby_dst, dtype=np.float32))
                    
                    regions.append({
                        'region_id': len(regions),
                        'src_bbox': [int(src_bbox[0]), int(src_bbox[1]), int(src_bbox[2]), int(src_bbox[3])],
                        'dst_bbox': [int(dst_bbox[0]), int(dst_bbox[1]), int(dst_bbox[2]), int(dst_bbox[3])],
                        'displacement': [float(displacement[0]), float(displacement[1])],
                        'displacement_magnitude': float(displacement_magnitude),
                        'point_count': len(nearby_src),
                        'confidence': min(1.0, len(nearby_src) / 10.0)
                    })
        
        return regions
        
    except Exception as e:
        logger.warning(f"Failed to extract copy-move regions: {str(e)}")
        return []


def _analyze_noise_patterns_worker(image_data: bytes, image_shape: tuple) -> Dict[str, Any]:
    """
    Analyze noise patterns for inconsistencies that might indicate tampering.
    
    Detects inconsistent noise characteristics across different regions of the image,
    which can indicate splicing, copy-move operations, or other manipulations.
    
    Args:
        image_data: Image data as bytes for process communication
        image_shape: Shape tuple (height, width, channels) to reconstruct image
        
    Returns:
        Dictionary with noise analysis results
        
    Raises:
        ImageProcessingError: If noise analysis fails
    """
    try:
        import cv2
        import numpy as np
        from .forensics_exceptions import ImageProcessingError
        
        # Reconstruct image from bytes
        image = np.frombuffer(image_data, dtype=np.uint8).reshape(image_shape)
        
        # Convert to grayscale for noise analysis
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        else:
            gray = image
        
        # Ensure float type for accurate calculations
        gray = gray.astype(np.float64)
        
        # Apply high-pass filter to isolate noise
        noise_image = _extract_noise_component_worker(gray)
        
        # Analyze noise characteristics in different regions
        noise_statistics = _analyze_regional_noise_worker(noise_image)
        
        # Detect noise inconsistencies
        inconsistency_score = _detect_noise_inconsistencies_worker(noise_statistics)
        
        # Model noise distribution
        noise_model = _model_noise_distribution_worker(noise_image)
        
        # Calculate overall noise analysis score
        noise_score = min(1.0, inconsistency_score + noise_model.get('anomaly_score', 0.0))
        
        return {
            'score': float(noise_score),
            'regional_statistics': noise_statistics,
            'noise_model': noise_model,
            'inconsistency_score': float(inconsistency_score),
            'analysis_method': 'Gaussian noise modeling with regional analysis',
            'regions_analyzed': len(noise_statistics)
        }
        
    except Exception as e:
        logger.error(f"Noise analysis failed: {str(e)}")
        raise ImageProcessingError(f"Noise analysis error: {str(e)}")


def _extract_noise_component_worker(gray):
    """
    Extract noise component from image using high-pass filtering.
    
    Args:
        gray: Grayscale image as float64 array
        
    Returns:
        Noise component of the image
    """
    try:
        import cv2
        from skimage import filters
        
        # Apply Gaussian blur to get low-frequency component
        blurred = filters.gaussian(gray, sigma=1.0)
        
        # Subtract blurred from original to get high-frequency (noise) component
        noise = gray - blurred
        
        # Alternative method: use Laplacian for edge-preserving noise extraction
        laplacian = cv2.Laplacian(gray, cv2.CV_64F, ksize=3)
        
        # Combine both methods for robust noise estimation
        combined_noise = 0.7 * noise + 0.3 * laplacian
        
        return combined_noise
        
    except Exception as e:
        logger.warning(f"Failed to extract noise component: {str(e)}")
        return gray - filters.gaussian(gray, sigma=1.0)  # Fallback method


def _analyze_regional_noise_worker(noise_image) -> List[Dict[str, Any]]:
    """
    Analyze noise characteristics in different regions of the image.
    
    Args:
        noise_image: High-frequency noise component of the image
        
    Returns:
        List of regional noise statistics
    """
    try:
        import numpy as np
        
        h, w = noise_image.shape
        region_size = 64  # 64x64 pixel regions
        noise_stats = []
        
        # Analyze noise in overlapping regions
        step_size = region_size // 2  # 50% overlap
        
        for y in range(0, h - region_size + 1, step_size):
            for x in range(0, w - region_size + 1, step_size):
                region = noise_image[y:y+region_size, x:x+region_size]
                
                # Calculate noise statistics for this region
                noise_variance = float(np.var(region))
                noise_mean = float(np.mean(region))
                noise_std = float(np.std(region))
                noise_skewness = float(_calculate_skewness_worker(region))
                noise_kurtosis = float(_calculate_kurtosis_worker(region))
                
                # Estimate local signal-to-noise ratio
                signal_power = float(np.var(region + np.mean(region)))
                snr = signal_power / max(noise_variance, 1e-10)
                
                noise_stats.append({
                    'region_id': len(noise_stats),
                    'bbox': [x, y, region_size, region_size],
                    'variance': noise_variance,
                    'mean': noise_mean,
                    'std': noise_std,
                    'skewness': noise_skewness,
                    'kurtosis': noise_kurtosis,
                    'snr': float(snr)
                })
        
        return noise_stats
        
    except Exception as e:
        logger.warning(f"Failed to analyze regional noise: {str(e)}")
        return []


def _detect_noise_inconsistencies_worker(noise_statistics: List[Dict[str, Any]]) -> float:
    """
    Detect inconsistencies in noise characteristics across regions.
    
    Args:
        noise_statistics: List of regional noise statistics
        
    Returns:
        Inconsistency score (0.0 to 1.0)
    """
    try:
        import numpy as np
        
        if len(noise_statistics) < 4:
            return 0.0
        
        # Extract statistical measures
        variances = [stat['variance'] for stat in noise_statistics]
        skewnesses = [stat['skewness'] for stat in noise_statistics]
        kurtoses = [stat['kurtosis'] for stat in noise_statistics]
        snrs = [stat['snr'] for stat in noise_statistics]
        
        # Calculate coefficient of variation for each measure
        variance_cv = np.std(variances) / max(np.mean(variances), 1e-10)
        skewness_cv = np.std(skewnesses) / max(abs(np.mean(skewnesses)), 1e-10)
        kurtosis_cv = np.std(kurtoses) / max(abs(np.mean(kurtoses)), 1e-10)
        snr_cv = np.std(snrs) / max(np.mean(snrs), 1e-10)
        
        # High coefficient of variation indicates inconsistent noise
        # Combine different measures with weights
        inconsistency_score = (
            0.4 * min(1.0, variance_cv / 0.5) +    # Variance inconsistency
            0.3 * min(1.0, skewness_cv / 1.0) +    # Distribution shape inconsistency
            0.2 * min(1.0, kurtosis_cv / 1.0) +    # Tail behavior inconsistency
            0.1 * min(1.0, snr_cv / 0.3)           # SNR inconsistency
        )
        
        return float(inconsistency_score)
        
    except Exception as e:
        logger.warning(f"Failed to detect noise inconsistencies: {str(e)}")
        return 0.0


def _model_noise_distribution_worker(noise_image) -> Dict[str, Any]:
    """
    Model the noise distribution and detect anomalies.
    
    Args:
        noise_image: High-frequency noise component
        
    Returns:
        Dictionary with noise model results
    """
    try:
        import numpy as np
        from scipy import stats
        
        # Flatten noise image for distribution analysis
        noise_flat = noise_image.flatten()
        
        # Remove extreme outliers for robust fitting
        percentile_1 = np.percentile(noise_flat, 1)
        percentile_99 = np.percentile(noise_flat, 99)
        noise_filtered = noise_flat[(noise_flat >= percentile_1) & (noise_flat <= percentile_99)]
        
        # Fit Gaussian distribution
        gaussian_params = stats.norm.fit(noise_filtered)
        gaussian_mean = float(gaussian_params[0])
        gaussian_std = float(gaussian_params[1])
        
        # Test goodness of fit using Kolmogorov-Smirnov test
        ks_statistic, ks_p_value = stats.kstest(
            noise_filtered, 
            lambda x: stats.norm.cdf(x, gaussian_mean, gaussian_std)
        )
        
        # Calculate anomaly score based on deviation from Gaussian
        # High KS statistic indicates non-Gaussian noise (potential manipulation)
        anomaly_score = min(1.0, ks_statistic / 0.1)
        
        # Additional check: analyze noise histogram
        hist, bin_edges = np.histogram(noise_filtered, bins=50, density=True)
        
        # Expected Gaussian values at bin centers
        bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
        expected_gaussian = stats.norm.pdf(bin_centers, gaussian_mean, gaussian_std)
        
        # Calculate chi-squared statistic for histogram comparison
        chi_squared = np.sum((hist - expected_gaussian) ** 2 / (expected_gaussian + 1e-10))
        
        return {
            'gaussian_mean': gaussian_mean,
            'gaussian_std': gaussian_std,
            'ks_statistic': float(ks_statistic),
            'ks_p_value': float(ks_p_value),
            'anomaly_score': float(anomaly_score),
            'chi_squared': float(chi_squared),
            'distribution_type': 'Gaussian' if ks_p_value > 0.05 else 'Non-Gaussian'
        }
        
    except Exception as e:
        logger.warning(f"Failed to model noise distribution: {str(e)}")
        return {
            'gaussian_mean': 0.0,
            'gaussian_std': 1.0,
            'anomaly_score': 0.0,
            'distribution_type': 'Unknown'
        }


def _calculate_skewness_worker(data) -> float:
    """Calculate skewness of data distribution."""
    try:
        import numpy as np
        
        data_flat = data.flatten()
        mean = np.mean(data_flat)
        std = np.std(data_flat)
        
        if std == 0:
            return 0.0
        
        skewness = np.mean(((data_flat - mean) / std) ** 3)
        return float(skewness)
        
    except Exception:
        return 0.0


def _calculate_kurtosis_worker(data) -> float:
    """Calculate kurtosis of data distribution."""
    try:
        import numpy as np
        
        data_flat = data.flatten()
        mean = np.mean(data_flat)
        std = np.std(data_flat)
        
        if std == 0:
            return 0.0
        
        kurtosis = np.mean(((data_flat - mean) / std) ** 4) - 3  # Excess kurtosis
        return float(kurtosis)
        
    except Exception:
        return 0.0


def _detect_jpeg_artifacts_worker(gray) -> Dict[str, Any]:
    """Detect JPEG compression artifacts."""
    try:
        import cv2
        import numpy as np
        
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
        avg_artifact = float(np.mean(artifacts)) if artifacts else 0.0
        artifact_score = min(1.0, avg_artifact / 10.0)
        
        return {
            'score': float(artifact_score),
            'avg_artifact_level': float(avg_artifact),
            'artifact_variance': float(np.var(artifacts)) if artifacts else 0.0,
            'blocks_analyzed': int(len(artifacts))
        }
        
    except Exception as e:
        logger.error(f"JPEG artifact detection worker failed: {str(e)}")
        raise CompressionAnalysisError(f"JPEG artifact detection error: {str(e)}")


def _detect_compression_inconsistencies_worker(image) -> Dict[str, Any]:
    """Detect compression quality inconsistencies."""
    try:
        import numpy as np
        from skimage.color import rgb2gray
        
        # Analyze compression quality across different regions
        h, w, _ = image.shape
        region_size = 64
        quality_measures = []
        
        for i in range(0, h - region_size, region_size):
            for j in range(0, w - region_size, region_size):
                region = image[i:i+region_size, j:j+region_size]
                
                # Calculate local quality measure
                gray_region = rgb2gray(region)
                quality = float(np.var(gray_region))
                quality_measures.append(quality)
        
        # Check for inconsistencies
        quality_std = float(np.std(quality_measures)) if quality_measures else 0.0
        inconsistency_score = min(1.0, quality_std / 100.0)
        
        return {
            'score': float(inconsistency_score),
            'quality_variance': float(quality_std),
            'regions_analyzed': int(len(quality_measures)),
            'avg_quality': float(np.mean(quality_measures)) if quality_measures else 0.0
        }
        
    except Exception as e:
        logger.error(f"Compression inconsistency detection worker failed: {str(e)}")
        raise CompressionAnalysisError(f"Compression inconsistency detection error: {str(e)}")


def _detect_recompression_patterns_worker(gray) -> Dict[str, Any]:
    """Detect patterns indicating multiple compression passes."""
    try:
        import numpy as np
        
        # Analyze frequency domain for recompression indicators
        f_transform = np.fft.fft2(gray)
        f_magnitude = np.abs(f_transform)
        
        # Look for periodic patterns that might indicate recompression
        h, w = f_magnitude.shape
        center_h, center_w = h // 2, w // 2
        
        # Analyze frequency distribution
        freq_profile = f_magnitude[center_h-20:center_h+20, center_w-20:center_w+20]
        recompression_indicator = float(np.std(freq_profile))
        
        recompression_score = min(1.0, recompression_indicator / 10000.0)
        
        return {
            'score': float(recompression_score),
            'frequency_std': float(recompression_indicator),
            'analysis_region_shape': list(freq_profile.shape)
        }
        
    except Exception as e:
        logger.error(f"Recompression pattern detection worker failed: {str(e)}")
        raise CompressionAnalysisError(f"Recompression pattern detection error: {str(e)}")


def _analyze_block_artifacts_worker(gray) -> Dict[str, Any]:
    """Analyze block-based compression artifacts."""
    try:
        import cv2
        import numpy as np
        
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
        avg_boundary_strength = float(np.mean(block_boundaries)) if block_boundaries else 0.0
        block_artifact_score = min(1.0, avg_boundary_strength / 50.0)
        
        return {
            'score': float(block_artifact_score),
            'avg_boundary_strength': float(avg_boundary_strength),
            'boundaries_analyzed': int(len(block_boundaries))
        }
        
    except Exception as e:
        logger.error(f"Block artifact analysis worker failed: {str(e)}")
        raise CompressionAnalysisError(f"Block artifact analysis error: {str(e)}")


def _detect_text_regions_worker(gray) -> List[Dict[str, Any]]:
    """Detect text regions in the image."""
    try:
        import cv2
        
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
        logger.error(f"Text region detection worker failed: {str(e)}")
        return []


def _analyze_font_characteristics_worker(gray, text_regions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze font characteristics in detected text regions."""
    try:
        import numpy as np
        
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
                'stroke_width': _estimate_stroke_width_worker(text_roi),
                'text_density': float(np.mean(text_roi < 0.5)),
                'uniformity': float(np.std(text_roi)),
                'bbox': region['bbox']
            }
            
            characteristics.append(char_analysis)
        
        # Calculate consistency score
        if len(characteristics) > 1:
            stroke_widths = [c['stroke_width'] for c in characteristics]
            densities = [c['text_density'] for c in characteristics]
            
            stroke_consistency = 1.0 - (float(np.std(stroke_widths)) / max(float(np.mean(stroke_widths)), 0.1))
            density_consistency = 1.0 - (float(np.std(densities)) / max(float(np.mean(densities)), 0.1))
            
            consistency_score = (stroke_consistency + density_consistency) / 2.0
        else:
            consistency_score = 1.0
        
        return {
            'consistency_score': float(max(0.0, min(1.0, consistency_score))),
            'characteristics': characteristics,
            'regions_analyzed': int(len(characteristics))
        }
        
    except Exception as e:
        logger.error(f"Font characteristics analysis worker failed: {str(e)}")
        raise ForensicsAnalysisError(f"Font characteristics analysis error: {str(e)}")


def _estimate_stroke_width_worker(text_roi) -> float:
    """Estimate stroke width of text in a region."""
    try:
        import cv2
        import numpy as np
        
        # Apply distance transform to estimate stroke width
        binary = (text_roi < 0.5).astype(np.uint8) * 255
        dist_transform = cv2.distanceTransform(binary, cv2.DIST_L2, 5)
        
        # Estimate stroke width from distance transform
        stroke_width = np.mean(dist_transform[dist_transform > 0]) * 2 if np.any(dist_transform > 0) else 1.0
        
        return float(stroke_width)
        
    except Exception as e:
        logger.error(f"Stroke width estimation worker failed: {str(e)}")
        return 1.0


def _detect_font_inconsistencies_worker(font_characteristics: Dict[str, Any]) -> Dict[str, Any]:
    """Detect inconsistencies in font characteristics."""
    try:
        import numpy as np
        
        characteristics = font_characteristics.get('characteristics', [])
        
        if len(characteristics) < 2:
            return {'penalty': 0.0, 'inconsistencies': []}
        
        # Analyze stroke width variations
        stroke_widths = [c['stroke_width'] for c in characteristics]
        stroke_cv = float(np.std(stroke_widths)) / max(float(np.mean(stroke_widths)), 0.1)
        
        # Analyze density variations
        densities = [c['text_density'] for c in characteristics]
        density_cv = float(np.std(densities)) / max(float(np.mean(densities)), 0.1)
        
        # Calculate penalty for inconsistencies
        inconsistency_penalty = min(1.0, (stroke_cv + density_cv) / 2.0)
        
        inconsistencies = []
        if stroke_cv > 0.3:
            inconsistencies.append('High stroke width variation')
        if density_cv > 0.3:
            inconsistencies.append('High text density variation')
        
        return {
            'penalty': float(inconsistency_penalty),
            'inconsistencies': inconsistencies,
            'stroke_cv': float(stroke_cv),
            'density_cv': float(density_cv)
        }
        
    except Exception as e:
        logger.error(f"Font inconsistency detection worker failed: {str(e)}")
        raise ForensicsAnalysisError(f"Font inconsistency detection error: {str(e)}")


def _analyze_text_alignment_worker(gray, text_regions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze text alignment and spacing."""
    try:
        import numpy as np
        
        if len(text_regions) < 2:
            return {'score': 1.0, 'alignment_analysis': 'Insufficient regions'}
        
        # Extract y-coordinates of text regions
        y_coords = [region['bbox'][1] for region in text_regions]
        
        # Analyze alignment
        y_std = float(np.std(y_coords))
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
            
            spacing_std = float(np.std(spacings)) if spacings else 0.0
            spacing_score = max(0.0, 1.0 - (spacing_std / 50.0))
        else:
            spacing_score = 1.0
        
        overall_score = (alignment_score + spacing_score) / 2.0
        
        return {
            'score': float(overall_score),
            'alignment_score': float(alignment_score),
            'spacing_score': float(spacing_score),
            'y_std': float(y_std),
            'spacing_std': float(spacing_std) if 'spacing_std' in locals() else 0.0
        }
        
    except Exception as e:
        logger.error(f"Text alignment analysis worker failed: {str(e)}")
        raise ForensicsAnalysisError(f"Text alignment analysis error: {str(e)}")