import os
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
import PyPDF2
import fitz  # PyMuPDF
from pdf2image import convert_from_path
from PIL import Image
import io

from .image_utils import (
    cleanup_temp_files
)

logger = logging.getLogger(__name__)


class PDFValidationError(Exception):
    """Exception raised for PDF validation errors."""
    pass


class PDFProcessingError(Exception):
    """Exception raised for PDF processing errors."""
    pass


def validate_pdf_file(file_path: str) -> Dict[str, Any]:
    """
    Validate PDF file format, size, and properties.
    
    Args:
        file_path: Path to the PDF file
        
    Returns:
        Dictionary with validation results
        
    Raises:
        PDFValidationError: If validation fails
    """
    try:
        if not os.path.exists(file_path):
            raise PDFProcessingError(f"PDF file not found: {file_path}")
        
        # Check file size
        file_size = os.path.getsize(file_path)
        max_size = 50 * 1024 * 1024  # 50MB
        
        if file_size > max_size:
            raise PDFValidationError(f"PDF file too large: {file_size} bytes (max: {max_size} bytes)")
        
        # Try to open with PyPDF2 for basic validation
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                num_pages = len(pdf_reader.pages)
                
                # Check page count
                max_pages = 10  # Reasonable limit for check images
                if num_pages > max_pages:
                    raise PDFValidationError(f"PDF has too many pages: {num_pages} (max: {max_pages})")
                
                # Check if PDF is encrypted
                if pdf_reader.is_encrypted:
                    raise PDFValidationError("Encrypted PDFs are not supported")
                
                # Get metadata
                metadata = pdf_reader.metadata or {}
                
        except PyPDF2.errors.PdfReadError as e:
            raise PDFValidationError(f"Invalid PDF file: {str(e)}")
        
        # Additional validation with PyMuPDF for more detailed info
        try:
            doc = fitz.open(file_path)
            
            # Check if document is valid
            if doc.is_closed:
                raise PDFValidationError("PDF document appears to be corrupted")
            
            # Get additional metadata
            doc_metadata = doc.metadata
            doc.close()
            
        except Exception as e:
            logger.warning(f"PyMuPDF validation failed: {str(e)}")
            doc_metadata = {}
        
        return {
            'valid': True,
            'format': 'PDF',
            'file_size': file_size,
            'page_count': num_pages,
            'is_encrypted': False,
            'metadata': {
                'title': metadata.get('/Title', ''),
                'author': metadata.get('/Author', ''),
                'subject': metadata.get('/Subject', ''),
                'creator': metadata.get('/Creator', ''),
                'producer': metadata.get('/Producer', ''),
                'creation_date': str(metadata.get('/CreationDate', '')),
                'modification_date': str(metadata.get('/ModDate', ''))
            },
            'mupdf_metadata': doc_metadata
        }
        
    except PDFValidationError:
        raise
    except PDFProcessingError:
        raise
    except Exception as e:
        raise PDFValidationError(f"PDF validation failed: {str(e)}")


def extract_pdf_metadata(file_path: str) -> Dict[str, Any]:
    """
    Extract comprehensive metadata from PDF file.
    
    Args:
        file_path: Path to the PDF file
        
    Returns:
        Dictionary with metadata information
        
    Raises:
        PDFProcessingError: If processing fails
    """
    try:
        metadata = {}
        
        # Extract metadata with PyPDF2
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                pdf_metadata = pdf_reader.metadata or {}
                
                metadata['basic'] = {
                    'page_count': len(pdf_reader.pages),
                    'is_encrypted': pdf_reader.is_encrypted,
                    'title': pdf_metadata.get('/Title', ''),
                    'author': pdf_metadata.get('/Author', ''),
                    'subject': pdf_metadata.get('/Subject', ''),
                    'creator': pdf_metadata.get('/Creator', ''),
                    'producer': pdf_metadata.get('/Producer', ''),
                    'creation_date': str(pdf_metadata.get('/CreationDate', '')),
                    'modification_date': str(pdf_metadata.get('/ModDate', ''))
                }
                
        except Exception as e:
            logger.warning(f"PyPDF2 metadata extraction failed: {str(e)}")
            metadata['basic'] = {}
        
        # Extract detailed metadata with PyMuPDF
        try:
            doc = fitz.open(file_path)
            
            metadata['detailed'] = {
                'page_count': doc.page_count,
                'is_pdf': doc.is_pdf,
                'needs_pass': doc.needs_pass,
                'is_encrypted': doc.is_encrypted,
                'permissions': doc.permissions,
                'metadata': doc.metadata,
                'toc': doc.get_toc(),
                'page_sizes': []
            }
            
            # Get page dimensions
            for page_num in range(min(doc.page_count, 5)):  # Limit to first 5 pages
                page = doc[page_num]
                rect = page.rect
                metadata['detailed']['page_sizes'].append({
                    'page': page_num + 1,
                    'width': rect.width,
                    'height': rect.height,
                    'rotation': page.rotation
                })
            
            doc.close()
            
        except Exception as e:
            logger.warning(f"PyMuPDF metadata extraction failed: {str(e)}")
            metadata['detailed'] = {}
        
        return metadata
        
    except Exception as e:
        raise PDFProcessingError(f"Failed to extract PDF metadata: {str(e)}")


