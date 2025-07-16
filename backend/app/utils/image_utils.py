import os
import tempfile
import logging
from typing import Tuple, Optional, Dict, Any
from pathlib import Path
import cv2
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter
import io

logger = logging.getLogger(__name__)


class ImageValidationError(Exception):
    """Exception raised for image validation errors."""
    pass


class ImageProcessingError(Exception):
    """Exception raised for image processing errors."""
    pass


def validate_image_file(file_path: str) -> Dict[str, Any]:
    """
    Validate image file format, size, and properties.
    
    Args:
        file_path: Path to the image file
        
    Returns:
        Dictionary with validation results
        
    Raises:
        ImageValidationError: If validation fails
    """
    try:
        if not os.path.exists(file_path):
            raise ImageProcessingError(f"Image file not found: {file_path}")
        
        # Check file size
        file_size = os.path.getsize(file_path)
        max_size = 50 * 1024 * 1024  # 50MB
        
        if file_size > max_size:
            raise ImageValidationError(f"Image file too large: {file_size} bytes (max: {max_size} bytes)")
        
        # Load image to validate format
        image = Image.open(file_path)
        
        # Check image format
        allowed_formats = ['JPEG', 'PNG', 'TIFF', 'BMP', 'WEBP']
        if image.format not in allowed_formats:
            raise ImageValidationError(f"Unsupported image format: {image.format}")
        
        # Check image dimensions
        width, height = image.size
        max_dimension = 8192
        
        if width > max_dimension or height > max_dimension:
            raise ImageValidationError(f"Image dimensions too large: {width}x{height} (max: {max_dimension}x{max_dimension})")
        
        # Check if image is corrupted
        try:
            image.verify()
        except Exception as e:
            raise ImageProcessingError(f"Image appears to be corrupted: {str(e)}")
        
        # Reload image after verify (verify() closes the image)
        image = Image.open(file_path)
        
        return {
            'valid': True,
            'format': image.format,
            'size': (width, height),
            'file_size': file_size,
            'mode': image.mode,
            'has_transparency': image.mode in ('RGBA', 'LA') or 'transparency' in image.info
        }
        
    except ImageValidationError:
        raise
    except ImageProcessingError:
        raise  
    except Exception as e:
        raise ImageProcessingError(f"Image validation failed: {str(e)}")


def normalize_image_format(file_path: str, target_format: str = 'JPEG', 
                          quality: int = 90) -> str:
    """
    Normalize image format to a standard format.
    
    Args:
        file_path: Path to the source image
        target_format: Target format ('JPEG', 'PNG', etc.)
        quality: JPEG quality (1-100)
        
    Returns:
        Path to the normalized image file
        
    Raises:
        ImageProcessingError: If processing fails
    """
    try:
        # Validate input
        validate_image_file(file_path)
        
        # Load image
        image = Image.open(file_path)
        
        # Convert to RGB if necessary for JPEG
        if target_format == 'JPEG' and image.mode in ('RGBA', 'LA'):
            # Create white background for transparent images
            background = Image.new('RGB', image.size, (255, 255, 255))
            background.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
            image = background
        elif target_format == 'JPEG' and image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Generate output path
        file_path_obj = Path(file_path)
        output_path = file_path_obj.with_suffix(f'.normalized.{target_format.lower()}')
        
        # Save normalized image
        save_kwargs = {}
        if target_format == 'JPEG':
            save_kwargs['quality'] = quality
            save_kwargs['optimize'] = True
        elif target_format == 'PNG':
            save_kwargs['optimize'] = True
        
        image.save(output_path, format=target_format, **save_kwargs)
        
        return str(output_path)
        
    except Exception as e:
        raise ImageProcessingError(f"Image normalization failed: {str(e)}")


