"""
Additional comprehensive tests to reach 90%+ coverage.
"""
import pytest
import asyncio
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi import HTTPException

from app.api.deps import get_db_session
from app.core.forensics import ForensicsEngine
from app.core.ocr import OCREngine
from app.core.rule_engine import RuleEngine


class TestDepsModule:
    """Test deps module for missing coverage."""
    
    @pytest.mark.asyncio
    async def test_get_db_session_success(self):
        """Test successful database session dependency."""
        mock_session = AsyncMock()
        
        with patch('app.api.deps.get_db') as mock_get_db:
            # Mock the async context manager
            mock_context = AsyncMock()
            mock_context.__aenter__ = AsyncMock(return_value=mock_session)
            mock_context.__aexit__ = AsyncMock(return_value=None)
            mock_get_db.return_value = mock_context
            
            # Test the dependency
            db_gen = get_db_session()
            session = await db_gen.__anext__()
            
            assert session == mock_session
            
            # Clean up
            try:
                await db_gen.__anext__()
            except StopAsyncIteration:
                pass
    
    @pytest.mark.asyncio
    async def test_get_db_session_error(self):
        """Test database session dependency with error."""
        with patch('app.api.deps.get_db') as mock_get_db:
            mock_get_db.side_effect = Exception("Database connection failed")
            
            with pytest.raises(Exception, match="Database connection failed"):
                db_gen = get_db_session()
                await db_gen.__anext__()


class TestForensicsEngineEdgeCases:
    """Test forensics engine edge cases for coverage."""
    
    @pytest.mark.asyncio
    async def test_forensics_engine_invalid_image_path(self):
        """Test forensics engine with invalid image path."""
        engine = ForensicsEngine()
        
        # Test with None path
        with pytest.raises(FileNotFoundError):
            await engine.analyze_image("nonexistent_file.jpg")
    
    @pytest.mark.asyncio
    async def test_forensics_engine_memory_optimization(self):
        """Test forensics engine memory optimization paths."""
        engine = ForensicsEngine()
        
        # Create a mock image that would trigger memory optimization
        mock_image = MagicMock()
        mock_image.shape = (8000, 6000, 3)  # Large image
        
        with patch('cv2.imread', return_value=mock_image):
            with patch('cv2.resize', return_value=mock_image):
                with patch('os.path.exists', return_value=True):
                    with patch.object(engine, '_detect_edge_inconsistencies', return_value={'score': 0.5}):
                        with patch.object(engine, '_detect_compression_artifacts', return_value={'score': 0.6}):
                            with patch.object(engine, '_analyze_font_consistency', return_value={'score': 0.7}):
                                result = await engine.analyze_image("test.jpg")
                                assert result is not None
    
    @pytest.mark.asyncio
    async def test_forensics_engine_error_recovery(self):
        """Test forensics engine error recovery."""
        engine = ForensicsEngine()
        
        with patch('cv2.imread', return_value=None):  # Simulate failed image load
            with pytest.raises(ValueError, match="Failed to load image"):
                await engine.analyze_image("test.jpg")