def convert_pdf_to_images(file_path: str, 
                         dpi: int = 300,
                         output_format: str = 'JPEG',
                         quality: int = 90,
                         first_page: Optional[int] = None,
                         last_page: Optional[int] = None) -> List[str]:
    """
    Convert PDF pages to images.
    
    Args:
        file_path: Path to the PDF file
        dpi: Resolution in DPI for conversion
        output_format: Output image format ('JPEG', 'PNG')
        quality: JPEG quality (1-100)
        first_page: First page to convert (1-indexed)
        last_page: Last page to convert (1-indexed)
        
    Returns:
        List of paths to converted image files
        
    Raises:
        PDFProcessingError: If conversion fails
    """
    try:
        # Validate PDF first
        validate_pdf_file(file_path)
        
        # Convert PDF to images
        images = convert_from_path(
            file_path,
            dpi=dpi,
            first_page=first_page,
            last_page=last_page,
            fmt=output_format.lower()
        )
        
        if not images:
            raise PDFProcessingError("No pages could be converted from PDF")
        
        # Save images to temporary files
        output_paths = []
        file_path_obj = Path(file_path)
        
        for i, image in enumerate(images):
            page_num = (first_page or 1) + i
            output_path = file_path_obj.with_suffix(f'.page{page_num}.{output_format.lower()}')
            
            # Save image
            save_kwargs = {}
            if output_format.upper() == 'JPEG':
                save_kwargs['quality'] = quality
                save_kwargs['optimize'] = True
            elif output_format.upper() == 'PNG':
                save_kwargs['optimize'] = True
            
            image.save(output_path, format=output_format, **save_kwargs)
            output_paths.append(str(output_path))
        
        return output_paths
        
    except Exception as e:
        raise PDFProcessingError(f"PDF to image conversion failed: {str(e)}")


def convert_pdf_to_images_mupdf(file_path: str,
                               dpi: int = 300,
                               output_format: str = 'JPEG',
                               quality: int = 90,
                               first_page: Optional[int] = None,
                               last_page: Optional[int] = None) -> List[str]:
    """
    Convert PDF pages to images using PyMuPDF (alternative method).
    
    Args:
        file_path: Path to the PDF file
        dpi: Resolution in DPI for conversion
        output_format: Output image format ('JPEG', 'PNG')
        quality: JPEG quality (1-100)
        first_page: First page to convert (0-indexed for PyMuPDF)
        last_page: Last page to convert (0-indexed for PyMuPDF)
        
    Returns:
        List of paths to converted image files
        
    Raises:
        PDFProcessingError: If conversion fails
    """
    try:
        # Validate PDF first
        validate_pdf_file(file_path)
        
        # Open PDF with PyMuPDF
        doc = fitz.open(file_path)
        
        # Determine page range
        start_page = (first_page - 1) if first_page else 0
        end_page = (last_page - 1) if last_page else doc.page_count - 1
        
        # Ensure valid range
        start_page = max(0, start_page)
        end_page = min(doc.page_count - 1, end_page)
        
        if start_page > end_page:
            raise PDFProcessingError(f"Invalid page range: {start_page+1} to {end_page+1}")
        
        output_paths = []
        file_path_obj = Path(file_path)
        
        # Convert each page
        for page_num in range(start_page, end_page + 1):
            page = doc[page_num]
            
            # Create matrix for scaling (DPI)
            mat = fitz.Matrix(dpi / 72, dpi / 72)
            
            # Render page to pixmap
            pix = page.get_pixmap(matrix=mat, alpha=False)
            
            # Convert to PIL Image
            img_data = pix.tobytes("png")
            image = Image.open(io.BytesIO(img_data))
            
            # Convert to RGB if needed for JPEG
            if output_format.upper() == 'JPEG' and image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Generate output path
            output_path = file_path_obj.with_suffix(f'.page{page_num+1}.{output_format.lower()}')
            
            # Save image
            save_kwargs = {}
            if output_format.upper() == 'JPEG':
                save_kwargs['quality'] = quality
                save_kwargs['optimize'] = True
            elif output_format.upper() == 'PNG':
                save_kwargs['optimize'] = True
            
            image.save(output_path, format=output_format, **save_kwargs)
            output_paths.append(str(output_path))
        
        doc.close()
        return output_paths
        
    except Exception as e:
        raise PDFProcessingError(f"PDF to image conversion (PyMuPDF) failed: {str(e)}")