def resize_image(file_path: str, max_width: int = 2048, max_height: int = 2048, 
                maintain_aspect_ratio: bool = True) -> str:
    """
    Resize image to specified dimensions.
    
    Args:
        file_path: Path to the source image
        max_width: Maximum width in pixels
        max_height: Maximum height in pixels
        maintain_aspect_ratio: Whether to maintain aspect ratio
        
    Returns:
        Path to the resized image file
        
    Raises:
        ImageProcessingError: If processing fails
    """
    try:
        # Load image
        image = Image.open(file_path)
        original_width, original_height = image.size
        
        # Calculate new dimensions
        if maintain_aspect_ratio:
            # Calculate scaling factor
            width_ratio = max_width / original_width
            height_ratio = max_height / original_height
            scale_factor = min(width_ratio, height_ratio, 1.0)  # Don't upscale
            
            new_width = int(original_width * scale_factor)
            new_height = int(original_height * scale_factor)
        else:
            new_width = min(max_width, original_width)
            new_height = min(max_height, original_height)
        
        # Only resize if dimensions changed
        if new_width != original_width or new_height != original_height:
            image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # Generate output path
        file_path_obj = Path(file_path)
        output_path = file_path_obj.with_suffix(f'.resized{file_path_obj.suffix}')
        
        # Save resized image
        image.save(output_path, quality=90, optimize=True)
        
        return str(output_path)
        
    except Exception as e:
        raise ImageProcessingError(f"Image resizing failed: {str(e)}")


def enhance_image_quality(file_path: str, enhance_contrast: bool = True,
                         enhance_sharpness: bool = True, 
                         enhance_brightness: bool = False) -> str:
    """
    Enhance image quality for better OCR and analysis.
    
    Args:
        file_path: Path to the source image
        enhance_contrast: Whether to enhance contrast
        enhance_sharpness: Whether to enhance sharpness
        enhance_brightness: Whether to enhance brightness
        
    Returns:
        Path to the enhanced image file
        
    Raises:
        ImageProcessingError: If processing fails
    """
    try:
        # Load image
        image = Image.open(file_path)
        
        # Apply enhancements
        if enhance_contrast:
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(1.2)  # Increase contrast by 20%
        
        if enhance_sharpness:
            enhancer = ImageEnhance.Sharpness(image)
            image = enhancer.enhance(1.1)  # Increase sharpness by 10%
        
        if enhance_brightness:
            enhancer = ImageEnhance.Brightness(image)
            image = enhancer.enhance(1.05)  # Increase brightness by 5%
        
        # Apply noise reduction
        image = image.filter(ImageFilter.MedianFilter(size=3))
        
        # Generate output path
        file_path_obj = Path(file_path)
        output_path = file_path_obj.with_suffix(f'.enhanced{file_path_obj.suffix}')
        
        # Save enhanced image
        image.save(output_path, quality=95, optimize=True)
        
        return str(output_path)
        
    except Exception as e:
        raise ImageProcessingError(f"Image enhancement failed: {str(e)}")


def convert_to_grayscale(file_path: str) -> str:
    """
    Convert image to grayscale.
    
    Args:
        file_path: Path to the source image
        
    Returns:
        Path to the grayscale image file
        
    Raises:
        ImageProcessingError: If processing fails
    """
    try:
        # Load image
        image = Image.open(file_path)
        
        # Convert to grayscale
        grayscale_image = image.convert('L')
        
        # Generate output path
        file_path_obj = Path(file_path)
        output_path = file_path_obj.with_suffix(f'.grayscale{file_path_obj.suffix}')
        
        # Save grayscale image
        grayscale_image.save(output_path, quality=90, optimize=True)
        
        return str(output_path)
        
    except Exception as e:
        raise ImageProcessingError(f"Grayscale conversion failed: {str(e)}")


