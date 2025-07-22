import os
import logging
from typing import Dict, Any, List
from pathlib import Path
from PIL import Image

from .image_utils import (
    validate_image_file, 
    ImageValidationError, 
    ImageProcessingError,
    normalize_image_format,
    enhance_image_quality,
    cleanup_temp_files
)
from .pdf_utils import (
    validate_pdf_file,
    PDFValidationError,
    PDFProcessingError,
    convert_pdf_to_image_for_analysis,
    is_pdf_file
)

logger = logging.getLogger(__name__)


class FileValidationError(Exception):
    """Exception raised for file validation errors."""
    pass


class FileProcessingError(Exception):
    """Exception raised for file processing errors."""
    pass


def get_file_type(file_path: str) -> str:
    """
    Determine the file type based on extension and content.
    
    Args:
        file_path: Path to the file
        
    Returns:
        File type ('image', 'pdf', 'unknown')
    """
    try:
        logger.debug(f"Determining file type for: {file_path}")
        
        # Check if file exists
        if not os.path.exists(file_path):
            logger.warning(f"File does not exist: {file_path}")
            return 'unknown'
        
        # Check PDF first
        try:
            if is_pdf_file(file_path):
                logger.debug(f"File identified as PDF: {file_path}")
                return 'pdf'
        except Exception as e:
            logger.warning(f"PDF check failed for {file_path}: {str(e)}")
        
        # Check image formats
        try:
            with Image.open(file_path):
                # If we can open it as an image, it's an image
                logger.debug(f"File identified as image: {file_path}")
                return 'image'
        except Exception as e:
            logger.debug(f"Image check failed for {file_path}: {str(e)}")
        
        # Check by extension as fallback
        extension = Path(file_path).suffix.lower()
        logger.debug(f"Checking extension: {extension}")
        
        image_extensions = {'.jpg', '.jpeg', '.png', '.tiff', '.tif', '.bmp', '.webp', '.gif'}
        pdf_extensions = {'.pdf'}
        
        if extension in image_extensions:
            logger.debug(f"File identified as image by extension: {file_path}")
            return 'image'
        elif extension in pdf_extensions:
            logger.debug(f"File identified as PDF by extension: {file_path}")
            return 'pdf'
        
        logger.warning(f"File type unknown: {file_path}")
        return 'unknown'
        
    except Exception as e:
        logger.error(f"Could not determine file type for {file_path}: {str(e)}")
        return 'unknown'


def validate_file_for_analysis(file_path: str) -> Dict[str, Any]:
    """
    Validate a file (image or PDF) for check analysis.
    
    Args:
        file_path: Path to the file
        
    Returns:
        Dictionary with validation results
        
    Raises:
        FileValidationError: If validation fails
    """
    try:
        if not os.path.exists(file_path):
            raise FileValidationError(f"File not found: {file_path}")
        
        logger.debug(f"Validating file for analysis: {file_path}")
        file_type = get_file_type(file_path)
        logger.debug(f"File type determined as: {file_type}")
        
        if file_type == 'image':
            try:
                validation_result = validate_image_file(file_path)
                validation_result['file_type'] = 'image'
                logger.debug(f"Image validation successful: {file_path}")
                return validation_result
            except ImageValidationError as e:
                logger.error(f"Image validation failed for {file_path}: {str(e)}")
                raise FileValidationError(f"Image validation failed: {str(e)}")
                
        elif file_type == 'pdf':
            try:
                validation_result = validate_pdf_file(file_path)
                validation_result['file_type'] = 'pdf'
                logger.debug(f"PDF validation successful: {file_path}")
                return validation_result
            except PDFValidationError as e:
                logger.error(f"PDF validation failed for {file_path}: {str(e)}")
                raise FileValidationError(f"PDF validation failed: {str(e)}")
                
        else:
            error_msg = f"Unsupported file type: {file_type} for file: {file_path}"
            logger.error(error_msg)
            raise FileValidationError(error_msg)
        
    except FileValidationError:
        raise
    except Exception as e:
        error_msg = f"File validation failed: {str(e)}"
        logger.error(f"Unexpected error validating {file_path}: {error_msg}")
        raise FileValidationError(error_msg)