def extract_text_from_pdf(file_path: str, 
                         page_numbers: Optional[List[int]] = None) -> Dict[str, Any]:
    """
    Extract text from PDF pages.
    
    Args:
        file_path: Path to the PDF file
        page_numbers: List of page numbers to extract from (1-indexed), None for all pages
        
    Returns:
        Dictionary with extracted text and metadata
        
    Raises:
        PDFProcessingError: If extraction fails
    """
    try:
        # Validate PDF first
        validate_pdf_file(file_path)
        
        result = {
            'pages': {},
            'full_text': '',
            'metadata': {}
        }
        
        # Extract with PyPDF2
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                pages_to_process = page_numbers or list(range(1, len(pdf_reader.pages) + 1))
                
                for page_num in pages_to_process:
                    if 1 <= page_num <= len(pdf_reader.pages):
                        page = pdf_reader.pages[page_num - 1]
                        text = page.extract_text()
                        result['pages'][page_num] = {
                            'text': text,
                            'method': 'PyPDF2'
                        }
                        result['full_text'] += text + '\n'
                
        except Exception as e:
            logger.warning(f"PyPDF2 text extraction failed: {str(e)}")
        
        # Extract with PyMuPDF (more accurate)
        try:
            doc = fitz.open(file_path)
            
            pages_to_process = page_numbers or list(range(1, doc.page_count + 1))
            
            for page_num in pages_to_process:
                if 1 <= page_num <= doc.page_count:
                    page = doc[page_num - 1]
                    text = page.get_text()
                    
                    # If we didn't get text from PyPDF2 or PyMuPDF is better
                    if page_num not in result['pages'] or len(text) > len(result['pages'][page_num]['text']):
                        result['pages'][page_num] = {
                            'text': text,
                            'method': 'PyMuPDF'
                        }
                    
                    # Update full text (replace or append)
                    if page_num not in result['pages'] or result['pages'][page_num]['method'] == 'PyMuPDF':
                        # Rebuild full text with PyMuPDF version
                        result['full_text'] = '\n'.join([
                            result['pages'][p]['text'] for p in sorted(result['pages'].keys())
                        ])
            
            # Get text blocks with position info
            for page_num in pages_to_process:
                if 1 <= page_num <= doc.page_count:
                    page = doc[page_num - 1]
                    blocks = page.get_text("dict")
                    
                    if page_num in result['pages']:
                        result['pages'][page_num]['blocks'] = blocks
            
            doc.close()
            
        except Exception as e:
            logger.warning(f"PyMuPDF text extraction failed: {str(e)}")
        
        return result
        
    except Exception as e:
        raise PDFProcessingError(f"PDF text extraction failed: {str(e)}")


def get_pdf_info(file_path: str) -> Dict[str, Any]:
    """
    Get comprehensive information about a PDF file.
    
    Args:
        file_path: Path to the PDF file
        
    Returns:
        Dictionary with PDF information
        
    Raises:
        PDFProcessingError: If processing fails
    """
    try:
        # Start with validation results
        validation_result = validate_pdf_file(file_path)
        
        # Add metadata
        metadata = extract_pdf_metadata(file_path)
        
        # Combine all information
        info = {
            'file_path': file_path,
            'file_size': validation_result['file_size'],
            'format': validation_result['format'],
            'page_count': validation_result['page_count'],
            'is_encrypted': validation_result['is_encrypted'],
            'validation': validation_result,
            'metadata': metadata,
            'can_convert_to_images': True,
            'can_extract_text': True
        }
        
        return info
        
    except Exception as e:
        raise PDFProcessingError(f"Failed to get PDF info: {str(e)}")


