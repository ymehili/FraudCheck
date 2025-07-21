import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
import io
from fastapi import UploadFile

from app.utils.security_validation import (
    FileSecurityValidator, 
    SecurityValidationError,
    validate_upload_security
)
from app.utils.malware_scanner import MalwareScanner, MalwareDetected


class TestFileSecurityValidator:
    """Test suite for file security validation."""
    
    @pytest.fixture
    def validator(self):
        """Create a validator instance."""
        return FileSecurityValidator()
    
    @pytest.fixture
    def jpeg_content(self):
        """Valid JPEG file content."""
        return b'\xFF\xD8\xFF\xE0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00\xFF\xDB\x00C'
    
    @pytest.fixture
    def png_content(self):
        """Valid PNG file content."""
        return b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde'
    
    @pytest.fixture
    def pdf_content(self):
        """Valid PDF file content."""
        return b'%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n'
    
    @pytest.fixture
    def malicious_content(self):
        """Malicious content (PE executable header)."""
        return b'MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff\x00\x00'

    def test_detect_jpeg_mime_type(self, validator, jpeg_content):
        """Test JPEG MIME type detection."""
        mime_type = validator._detect_mime_type(jpeg_content, 'test.jpg')
        assert mime_type == 'image/jpeg'
    
    def test_detect_png_mime_type(self, validator, png_content):
        """Test PNG MIME type detection."""
        mime_type = validator._detect_mime_type(png_content, 'test.png')
        assert mime_type == 'image/png'
    
    def test_detect_pdf_mime_type(self, validator, pdf_content):
        """Test PDF MIME type detection."""
        mime_type = validator._detect_mime_type(pdf_content, 'test.pdf')
        assert mime_type == 'application/pdf'
    
    def test_mime_type_mismatch_raises_error(self, validator, jpeg_content):
        """Test that MIME type mismatch raises SecurityValidationError."""
        with pytest.raises(SecurityValidationError, match="MIME type mismatch"):
            validator._validate_mime_type_consistency(
                'application/pdf',  # Declared as PDF
                'image/jpeg',       # Actually JPEG
                'test.jpg'
            )
    
    def test_dangerous_patterns_detection(self, validator, malicious_content):
        """Test detection of dangerous content patterns."""
        with pytest.raises(SecurityValidationError, match="Dangerous content pattern detected"):
            validator._check_dangerous_patterns(malicious_content, 'malware.exe')
    
    def test_script_content_detection(self, validator):
        """Test detection of script content."""
        script_content = b'<script>alert("xss")</script>'
        with pytest.raises(SecurityValidationError, match="Script content detected"):
            validator._check_dangerous_patterns(script_content, 'malicious.html')
    
    def test_file_size_validation(self, validator):
        """Test file size validation."""
        # Test oversized file
        with pytest.raises(SecurityValidationError, match="File too large"):
            validator._validate_file_size(100 * 1024 * 1024, 'image/jpeg')  # 100MB
        
        # Test empty file
        with pytest.raises(SecurityValidationError, match="File is empty"):
            validator._validate_file_size(0, 'image/jpeg')
    
    @pytest.mark.asyncio
    async def test_valid_jpeg_validation(self, validator):
        """Test validation of valid JPEG content."""
        # Create a more complete JPEG content for PIL validation
        jpeg_content = (
            b'\xFF\xD8\xFF\xE0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00'
            b'\xFF\xDB\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t'
            b'\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a'
            b'\x1f\x1e\x1d\x1a\x1c\x1c $.\' ",#\x1c\x1c(7),01444\x1f\'9=82<.342'
            b'\xFF\xC0\x00\x11\x08\x00\x01\x00\x01\x01\x01\x11\x00\x02\x11\x01'
            b'\x03\x11\x01\xFF\xC4\x00\x14\x00\x01\x00\x00\x00\x00\x00\x00\x00'
            b'\x00\x00\x00\x00\x00\x00\x00\x00\x08\xFF\xC4\x00\x14\x10\x01\x00'
            b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xFF'
            b'\xDA\x00\x0c\x03\x01\x00\x02\x11\x03\x11\x00\x3f\x00\xaa\xFF\xD9'
        )
        
        with patch('app.utils.security_validation.scan_file_for_malware') as mock_scan:
            mock_scan.return_value = {'scanned': True, 'clean': True, 'scanner': 'test'}
            
            result = await validator.validate_file_content(
                jpeg_content, 
                'test.jpg', 
                'image/jpeg'
            )
            
            assert result['validation_passed'] is True
            assert result['actual_mime_type'] == 'image/jpeg'
            assert result['file_size'] == len(jpeg_content)
            assert 'file_hash' in result
    
    @pytest.mark.asyncio
    async def test_malware_detection_raises_error(self, validator, jpeg_content):
        """Test that malware detection raises SecurityValidationError."""
        with patch('app.utils.security_validation.scan_file_for_malware') as mock_scan:
            from app.utils.malware_scanner import MalwareDetected
            mock_scan.side_effect = MalwareDetected("Test malware detected")
            
            with pytest.raises(SecurityValidationError, match="Malware detected"):
                await validator.validate_file_content(
                    jpeg_content, 
                    'malware.jpg', 
                    'image/jpeg'
                )


