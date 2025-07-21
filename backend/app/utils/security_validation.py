import os
import tempfile
import logging
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path
import magic
from PIL import Image
import PyPDF2
from fastapi import UploadFile, HTTPException
import hashlib

logger = logging.getLogger(__name__)


class SecurityValidationError(Exception):
    """Exception raised for security validation errors."""
    pass


class FileSecurityValidator:
    """Comprehensive file security validation using content analysis."""
    
    # Magic number signatures for allowed file types
    ALLOWED_SIGNATURES = {
        # JPEG
        b'\xFF\xD8\xFF': 'image/jpeg',
        # PNG
        b'\x89PNG\r\n\x1a\n': 'image/png',
        # PDF
        b'%PDF-': 'application/pdf',
        # TIFF (little endian)
        b'II*\x00': 'image/tiff',
        # TIFF (big endian)
        b'MM\x00*': 'image/tiff',
        # BMP
        b'BM': 'image/bmp',
        # WebP
        b'RIFF': 'image/webp',  # Note: WebP has WEBP in bytes 8-11
    }
    
    # Maximum file sizes per type (in bytes)
    MAX_FILE_SIZES = {
        'image/jpeg': 50 * 1024 * 1024,  # 50MB
        'image/png': 50 * 1024 * 1024,   # 50MB
        'image/tiff': 100 * 1024 * 1024, # 100MB (TIFF can be large)
        'image/bmp': 50 * 1024 * 1024,   # 50MB
        'image/webp': 50 * 1024 * 1024,  # 50MB
        'application/pdf': 20 * 1024 * 1024,  # 20MB
    }
    
    # Dangerous file patterns to block
    DANGEROUS_PATTERNS = [
        # Executable files
        b'MZ',  # PE/COFF executables
        b'\x7fELF',  # ELF executables
        b'\xCA\xFE\xBA\xBE',  # Java class files
        b'\xFE\xED\xFA\xCE',  # Mach-O executables
        # Script files
        b'#!/',  # Shell scripts
        b'<?php',  # PHP scripts
        b'<script',  # HTML/JS scripts (case insensitive handled separately)
        # Archive files that could contain malware
        b'PK\x03\x04',  # ZIP files
        b'Rar!',  # RAR files
        b'\x1f\x8b',  # GZIP files
    ]
    
    def __init__(self):
        """Initialize the security validator."""
        try:
            # Initialize python-magic if available
            self.magic_mime = magic.Magic(mime=True)
            self.magic_available = True
        except Exception as e:
            logger.warning(f"python-magic not available, falling back to manual validation: {e}")
            self.magic_available = False

    async def validate_file_content(self, file_content: bytes, filename: str, declared_mime_type: str) -> Dict[str, Any]:
        """
        Validate file content using multiple security checks.
        
        Args:
            file_content: Raw file content bytes
            filename: Original filename
            declared_mime_type: MIME type declared by client
            
        Returns:
            Dictionary with validation results
            
        Raises:
            SecurityValidationError: If validation fails
        """
        logger.info(f"Validating file content for: {filename}")
        
        # Check file size
        file_size = len(file_content)
        self._validate_file_size(file_size, declared_mime_type)
        
        # Detect actual MIME type from content
        actual_mime_type = self._detect_mime_type(file_content, filename)
        
        # Validate MIME type consistency
        self._validate_mime_type_consistency(declared_mime_type, actual_mime_type, filename)
        
        # Check for dangerous content patterns
        self._check_dangerous_patterns(file_content, filename)
        
        # Perform deep content validation
        validation_result = await self._deep_content_validation(file_content, actual_mime_type, filename)
        
        # Scan for malware
        try:
            from .malware_scanner import scan_file_for_malware, MalwareDetected
            malware_scan_result = await scan_file_for_malware(file_content, filename)
            validation_result['malware_scan'] = malware_scan_result
        except MalwareDetected as e:
            raise SecurityValidationError(f"Malware detected in {filename}: {str(e)}")
        except Exception as e:
            logger.warning(f"Malware scan failed for {filename}: {str(e)}")
            validation_result['malware_scan'] = {
                'scanned': False,
                'error': str(e),
                'clean': None
            }
        
        # Calculate file hash for integrity tracking
        file_hash = hashlib.sha256(file_content).hexdigest()
        
        result = {
            'filename': filename,
            'declared_mime_type': declared_mime_type,
            'actual_mime_type': actual_mime_type,
            'file_size': file_size,
            'file_hash': file_hash,
            'validation_passed': True,
            'validation_details': validation_result
        }
        
        logger.info(f"File validation passed for: {filename}")
        return result

    def _validate_file_size(self, file_size: int, mime_type: str) -> None:
        """Validate file size against type-specific limits."""
        if file_size == 0:
            raise SecurityValidationError("File is empty")
        
        max_size = self.MAX_FILE_SIZES.get(mime_type, 10 * 1024 * 1024)  # Default 10MB
        
        if file_size > max_size:
            raise SecurityValidationError(
                f"File too large: {file_size} bytes (max: {max_size} bytes for {mime_type})"
            )

    def _detect_mime_type(self, file_content: bytes, filename: str) -> str:
        """Detect MIME type from file content using magic numbers."""
        # Check magic numbers first
        for signature, mime_type in self.ALLOWED_SIGNATURES.items():
            if file_content.startswith(signature):
                # Special case for WebP - need to check additional bytes
                if mime_type == 'image/webp' and len(file_content) >= 12:
                    if file_content[8:12] == b'WEBP':
                        return mime_type
                elif mime_type != 'image/webp':
                    return mime_type
        
        # Use python-magic if available
        if self.magic_available:
            try:
                with tempfile.NamedTemporaryFile() as temp_file:
                    temp_file.write(file_content)
                    temp_file.flush()
                    detected_mime = self.magic_mime.from_file(temp_file.name)
                    
                    # Map common variations
                    mime_mappings = {
                        'image/jpeg': 'image/jpeg',
                        'image/jpg': 'image/jpeg',
                        'image/png': 'image/png',
                        'image/tiff': 'image/tiff',
                        'image/bmp': 'image/bmp',
                        'image/webp': 'image/webp',
                        'application/pdf': 'application/pdf',
                    }
                    
                    return mime_mappings.get(detected_mime, detected_mime)
                    
            except Exception as e:
                logger.warning(f"Magic MIME detection failed: {e}")
        
        # Fallback to extension-based detection
        extension = Path(filename).suffix.lower()
        extension_mappings = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.pdf': 'application/pdf',
            '.tiff': 'image/tiff',
            '.tif': 'image/tiff',
            '.bmp': 'image/bmp',
            '.webp': 'image/webp',
        }
        
        detected_type = extension_mappings.get(extension)
        if not detected_type:
            raise SecurityValidationError(f"Unsupported file type: {extension}")
        
        return detected_type

    def _validate_mime_type_consistency(self, declared: str, actual: str, filename: str) -> None:
        """Validate that declared and actual MIME types are consistent."""
        # Normalize MIME types
        mime_aliases = {
            'image/jpg': 'image/jpeg',
        }
        
        normalized_declared = mime_aliases.get(declared, declared)
        normalized_actual = mime_aliases.get(actual, actual)
        
        if normalized_declared != normalized_actual:
            raise SecurityValidationError(
                f"MIME type mismatch for {filename}: declared '{declared}' but content is '{actual}'"
            )
        
        # Validate against allowed types
        allowed_types = set(self.MAX_FILE_SIZES.keys())
        if normalized_actual not in allowed_types:
            raise SecurityValidationError(
                f"Unsupported MIME type: {actual}. Allowed types: {', '.join(allowed_types)}"
            )

    def _check_dangerous_patterns(self, file_content: bytes, filename: str) -> None:
        """Check for dangerous content patterns."""
        # Check for executable signatures
        for pattern in self.DANGEROUS_PATTERNS:
            if pattern in file_content:
                raise SecurityValidationError(
                    f"Dangerous content pattern detected in {filename}"
                )
        
        # Check for script content (case insensitive)
        content_lower = file_content.lower()
        dangerous_scripts = [
            b'<script',
            b'javascript:',
            b'vbscript:',
            b'onload=',
            b'onerror=',
            b'<?php',
            b'<%',
        ]
        
        for pattern in dangerous_scripts:
            if pattern in content_lower:
                raise SecurityValidationError(
                    f"Script content detected in {filename}"
                )
        
        # Check for embedded executables in images
        if b'MZ' in file_content[100:]:  # Skip legitimate image headers
            raise SecurityValidationError(
                f"Embedded executable detected in {filename}"
            )

    async def _deep_content_validation(self, file_content: bytes, mime_type: str, filename: str) -> Dict[str, Any]:
        """Perform deep content validation specific to file type."""
        if mime_type.startswith('image/'):
            return self._validate_image_content(file_content, mime_type, filename)
        elif mime_type == 'application/pdf':
            return self._validate_pdf_content(file_content, filename)
        else:
            raise SecurityValidationError(f"No deep validation available for {mime_type}")

    def _validate_image_content(self, file_content: bytes, mime_type: str, filename: str) -> Dict[str, Any]:
        """Validate image content using PIL."""
        try:
            with tempfile.NamedTemporaryFile() as temp_file:
                temp_file.write(file_content)
                temp_file.flush()
                
                # Try to open and validate with PIL
                with Image.open(temp_file.name) as img:
                    # Verify image can be loaded
                    img.verify()
                
                # Re-open for getting info (verify() closes the image)
                with Image.open(temp_file.name) as img:
                    width, height = img.size
                    format_name = img.format
                    mode = img.mode
                    
                    # Sanity checks
                    if width <= 0 or height <= 0:
                        raise SecurityValidationError(f"Invalid image dimensions: {width}x{height}")
                    
                    if width > 50000 or height > 50000:
                        raise SecurityValidationError(f"Image dimensions too large: {width}x{height}")
                    
                    return {
                        'width': width,
                        'height': height,
                        'format': format_name,
                        'mode': mode,
                        'validation_method': 'PIL'
                    }
                    
        except Exception as e:
            raise SecurityValidationError(f"Image validation failed for {filename}: {str(e)}")

    def _validate_pdf_content(self, file_content: bytes, filename: str) -> Dict[str, Any]:
        """Validate PDF content."""
        try:
            with tempfile.NamedTemporaryFile() as temp_file:
                temp_file.write(file_content)
                temp_file.flush()
                
                # Try to read with PyPDF2
                with open(temp_file.name, 'rb') as pdf_file:
                    pdf_reader = PyPDF2.PdfReader(pdf_file)
                    
                    page_count = len(pdf_reader.pages)
                    
                    if page_count <= 0:
                        raise SecurityValidationError("PDF has no pages")
                    
                    if page_count > 100:  # Reasonable limit
                        raise SecurityValidationError(f"PDF has too many pages: {page_count}")
                    
                    # Check for JavaScript or other executable content
                    for page_num, page in enumerate(pdf_reader.pages):
                        try:
                            text = page.extract_text().lower()
                            dangerous_content = ['javascript', '/js', '/action', 'eval(']
                            
                            for dangerous in dangerous_content:
                                if dangerous in text:
                                    raise SecurityValidationError(
                                        f"Potentially dangerous content in PDF page {page_num + 1}"
                                    )
                        except Exception:
                            # If text extraction fails, continue
                            pass
                    
                    return {
                        'page_count': page_count,
                        'validation_method': 'PyPDF2'
                    }
                    
        except SecurityValidationError:
            raise
        except Exception as e:
            raise SecurityValidationError(f"PDF validation failed for {filename}: {str(e)}")


# Global validator instance
security_validator = FileSecurityValidator()


def validate_upload_security(file: UploadFile) -> Dict[str, Any]:
    """
    Validate uploaded file for security threats.
    
    Args:
        file: FastAPI UploadFile object
        
    Returns:
        Dictionary with validation results
        
    Raises:
        SecurityValidationError: If validation fails
        HTTPException: If file cannot be processed
    """
    try:
        # Read file content
        file.file.seek(0)  # Ensure we're at the beginning
        file_content = file.file.read()
        file.file.seek(0)  # Reset for any subsequent reads
        
        if not file_content:
            raise SecurityValidationError("File is empty")
        
        # Perform security validation
        result = await security_validator.validate_file_content(
            file_content=file_content,
            filename=file.filename or "unknown",
            declared_mime_type=file.content_type or "application/octet-stream"
        )
        
        return result
        
    except SecurityValidationError:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during security validation: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="File security validation failed"
        )