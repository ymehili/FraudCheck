"""
Streaming file processing utilities for memory-bounded analysis.

This module provides streaming file validation, chunked processing, and progress
tracking for large files to prevent memory exhaustion during analysis.

Security validation is handled exclusively by ClamAV daemon integration.
"""

import os
import logging
import asyncio
import aiofiles
import tempfile
from typing import Optional, Callable
from pathlib import Path
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Constants for streaming processing
DEFAULT_CHUNK_SIZE = 8192  # 8KB chunks as specified in PRP
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB as specified in success criteria


@dataclass
class StreamValidationResult:
    """Result of streaming file validation."""
    valid: bool
    file_size: int
    file_type: Optional[str] = None
    validation_time_seconds: float = 0.0
    chunks_processed: int = 0
    error_message: Optional[str] = None


@dataclass
class StreamProgress:
    """Progress information for streaming operations."""
    phase: str
    bytes_processed: int
    total_bytes: int
    progress_percentage: float
    chunks_processed: int
    estimated_remaining_seconds: Optional[float] = None


class StreamingValidationError(Exception):
    """Exception raised for streaming validation errors."""
    pass


class StreamingProcessingError(Exception):
    """Exception raised for streaming processing errors."""
    pass


async def stream_validate_file(
    file_path: str, 
    max_chunk_size: int = DEFAULT_CHUNK_SIZE,
    progress_callback: Optional[Callable[[StreamProgress], None]] = None
) -> StreamValidationResult:
    """
    Stream-validate file without loading entirely into memory.
    
    Performs basic file validation on chunks without memory exhaustion.
    Security validation is handled separately by ClamAV daemon.
    
    Args:
        file_path: Path to file to validate
        max_chunk_size: Maximum size of chunks to read (default 8KB)
        progress_callback: Optional callback for progress updates
        
    Returns:
        StreamValidationResult with validation outcome
        
    Raises:
        StreamingValidationError: If validation fails
    """
    start_time = asyncio.get_event_loop().time()
    
    try:
        # Check file existence and basic properties
        if not os.path.exists(file_path):
            raise StreamingValidationError(f"File not found: {file_path}")
            
        file_stat = os.stat(file_path)
        total_size = file_stat.st_size
        
        # Check file size limit before processing
        if total_size > MAX_FILE_SIZE:
            raise StreamingValidationError(
                f"File too large: {total_size} bytes (max: {MAX_FILE_SIZE} bytes)"
            )
        
        # Initialize validation state
        bytes_processed = 0
        chunks_processed = 0
        file_header = b""
        detected_file_type = None
        
        # Stream through file in chunks
        async with aiofiles.open(file_path, 'rb') as f:
            while True:
                chunk = await f.read(max_chunk_size)
                if not chunk:
                    break
                    
                bytes_processed += len(chunk)
                chunks_processed += 1
                
                # Collect file header for type detection (first 2KB)
                if len(file_header) < 2048:
                    remaining_header_bytes = 2048 - len(file_header)
                    file_header += chunk[:remaining_header_bytes]
                
                # Basic chunk validation (non-security)
                await _validate_chunk_basic(chunk, chunks_processed)
                
                # Update progress if callback provided
                if progress_callback:
                    progress = StreamProgress(
                        phase="validation",
                        bytes_processed=bytes_processed,
                        total_bytes=total_size,
                        progress_percentage=(bytes_processed / total_size) * 100,
                        chunks_processed=chunks_processed
                    )
                    progress_callback(progress)
                
                # Yield control to event loop every 10 chunks
                if chunks_processed % 10 == 0:
                    await asyncio.sleep(0.001)
        
        # Determine file type from header
        detected_file_type = _detect_file_type_from_header(file_header)
        
        # Validate file type is supported
        if detected_file_type not in ['image', 'pdf']:
            raise StreamingValidationError(
                f"Unsupported file type detected: {detected_file_type}"
            )
        
        end_time = asyncio.get_event_loop().time()
        validation_time = end_time - start_time
        
        return StreamValidationResult(
            valid=True,
            file_size=total_size,
            file_type=detected_file_type,
            validation_time_seconds=validation_time,
            chunks_processed=chunks_processed
        )
        
    except StreamingValidationError:
        raise
    except Exception as e:
        logger.error(f"Streaming validation failed for {file_path}: {str(e)}")
        raise StreamingValidationError(f"Validation failed: {str(e)}")


async def _validate_chunk_basic(chunk: bytes, chunk_number: int) -> None:
    """
    Perform basic chunk validation (non-security checks).
    
    Security validation is handled exclusively by ClamAV daemon.
    
    Args:
        chunk: Bytes to validate
        chunk_number: Sequential chunk number for context
        
    Raises:
        StreamingValidationError: If basic validation fails
    """
    try:
        # Basic sanity checks only
        if len(chunk) == 0:
            raise StreamingValidationError(f"Empty chunk {chunk_number}")
        
        # Check for extremely long lines (potential file corruption)
        lines = chunk.split(b'\n')
        for line in lines:
            if len(line) > 50000:  # 50KB line limit (increased from security check)
                raise StreamingValidationError(
                    f"Corrupted file: extremely long line in chunk {chunk_number}"
                )
                
    except StreamingValidationError:
        raise
    except Exception as e:
        logger.warning(f"Chunk basic validation error: {str(e)}")
        # Don't fail on validation errors, just log them