def prepare_file_for_analysis(file_path: str, page_number: int = 1) -> str:
    """
    Prepare a file (image or PDF) for analysis by converting to optimized image format.
    
    Args:
        file_path: Path to the source file
        page_number: Page number for PDFs (1-indexed)
        
    Returns:
        Path to the prepared image file ready for analysis
        
    Raises:
        FileProcessingError: If preparation fails
    """
    try:
        # Validate file first
        logger.debug(f"Preparing file for analysis: {file_path}, page: {page_number}")
        validation_result = validate_file_for_analysis(file_path)
        file_type = validation_result.get('file_type')
        logger.debug(f"File type for analysis: {file_type}")
        
        if file_type == 'image':
            # Process as image
            try:
                # Normalize image format
                normalized_path = normalize_image_format(file_path, 'JPEG', quality=95)
                
                # Enhance for analysis
                enhanced_path = enhance_image_quality(
                    normalized_path,
                    enhance_contrast=True,
                    enhance_sharpness=True,
                    enhance_brightness=False
                )
                
                # Clean up intermediate file if different
                if normalized_path != enhanced_path and normalized_path != file_path:
                    cleanup_temp_files([normalized_path])
                
                return enhanced_path
                
            except (ImageValidationError, ImageProcessingError) as e:
                raise FileProcessingError(f"Image processing failed: {str(e)}")
                
        elif file_type == 'pdf':
            # Convert PDF to image for analysis
            try:
                image_path = convert_pdf_to_image_for_analysis(
                    file_path,
                    page_number=page_number,
                    dpi=300,
                    enhance_for_ocr=True
                )
                
                return image_path
                
            except PDFProcessingError as e:
                raise FileProcessingError(f"PDF processing failed: {str(e)}")
                
        else:
            raise FileProcessingError(f"Unsupported file type for analysis: {file_type}")
        
    except FileProcessingError:
        raise
    except Exception as e:
        raise FileProcessingError(f"File preparation failed: {str(e)}")


def get_file_info(file_path: str) -> Dict[str, Any]:
    """
    Get comprehensive information about a file (image or PDF).
    
    Args:
        file_path: Path to the file
        
    Returns:
        Dictionary with file information
        
    Raises:
        FileProcessingError: If processing fails
    """
    try:
        file_type = get_file_type(file_path)
        
        base_info = {
            'file_path': file_path,
            'file_type': file_type,
            'file_size': os.path.getsize(file_path),
            'filename': os.path.basename(file_path),
            'extension': Path(file_path).suffix.lower()
        }
        
        if file_type == 'image':
            from .image_utils import get_image_info
            try:
                image_info = get_image_info(file_path)
                base_info.update(image_info)
                base_info['analysis_ready'] = True
                base_info['pages'] = 1
            except Exception as e:
                logger.warning(f"Could not get image info: {str(e)}")
                base_info['analysis_ready'] = False
                
        elif file_type == 'pdf':
            from .pdf_utils import get_pdf_info
            try:
                pdf_info = get_pdf_info(file_path)
                base_info.update(pdf_info)
                base_info['analysis_ready'] = True
                base_info['pages'] = pdf_info.get('page_count', 1)
            except Exception as e:
                logger.warning(f"Could not get PDF info: {str(e)}")
                base_info['analysis_ready'] = False
                base_info['pages'] = 1
                
        else:
            base_info['analysis_ready'] = False
            base_info['pages'] = 0
            base_info['error'] = f"Unsupported file type: {file_type}"
        
        return base_info
        
    except Exception as e:
        raise FileProcessingError(f"Failed to get file info: {str(e)}")