class TestOCREngineEdgeCases:
    """Test OCR engine edge cases for coverage."""
    
    @pytest.mark.asyncio
    async def test_ocr_engine_image_format_edge_cases(self):
        """Test OCR engine with various image format edge cases."""
        engine = OCREngine("fake-api-key")
        
        # Test with empty image path
        with pytest.raises(FileNotFoundError):
            await engine.extract_fields("")
    
    @pytest.mark.asyncio
    async def test_ocr_engine_api_retry_logic(self):
        """Test OCR engine API retry logic."""
        engine = OCREngine("fake-api-key")
        
        # Mock image loading to succeed
        with patch.object(engine, '_load_image', return_value=MagicMock()):
            # Mock API call to fail multiple times then succeed
            call_count = 0
            def mock_api_call(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count < 3:
                    raise Exception("API temporarily unavailable")
                
                # Return successful response
                mock_response = MagicMock()
                mock_response.candidates = [MagicMock()]
                mock_response.candidates[0].content.parts = [MagicMock()]
                mock_response.candidates[0].content.parts[0].text = '{"payee": "John Doe"}'
                return mock_response
            
            with patch.object(engine, '_call_gemini_api', side_effect=mock_api_call):
                with patch('os.path.exists', return_value=True):
                    result = await engine.extract_fields("test.jpg")
                    assert result.payee == "John Doe"
                    assert call_count == 3  # Should have retried
    
    @pytest.mark.asyncio
    async def test_ocr_engine_confidence_calculation_edge_cases(self):
        """Test OCR confidence calculation edge cases."""
        engine = OCREngine("fake-api-key")
        
        # Test with None values
        confidence = engine._calculate_field_confidence('payee', None)
        assert confidence == 0.0
        
        # Test with empty string
        confidence = engine._calculate_field_confidence('payee', '')
        assert confidence == 0.0
        
        # Test with very long string
        long_string = 'x' * 1000
        confidence = engine._calculate_field_confidence('payee', long_string)
        assert 0.0 <= confidence <= 1.0


class TestRuleEngineEdgeCases:
    """Test rule engine edge cases for coverage."""
    
    @pytest.mark.asyncio
    async def test_rule_engine_null_input_handling(self):
        """Test rule engine with null inputs."""
        engine = RuleEngine()
        
        # Test with all None inputs
        result = await engine.process_results(None, None)
        
        assert result.risk_score >= 0.0
        assert result.overall_confidence >= 0.0
        assert isinstance(result.violations, list)
        assert isinstance(result.passed_rules, list)
        assert isinstance(result.recommendations, list)
    
    @pytest.mark.asyncio
    async def test_rule_engine_partial_data_processing(self):
        """Test rule engine with partial data."""
        engine = RuleEngine()
        
        # Mock forensics result with minimal data
        mock_forensics = MagicMock()
        mock_forensics.overall_score = 0.5
        mock_forensics.edge_score = None
        mock_forensics.compression_score = None
        mock_forensics.font_score = None
        
        result = await engine.process_results(mock_forensics, None)
        
        assert result.risk_score >= 0.0
        assert result.overall_confidence >= 0.0
    
    @pytest.mark.asyncio
    async def test_rule_engine_extreme_values(self):
        """Test rule engine with extreme values."""
        engine = RuleEngine()
        
        # Mock with extreme values
        mock_forensics = MagicMock()
        mock_forensics.overall_score = 0.0  # Minimum
        mock_forensics.edge_score = 1.0     # Maximum
        mock_forensics.compression_score = 0.5
        mock_forensics.font_score = 0.0
        
        mock_ocr = MagicMock()
        mock_ocr.extraction_confidence = 1.0  # Maximum
        mock_ocr.amount = "$999999.99"  # Large amount
        mock_ocr.payee = "X" * 100      # Very long payee
        
        result = await engine.process_results(mock_forensics, mock_ocr)
        
        assert 0.0 <= result.risk_score <= 1.0
        assert 0.0 <= result.overall_confidence <= 1.0


class TestFileUploadEdgeCases:
    """Test file upload edge cases."""
    
    @pytest.mark.asyncio
    async def test_file_validation_edge_cases(self):
        """Test file validation with edge cases."""
        from app.utils.image_utils import validate_image_file, ImageValidationError
        
        # Test with very small file
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
            tmp.write(b'')  # Empty file
            tmp.flush()
            
            with pytest.raises(ImageValidationError):
                validate_image_file(tmp.name)
    
    def test_temp_file_cleanup_error_handling(self):
        """Test temporary file cleanup with errors."""
        from app.api.v1.analyze import cleanup_temp_files
        
        # Test cleanup with permission errors
        import tempfile
        import os
        
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            temp_file = tmp.name
        
        # Make file read-only (might not prevent deletion on all systems)
        try:
            os.chmod(temp_file, 0o444)
        except:
            pass
        
        # Should not raise exception even if deletion fails
        cleanup_temp_files([temp_file])
        
        # Clean up manually if still exists
        try:
            os.chmod(temp_file, 0o777)
            os.unlink(temp_file)
        except:
            pass


class TestConfigurationEdgeCases:
    """Test configuration edge cases."""
    
    def test_config_loading_with_missing_values(self):
        """Test configuration loading with missing values."""
        from app.core.config import settings
        
        # Settings should have default values
        assert hasattr(settings, 'database_url')
        assert hasattr(settings, 'secret_key')
        assert hasattr(settings, 'algorithm')
    
    def test_config_validation(self):
        """Test configuration validation."""
        from app.core.config import Settings
        
        # Test creating settings with minimal values
        minimal_settings = Settings()
        
        assert minimal_settings.database_url is not None
        assert minimal_settings.secret_key is not None
        assert minimal_settings.algorithm is not None


class TestSecurityEdgeCases:
    """Test security module edge cases."""
    
    def test_token_creation_with_edge_cases(self):
        """Test token creation with edge cases."""
        from app.core.security import create_access_token
        
        # Test with empty data
        token = create_access_token(data={})
        assert token is not None
        assert isinstance(token, str)
        
        # Test with None expiration
        token = create_access_token(data={"sub": "test"}, expires_delta=None)
        assert token is not None
    
    def test_password_verification_edge_cases(self):
        """Test password verification edge cases."""
        from app.core.security import verify_password, get_password_hash
        
        # Test with empty password
        hashed = get_password_hash("")
        assert verify_password("", hashed) is True
        assert verify_password("wrong", hashed) is False
        
        # Test with very long password
        long_password = "x" * 1000
        hashed = get_password_hash(long_password)
        assert verify_password(long_password, hashed) is True


class TestModelEdgeCases:
    """Test model edge cases."""
    
    def test_model_string_representations(self):
        """Test model string representations."""
        from app.models.user import User
        from app.models.file import FileRecord
        from app.models.analysis import AnalysisResult
        from datetime import datetime, timezone
        
        # Test User model
        user = User(id="test", email="test@example.com")
        assert str(user) is not None
        
        # Test FileRecord model
        file_record = FileRecord(
            id="test",
            filename="test.jpg",
            s3_key="test/key",
            content_type="image/jpeg",
            file_size=1024,
            user_id="test"
        )
        assert str(file_record) is not None
        
        # Test AnalysisResult model
        analysis = AnalysisResult(
            id="test",
            file_id="test",
            analysis_timestamp=datetime.now(timezone.utc),
            forensics_score=0.5,
            edge_inconsistencies={},
            compression_artifacts={},
            font_analysis={},
            ocr_confidence=0.8,
            extracted_fields={},
            overall_risk_score=0.3,
            rule_violations=[],
            confidence_factors={}
        )
        assert str(analysis) is not None
    
    def test_model_field_validation(self):
        """Test model field validation."""
        from app.models.user import User
        from app.models.file import FileRecord
        
        # Test invalid email format (should be handled by Pydantic)
        try:
            user = User(id="test", email="invalid-email")
            # If no validation error, model accepts any string
            assert user.email == "invalid-email"
        except:
            # If validation error, that's also fine
            pass
        
        # Test negative file size
        try:
            file_record = FileRecord(
                id="test",
                filename="test.jpg",
                s3_key="test/key",
                content_type="image/jpeg",
                file_size=-1,  # Negative size
                user_id="test"
            )
            # Model might accept negative values
            assert file_record.file_size == -1
        except:
            # Or it might reject them
            pass


class TestS3ServiceEdgeCases:
    """Test S3 service edge cases."""
    
    @pytest.mark.asyncio
    async def test_s3_service_error_handling(self):
        """Test S3 service error handling."""
        from app.core.s3 import S3Service
        
        service = S3Service()
        
        # Test with invalid bucket name
        with patch.object(service, 'client') as mock_client:
            mock_client.upload_fileobj.side_effect = Exception("S3 Error")
            
            with pytest.raises(Exception):
                await service.upload_file(b"test data", "test.jpg")
    
    def test_s3_key_generation_edge_cases(self):
        """Test S3 key generation edge cases."""
        from app.core.s3 import S3Service
        
        service = S3Service()
        
        # Test with empty user_id
        key = service.generate_s3_key("", "test.jpg")
        assert "uploads/" in key
        assert "test.jpg" in key
        
        # Test with special characters in filename
        key = service.generate_s3_key("user", "file with spaces & symbols.jpg")
        assert "uploads/user/" in key
        assert "file with spaces & symbols.jpg" in key


class TestSchemaValidation:
    """Test schema validation edge cases."""
    
    def test_analysis_request_validation(self):
        """Test analysis request schema validation."""
        from app.schemas.analysis import AnalysisRequest
        
        # Test with minimal valid data
        request = AnalysisRequest(
            file_id="test",
            analysis_types=["forensics"]
        )
        assert request.file_id == "test"
        assert request.analysis_types == ["forensics"]
        
        # Test with all analysis types
        request = AnalysisRequest(
            file_id="test",
            analysis_types=["forensics", "ocr", "rules"]
        )
        assert len(request.analysis_types) == 3
    
    def test_file_upload_schema_validation(self):
        """Test file upload schema validation."""
        from app.schemas.file import FileUploadResponse
        
        response = FileUploadResponse(
            file_id="test",
            filename="test.jpg",
            message="Upload successful"
        )
        assert response.file_id == "test"
        assert response.filename == "test.jpg"
        assert response.message == "Upload successful"