def _detect_file_type_from_header(header: bytes) -> str:
    """
    Detect file type from file header bytes.
    
    Args:
        header: First bytes of file
        
    Returns:
        Detected file type ('image', 'pdf', 'unknown')
    """
    if not header:
        return 'unknown'
    
    # PDF signature
    if header.startswith(b'%PDF-'):
        return 'pdf'
    
    # Common image signatures
    image_signatures = [
        (b'\xFF\xD8\xFF', 'image'),  # JPEG
        (b'\x89PNG\r\n\x1A\n', 'image'),  # PNG
        (b'GIF87a', 'image'),  # GIF87a
        (b'GIF89a', 'image'),  # GIF89a
        (b'BM', 'image'),  # BMP
        (b'II*\x00', 'image'),  # TIFF (little endian)
        (b'MM\x00*', 'image'),  # TIFF (big endian)
        (b'RIFF', 'image'),  # WebP (check for WEBP later in header)
    ]
    
    for signature, file_type in image_signatures:
        if header.startswith(signature):
            # Special case for WebP
            if signature == b'RIFF' and b'WEBP' in header[:20]:
                return 'image'
            elif signature != b'RIFF':
                return 'image'
    
    return 'unknown'


async def stream_download_file(
    s3_key: str,
    progress_callback: Optional[Callable[[StreamProgress], None]] = None
) -> str:
    """
    Download file from S3 using streaming to prevent memory exhaustion.
    
    Args:
        s3_key: S3 object key
        progress_callback: Optional callback for progress updates
        
    Returns:
        Path to downloaded temporary file
        
    Raises:
        StreamingProcessingError: If download fails
    """
    try:
        from ..core.s3 import s3_service
        import aiohttp
        
        # Generate presigned URL
        download_url = await s3_service.generate_presigned_url(s3_key)
        if not download_url:
            raise StreamingProcessingError("Failed to generate download URL")
        
        # Extract file extension from S3 key
        s3_path = Path(s3_key)
        file_extension = s3_path.suffix or '.tmp'
        
        # Create temporary file
        temp_file = tempfile.NamedTemporaryFile(suffix=file_extension, delete=False)
        temp_path = temp_file.name
        temp_file.close()
        
        # Stream download
        async with aiohttp.ClientSession() as session:
            async with session.get(download_url) as response:
                if response.status != 200:
                    raise StreamingProcessingError(
                        f"Failed to download file from S3: HTTP {response.status}"
                    )
                
                content_length = response.headers.get('Content-Length')
                total_size = int(content_length) if content_length else 0
                bytes_downloaded = 0
                
                async with aiofiles.open(temp_path, 'wb') as f:
                    async for chunk in response.content.iter_chunked(DEFAULT_CHUNK_SIZE):
                        await f.write(chunk)
                        bytes_downloaded += len(chunk)
                        
                        # Update progress
                        if progress_callback and total_size > 0:
                            progress = StreamProgress(
                                phase="downloading",
                                bytes_processed=bytes_downloaded,
                                total_bytes=total_size,
                                progress_percentage=(bytes_downloaded / total_size) * 100,
                                chunks_processed=bytes_downloaded // DEFAULT_CHUNK_SIZE
                            )
                            progress_callback(progress)
                        
                        # Yield control periodically
                        if bytes_downloaded % (DEFAULT_CHUNK_SIZE * 10) == 0:
                            await asyncio.sleep(0.001)
        
        return temp_path
        
    except Exception as e:
        logger.error(f"Stream download failed for {s3_key}: {str(e)}")
        # Clean up temp file on error
        if 'temp_path' in locals() and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except OSError:
                pass
        raise StreamingProcessingError(f"Download failed: {str(e)}")


async def stream_preprocess_file(
    file_path: str,
    page_number: int = 1,
    progress_callback: Optional[Callable[[StreamProgress], None]] = None
) -> str:
    """
    Preprocess file using streaming techniques to avoid memory spikes.
    
    Args:
        file_path: Path to file to preprocess
        page_number: Page number for PDFs
        progress_callback: Optional callback for progress updates
        
    Returns:
        Path to preprocessed file
        
    Raises:
        StreamingProcessingError: If preprocessing fails
    """
    try:
        # First stream-validate the file
        validation_result = await stream_validate_file(
            file_path, 
            progress_callback=progress_callback
        )
        
        if not validation_result.valid:
            raise StreamingProcessingError(
                f"File validation failed: {validation_result.error_message}"
            )
        
        file_type = validation_result.file_type
        
        if file_type == 'image':
            # For images, use existing processing but with memory monitoring
            return await _preprocess_image_streaming(file_path, progress_callback)
            
        elif file_type == 'pdf':
            # For PDFs, use existing conversion but with streaming awareness
            return await _preprocess_pdf_streaming(file_path, page_number, progress_callback)
            
        else:
            raise StreamingProcessingError(f"Unsupported file type: {file_type}")
            
    except StreamingProcessingError:
        raise
    except Exception as e:
        logger.error(f"Stream preprocessing failed for {file_path}: {str(e)}")
        raise StreamingProcessingError(f"Preprocessing failed: {str(e)}")