def get_supported_file_types() -> Dict[str, List[str]]:
    """
    Get list of supported file types and their extensions.
    
    Returns:
        Dictionary mapping file types to supported extensions
    """
    return {
        'image': ['.jpg', '.jpeg', '.png', '.tiff', '.tif', '.bmp', '.webp'],
        'pdf': ['.pdf']
    }


def is_supported_file_type(filename: str) -> bool:
    """
    Check if a filename has a supported extension.
    
    Args:
        filename: Name of the file
        
    Returns:
        True if supported, False otherwise
    """
    supported = get_supported_file_types()
    extension = Path(filename).suffix.lower()
    
    for file_type, extensions in supported.items():
        if extension in extensions:
            return True
    
    return False


def get_content_type_from_file(file_path: str) -> str:
    """
    Get MIME content type from file.
    
    Args:
        file_path: Path to the file
        
    Returns:
        MIME content type string
    """
    file_type = get_file_type(file_path)
    extension = Path(file_path).suffix.lower()
    
    # Content type mapping
    content_types = {
        'image': {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.tiff': 'image/tiff',
            '.tif': 'image/tiff',
            '.bmp': 'image/bmp',
            '.webp': 'image/webp',
            '.gif': 'image/gif'
        },
        'pdf': {
            '.pdf': 'application/pdf'
        }
    }
    
    if file_type in content_types and extension in content_types[file_type]:
        return content_types[file_type][extension]
    
    # Fallback
    if file_type == 'image':
        return 'image/jpeg'  # Default image type
    elif file_type == 'pdf':
        return 'application/pdf'
    
    return 'application/octet-stream'


class TempAnalysisFile:
    """Context manager for temporary files prepared for analysis."""
    
    def __init__(self, source_path: str, page_number: int = 1):
        self.source_path = source_path
        self.page_number = page_number
        self.temp_path = None
        self.needs_cleanup = False
    
    def __enter__(self):
        """Prepare file for analysis and return path to temporary file."""
        try:
            self.temp_path = prepare_file_for_analysis(self.source_path, self.page_number)
            
            # Check if we created a new temporary file or if it's the same as source
            self.needs_cleanup = (self.temp_path != self.source_path)
            
            return self.temp_path
            
        except Exception as e:
            logger.error(f"Failed to prepare file for analysis: {str(e)}")
            raise
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Clean up temporary file if needed."""
        if self.needs_cleanup and self.temp_path and os.path.exists(self.temp_path):
            try:
                cleanup_temp_files([self.temp_path])
            except Exception as e:
                logger.warning(f"Failed to clean up temporary analysis file: {str(e)}")


def validate_file_upload(filename: str, content_type: str, file_size: int) -> bool:
    """
    Validate file upload parameters.
    
    Args:
        filename: Name of the uploaded file
        content_type: MIME content type
        file_size: Size of the file in bytes
        
    Returns:
        True if valid, raises exception if invalid
        
    Raises:
        FileValidationError: If validation fails
    """
    # Check filename
    if not filename:
        raise FileValidationError("Filename is required")
    
    # Check if file type is supported
    if not is_supported_file_type(filename):
        supported = get_supported_file_types()
        all_extensions = []
        for extensions in supported.values():
            all_extensions.extend(extensions)
        raise FileValidationError(
            f"Unsupported file type. Supported extensions: {', '.join(all_extensions)}"
        )
    
    # Check content type
    allowed_content_types = [
        'image/jpeg', 'image/jpg', 'image/png', 'image/tiff', 'image/bmp', 'image/webp',
        'application/pdf'
    ]
    
    if content_type not in allowed_content_types:
        raise FileValidationError(
            f"Unsupported content type: {content_type}. Allowed types: {', '.join(allowed_content_types)}"
        )
    
    # Check file size (50MB limit)
    max_size = 50 * 1024 * 1024
    if file_size > max_size:
        raise FileValidationError(
            f"File too large: {file_size} bytes (max: {max_size} bytes)"
        )
    
    return True