class TestMalwareScanner:
    """Test suite for malware scanner."""
    
    @pytest.fixture
    def scanner(self):
        """Create a scanner instance."""
        return MalwareScanner()
    
    @pytest.fixture
    def clean_content(self):
        """Clean file content."""
        return b'This is clean content without any malware signatures.'
    
    @pytest.fixture
    def malicious_content(self):
        """Malicious content with PE header."""
        return b'MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff\x00\x00'
    
    @pytest.mark.asyncio
    async def test_signature_scan_clean_content(self, scanner, clean_content):
        """Test signature scanning of clean content."""
        result = await scanner._signature_based_scan(clean_content, 'clean.txt')
        assert result['clean'] is True
        assert result['scanner'] == 'signature'
        assert len(result['threats']) == 0
    
    @pytest.mark.asyncio
    async def test_signature_scan_malicious_content(self, scanner, malicious_content):
        """Test signature scanning of malicious content."""
        result = await scanner._signature_based_scan(malicious_content, 'malware.exe')
        assert result['clean'] is False
        assert result['scanner'] == 'signature'
        assert 'PE_Executable_Header' in result['threats']
    
    @pytest.mark.asyncio
    async def test_script_detection(self, scanner):
        """Test detection of script content."""
        script_content = b'<script>alert("xss")</script>'
        result = await scanner._signature_based_scan(script_content, 'script.html')
        assert result['clean'] is False
        assert 'JavaScript_Code' in result['threats']
    
    @pytest.mark.asyncio
    async def test_disabled_scanner(self):
        """Test scanner when disabled."""
        with patch.object(MalwareScanner, '__init__', lambda x: setattr(x, 'enabled', False)):
            scanner = MalwareScanner()
            scanner.enabled = False
            
            result = await scanner.scan_file_content(b'any content', 'test.txt')
            assert result['scanned'] is False
            assert result['clean'] is True
            assert result['scanner'] == 'disabled'
    
    def test_entropy_calculation(self, scanner):
        """Test entropy calculation."""
        # Low entropy (repeated data)
        low_entropy_data = b'A' * 100
        low_entropy = scanner._calculate_entropy(low_entropy_data)
        assert low_entropy < 1.0
        
        # High entropy (random-like data)
        high_entropy_data = bytes(range(256))
        high_entropy = scanner._calculate_entropy(high_entropy_data)
        assert high_entropy > 5.0


class TestUploadSecurity:
    """Test the upload security validation function."""
    
    def create_upload_file(self, content: bytes, filename: str, content_type: str):
        """Helper to create UploadFile mock."""
        file_obj = io.BytesIO(content)
        return UploadFile(
            filename=filename,
            file=file_obj,
            content_type=content_type
        )
    
    @pytest.mark.asyncio
    async def test_valid_upload_validation(self):
        """Test validation of a valid upload."""
        jpeg_content = b'\xFF\xD8\xFF\xE0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00\xFF\xDB\x00C'
        upload_file = self.create_upload_file(jpeg_content, 'test.jpg', 'image/jpeg')
        
        with patch('app.utils.security_validation.scan_file_for_malware') as mock_scan:
            mock_scan.return_value = {'scanned': True, 'clean': True, 'scanner': 'test'}
            
            result = await validate_upload_security(upload_file)
            assert result['validation_passed'] is True
            assert result['filename'] == 'test.jpg'
    
    @pytest.mark.asyncio
    async def test_empty_file_validation(self):
        """Test validation of empty file."""
        upload_file = self.create_upload_file(b'', 'empty.jpg', 'image/jpeg')
        
        with pytest.raises(SecurityValidationError, match="File is empty"):
            await validate_upload_security(upload_file)
    
    @pytest.mark.asyncio
    async def test_malicious_upload_validation(self):
        """Test validation of malicious upload."""
        malicious_content = b'MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff\x00\x00'
        upload_file = self.create_upload_file(malicious_content, 'malware.jpg', 'image/jpeg')
        
        with pytest.raises(SecurityValidationError, match="Dangerous content pattern detected"):
            await validate_upload_security(upload_file)


if __name__ == '__main__':
    pytest.main([__file__])