def crop_image(file_path: str, bbox: Tuple[int, int, int, int]) -> str:
    """
    Crop image to specified bounding box.
    
    Args:
        file_path: Path to the source image
        bbox: Bounding box as (left, top, right, bottom)
        
    Returns:
        Path to the cropped image file
        
    Raises:
        ImageProcessingError: If processing fails
    """
    try:
        # Load image
        image = Image.open(file_path)
        
        # Validate bounding box
        left, top, right, bottom = bbox
        width, height = image.size
        
        if left < 0 or top < 0 or right > width or bottom > height:
            raise ImageProcessingError(f"Bounding box {bbox} is outside image bounds {(width, height)}")
        
        if left >= right or top >= bottom:
            raise ImageProcessingError(f"Invalid bounding box: {bbox}")
        
        # Crop image
        cropped_image = image.crop(bbox)
        
        # Generate output path
        file_path_obj = Path(file_path)
        output_path = file_path_obj.with_suffix(f'.cropped{file_path_obj.suffix}')
        
        # Save cropped image
        cropped_image.save(output_path, quality=90, optimize=True)
        
        return str(output_path)
        
    except Exception as e:
        raise ImageProcessingError(f"Image cropping failed: {str(e)}")


def rotate_image(file_path: str, angle: float, expand: bool = True) -> str:
    """
    Rotate image by specified angle.
    
    Args:
        file_path: Path to the source image
        angle: Rotation angle in degrees (positive = counter-clockwise)
        expand: Whether to expand image to fit rotated content
        
    Returns:
        Path to the rotated image file
        
    Raises:
        ImageProcessingError: If processing fails
    """
    try:
        # Load image
        image = Image.open(file_path)
        
        # Rotate image
        rotated_image = image.rotate(angle, expand=expand, fillcolor='white')
        
        # Generate output path
        file_path_obj = Path(file_path)
        output_path = file_path_obj.with_suffix(f'.rotated{file_path_obj.suffix}')
        
        # Save rotated image
        rotated_image.save(output_path, quality=90, optimize=True)
        
        return str(output_path)
        
    except Exception as e:
        raise ImageProcessingError(f"Image rotation failed: {str(e)}")


def detect_image_orientation(file_path: str) -> float:
    """
    Detect image orientation using OpenCV.
    
    Args:
        file_path: Path to the image file
        
    Returns:
        Detected rotation angle in degrees
        
    Raises:
        ImageProcessingError: If processing fails
    """
    try:
        # Load image with OpenCV
        image = cv2.imread(file_path)
        if image is None:
            raise ImageProcessingError(f"Could not load image: {file_path}")
        
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Apply edge detection
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)
        
        # Use HoughLines to detect lines
        lines = cv2.HoughLines(edges, 1, np.pi/180, threshold=100)
        
        if lines is not None:
            angles = []
            for line in lines:
                rho, theta = line[0]
                angle = theta * 180 / np.pi
                
                # Convert to -90 to 90 range
                if angle > 90:
                    angle = angle - 180
                
                angles.append(angle)
            
            # Find the most common angle
            if angles:
                # Use histogram to find dominant angle
                hist, bins = np.histogram(angles, bins=36, range=(-90, 90))
                max_bin = np.argmax(hist)
                detected_angle = (bins[max_bin] + bins[max_bin + 1]) / 2
                
                # Round to nearest 90 degrees for text orientation
                if abs(detected_angle) < 45:
                    return 0.0
                elif detected_angle > 0:
                    return 90.0
                else:
                    return -90.0
        
        return 0.0  # No rotation needed
        
    except Exception as e:
        logger.warning(f"Orientation detection failed: {str(e)}")
        return 0.0


def create_thumbnail(file_path: str, size: Tuple[int, int] = (200, 200)) -> str:
    """
    Create thumbnail of the image.
    
    Args:
        file_path: Path to the source image
        size: Thumbnail size as (width, height)
        
    Returns:
        Path to the thumbnail image file
        
    Raises:
        ImageProcessingError: If processing fails
    """
    try:
        # Load image
        image = Image.open(file_path)
        
        # Create thumbnail
        image.thumbnail(size, Image.Resampling.LANCZOS)
        
        # Generate output path
        file_path_obj = Path(file_path)
        output_path = file_path_obj.with_suffix(f'.thumbnail{file_path_obj.suffix}')
        
        # Save thumbnail
        image.save(output_path, quality=85, optimize=True)
        
        return str(output_path)
        
    except Exception as e:
        raise ImageProcessingError(f"Thumbnail creation failed: {str(e)}")