def convert_pdf_to_image_for_analysis(file_path: str, 
                                     page_number: int = 1,
                                     dpi: int = 300,
                                     enhance_for_ocr: bool = True) -> str:
    """
    Convert a specific PDF page to an image optimized for analysis.
    
    Args:
        file_path: Path to the PDF file
        page_number: Page number to convert (1-indexed)
        dpi: Resolution for conversion
        enhance_for_ocr: Whether to enhance the image for OCR
        
    Returns:
        Path to the converted and enhanced image file
        
    Raises:
        PDFProcessingError: If conversion fails
    """
    try:
        # Convert single page to image
        image_paths = convert_pdf_to_images(
            file_path,
            dpi=dpi,
            output_format='JPEG',
            quality=95,
            first_page=page_number,
            last_page=page_number
        )
        
        if not image_paths:
            raise PDFProcessingError(f"Failed to convert PDF page {page_number}")
        
        image_path = image_paths[0]
        
        # Enhance for analysis if requested
        if enhance_for_ocr:
            from .image_utils import enhance_image_quality, normalize_image_format
            
            # Normalize format
            normalized_path = normalize_image_format(image_path, 'JPEG', quality=95)
            
            # Enhance for better OCR/analysis
            enhanced_path = enhance_image_quality(
                normalized_path,
                enhance_contrast=True,
                enhance_sharpness=True,
                enhance_brightness=False
            )
            
            # Clean up intermediate files
            if image_path != normalized_path:
                cleanup_temp_files([image_path])
            if normalized_path != enhanced_path:
                cleanup_temp_files([normalized_path])
            
            return enhanced_path
        
        return image_path
        
    except Exception as e:
        raise PDFProcessingError(f"PDF to analysis image conversion failed: {str(e)}")


def is_pdf_file(file_path: str) -> bool:
    """
    Check if a file is a PDF.
    
    Args:
        file_path: Path to the file
        
    Returns:
        True if file is a PDF, False otherwise
    """
    try:
        # Check file extension
        if not file_path.lower().endswith('.pdf'):
            return False
        
        # Check file header
        with open(file_path, 'rb') as f:
            header = f.read(4)
            return header == b'%PDF'
    
    except Exception:
        return False


def get_pdf_page_count(file_path: str) -> int:
    """
    Get the number of pages in a PDF file.
    
    Args:
        file_path: Path to the PDF file
        
    Returns:
        Number of pages
        
    Raises:
        PDFProcessingError: If unable to read PDF
    """
    try:
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            return len(pdf_reader.pages)
    
    except Exception as e:
        raise PDFProcessingError(f"Failed to get PDF page count: {str(e)}")


class TempPDFImageFiles:
    """Context manager for temporary PDF-to-image conversion files."""
    
    def __init__(self, pdf_path: str, dpi: int = 300, format: str = 'JPEG'):
        self.pdf_path = pdf_path
        self.dpi = dpi
        self.format = format
        self.image_paths = []
    
    def __enter__(self):
        """Convert PDF to images and return list of image paths."""
        try:
            self.image_paths = convert_pdf_to_images(
                self.pdf_path,
                dpi=self.dpi,
                output_format=self.format,
                quality=95
            )
            return self.image_paths
        except Exception as e:
            logger.error(f"Failed to convert PDF to images: {str(e)}")
            raise
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Clean up temporary image files."""
        cleanup_temp_files(self.image_paths)


def cleanup_pdf_temp_files(file_paths: list):
    """
    Clean up temporary PDF-related files.
    
    Args:
        file_paths: List of file paths to clean up
    """
    if file_paths is None:
        return
    
    for file_path in file_paths:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.debug(f"Cleaned up temporary PDF file: {file_path}")
        except Exception as e:
            logger.warning(f"Failed to clean up PDF file {file_path}: {str(e)}")


def validate_and_process_pdf(file_path: str) -> Dict[str, Any]:
    """
    Validate PDF and prepare it for analysis.
    
    Args:
        file_path: Path to the PDF file
        
    Returns:
        Dictionary with validation results and processing info
        
    Raises:
        PDFValidationError: If validation fails
        PDFProcessingError: If processing fails
    """
    try:
        # Validate PDF
        validation_result = validate_pdf_file(file_path)
        
        if not validation_result['valid']:
            raise PDFValidationError("PDF validation failed")
        
        # Get additional info
        pdf_info = get_pdf_info(file_path)
        
        # Determine optimal processing strategy
        processing_strategy = {
            'convert_to_images': True,
            'extract_text': True,
            'recommended_dpi': 300 if pdf_info['page_count'] <= 5 else 200,
            'pages_to_process': min(pdf_info['page_count'], 5),  # Limit processing
            'enhance_for_ocr': True
        }
        
        return {
            'validation': validation_result,
            'info': pdf_info,
            'strategy': processing_strategy
        }
        
    except Exception as e:
        raise PDFProcessingError(f"PDF validation and processing preparation failed: {str(e)}")