async def _preprocess_image_streaming(
    file_path: str,
    progress_callback: Optional[Callable[[StreamProgress], None]] = None
) -> str:
    """Preprocess image with streaming awareness."""
    try:
        # Import existing utilities
        from ..utils.image_utils import normalize_image_format, enhance_image_quality
        
        if progress_callback:
            progress_callback(StreamProgress(
                phase="preprocessing",
                bytes_processed=0,
                total_bytes=os.path.getsize(file_path),
                progress_percentage=10.0,
                chunks_processed=0
            ))
        
        # Use existing image processing (already memory-efficient)
        normalized_path = normalize_image_format(file_path, 'JPEG', quality=95)
        
        if progress_callback:
            progress_callback(StreamProgress(
                phase="preprocessing",
                bytes_processed=os.path.getsize(file_path) // 2,
                total_bytes=os.path.getsize(file_path),
                progress_percentage=50.0,
                chunks_processed=0
            ))
        
        enhanced_path = enhance_image_quality(
            normalized_path,
            enhance_contrast=True,
            enhance_sharpness=True,
            enhance_brightness=False
        )
        
        if progress_callback:
            progress_callback(StreamProgress(
                phase="preprocessing",
                bytes_processed=os.path.getsize(file_path),
                total_bytes=os.path.getsize(file_path),
                progress_percentage=100.0,
                chunks_processed=0
            ))
        
        return enhanced_path
        
    except Exception as e:
        raise StreamingProcessingError(f"Image preprocessing failed: {str(e)}")


async def _preprocess_pdf_streaming(
    file_path: str,
    page_number: int,
    progress_callback: Optional[Callable[[StreamProgress], None]] = None
) -> str:
    """Preprocess PDF with streaming awareness."""
    try:
        # Import existing utilities
        from ..utils.pdf_utils import convert_pdf_to_image_for_analysis
        
        if progress_callback:
            progress_callback(StreamProgress(
                phase="preprocessing",
                bytes_processed=0,
                total_bytes=os.path.getsize(file_path),
                progress_percentage=0.0,
                chunks_processed=0
            ))
        
        # Use existing PDF processing
        image_path = convert_pdf_to_image_for_analysis(
            file_path,
            page_number=page_number,
            dpi=300,
            enhance_for_ocr=True
        )
        
        if progress_callback:
            progress_callback(StreamProgress(
                phase="preprocessing",
                bytes_processed=os.path.getsize(file_path),
                total_bytes=os.path.getsize(file_path),
                progress_percentage=100.0,
                chunks_processed=0
            ))
        
        return image_path
        
    except Exception as e:
        raise StreamingProcessingError(f"PDF preprocessing failed: {str(e)}")


async def cleanup_temp_files_background(file_paths: list[str]) -> None:
    """
    Clean up temporary files in background without blocking.
    
    Args:
        file_paths: List of file paths to clean up
    """
    try:
        from ..utils.image_utils import cleanup_temp_files
        
        # Run cleanup in background
        def _cleanup():
            cleanup_temp_files(file_paths)
        
        # Schedule cleanup in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _cleanup)
        
    except Exception as e:
        logger.warning(f"Background cleanup failed: {str(e)}")


class StreamingFileProcessor:
    """Context manager for streaming file processing with automatic cleanup."""
    
    def __init__(
        self,
        s3_key: str,
        page_number: int = 1,
        progress_callback: Optional[Callable[[StreamProgress], None]] = None
    ):
        self.s3_key = s3_key
        self.page_number = page_number
        self.progress_callback = progress_callback
        self.temp_files = []
        self.prepared_path = None
    
    async def __aenter__(self):
        """Download and prepare file for analysis."""
        try:
            # Stream download
            downloaded_path = await stream_download_file(
                self.s3_key,
                self.progress_callback
            )
            self.temp_files.append(downloaded_path)
            
            # Stream preprocess
            self.prepared_path = await stream_preprocess_file(
                downloaded_path,
                self.page_number,
                self.progress_callback
            )
            
            # Track prepared file for cleanup if different
            if self.prepared_path != downloaded_path:
                self.temp_files.append(self.prepared_path)
            
            return self.prepared_path
            
        except Exception:
            # Clean up on error
            await self._cleanup()
            raise
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Clean up temporary files."""
        await self._cleanup()
    
    async def _cleanup(self):
        """Clean up all temporary files."""
        if self.temp_files:
            await cleanup_temp_files_background(self.temp_files)
            self.temp_files.clear()