def get_image_info(file_path: str) -> Dict[str, Any]:
    """
    Get comprehensive information about an image.
    
    Args:
        file_path: Path to the image file
        
    Returns:
        Dictionary with image information
        
    Raises:
        ImageProcessingError: If processing fails
    """
    try:
        # Validate image first
        validation_result = validate_image_file(file_path)
        
        # Load image
        image = Image.open(file_path)
        
        # Get additional information
        info = {
            'file_path': file_path,
            'file_size': validation_result['file_size'],
            'format': validation_result['format'],
            'size': validation_result['size'],
            'mode': validation_result['mode'],
            'has_transparency': validation_result['has_transparency'],
            'dpi': image.info.get('dpi', (72, 72)),
            'color_space': image.mode,
            'bit_depth': len(image.getbands()) * 8 if image.mode in ('RGB', 'RGBA') else 8
        }
        
        # Add EXIF data if available
        if hasattr(image, '_getexif'):
            exif_data = image._getexif()
            if exif_data:
                info['exif'] = {k: v for k, v in exif_data.items() if isinstance(v, (str, int, float))}
        
        return info
        
    except Exception as e:
        raise ImageProcessingError(f"Failed to get image info: {str(e)}")


def cleanup_temp_files(file_paths: list):
    """
    Clean up temporary image files.
    
    Args:
        file_paths: List of file paths to clean up
    """
    for file_path in file_paths:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.debug(f"Cleaned up temporary file: {file_path}")
        except Exception as e:
            logger.warning(f"Failed to clean up file {file_path}: {str(e)}")


def bytes_to_image(image_bytes: bytes) -> Image.Image:
    """
    Convert bytes to PIL Image.
    
    Args:
        image_bytes: Image data as bytes
        
    Returns:
        PIL Image object
        
    Raises:
        ImageProcessingError: If conversion fails
    """
    try:
        image_stream = io.BytesIO(image_bytes)
        image = Image.open(image_stream)
        return image
        
    except Exception as e:
        raise ImageProcessingError(f"Failed to convert bytes to image: {str(e)}")


def image_to_bytes(image: Image.Image, format: str = 'JPEG', quality: int = 90) -> bytes:
    """
    Convert PIL Image to bytes.
    
    Args:
        image: PIL Image object
        format: Output format ('JPEG', 'PNG', etc.)
        quality: JPEG quality (1-100)
        
    Returns:
        Image data as bytes
        
    Raises:
        ImageProcessingError: If conversion fails
    """
    try:
        image_stream = io.BytesIO()
        
        # Convert to RGB if necessary for JPEG
        if format == 'JPEG' and image.mode in ('RGBA', 'LA'):
            background = Image.new('RGB', image.size, (255, 255, 255))
            background.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
            image = background
        
        # Save to stream
        save_kwargs = {}
        if format == 'JPEG':
            save_kwargs['quality'] = quality
            save_kwargs['optimize'] = True
        
        image.save(image_stream, format=format, **save_kwargs)
        
        return image_stream.getvalue()
        
    except Exception as e:
        raise ImageProcessingError(f"Failed to convert image to bytes: {str(e)}")


# Context manager for temporary image files
class TempImageFile:
    """Context manager for temporary image files."""
    
    def __init__(self, suffix: str = '.jpg'):
        self.suffix = suffix
        self.temp_file = None
        self.file_path = None
    
    def __enter__(self):
        self.temp_file = tempfile.NamedTemporaryFile(suffix=self.suffix, delete=False)
        self.file_path = self.temp_file.name
        return self.file_path
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.temp_file:
            self.temp_file.close()
        
        if self.file_path and os.path.exists(self.file_path):
            try:
                os.remove(self.file_path)
            except Exception as e:
                logger.warning(f"Failed to clean up temporary file {self.file_path}: {str(e)}")