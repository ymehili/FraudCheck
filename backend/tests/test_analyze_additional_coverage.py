import pytest
import pytest_asyncio
from unittest.mock import patch, Mock, AsyncMock, MagicMock
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
import uuid
import tempfile
import os
import aiohttp
from datetime import datetime, timezone
from PIL import Image

from app.models.file import FileRecord
from app.models.analysis import AnalysisResult
from app.models.user import User
from app.schemas.analysis import AnalysisRequest, AnalysisResponse
from app.api.v1.analyze import (
    _download_file_for_analysis,
    _validate_and_preprocess_image,
    _run_comprehensive_analysis,
    _store_analysis_results,
    _format_analysis_response,
    _get_user_file,
    _get_existing_analysis,
    ComprehensiveAnalysisResult
)


@pytest.fixture
def sample_user():
    """Create a sample user for testing."""
    return User(id="user-123", email="test@example.com")


@pytest.fixture
def sample_file_record():
    """Create a sample file record for testing."""
    return FileRecord(
        id="file-123",
        user_id="user-123",
        filename="test.jpg",
        s3_key="test/file-123.jpg",
        s3_url="https://s3.amazonaws.com/test/file-123.jpg",
        file_size=1024,
        mime_type="image/jpeg"
    )


@pytest.fixture
def sample_analysis_result():
    """Create a sample analysis result."""
    return AnalysisResult(
        id="analysis-123",
        file_id="file-123",
        analysis_timestamp=datetime.now(timezone.utc),
        forensics_score=0.85,
        edge_inconsistencies={"score": 0.9, "anomalies": ["edge_issue"]},
        compression_artifacts={"score": 0.7, "blocks": 15},
        font_analysis={"score": 0.95, "consistency": 0.88},
        ocr_confidence=0.92,
        extracted_fields={
            "payee": "Test Payee",
            "amount": "$250.00",
            "date": "2024-01-20",
            "account_number": "123456789",
            "routing_number": "987654321",
            "check_number": "001",
            "memo": "Test memo",
            "signature_detected": True,
            "field_confidences": {"payee": 0.95, "amount": 0.98, "date": 0.85}
        },
        overall_risk_score=0.35,
        rule_violations={
            "violations": ["minor_issue"],
            "passed_rules": ["rule1", "rule2"],
            "rule_scores": {"rule1": 0.1, "rule2": 0.0}
        },
        confidence_factors={"overall": 0.85, "forensics": 0.82, "ocr": 0.92}
    )


@pytest.mark.asyncio
async def test_get_user_file_success(db_session, sample_user, sample_file_record):
    """Test successful user file retrieval."""
    db_session.add(sample_file_record)
    await db_session.commit()
    
    result = await _get_user_file(sample_file_record.id, sample_user.id, db_session)
    
    assert result is not None
    assert result.id == sample_file_record.id
    assert result.user_id == sample_user.id


@pytest.mark.asyncio
async def test_get_user_file_not_found(db_session, sample_user):
    """Test user file retrieval with non-existent file."""
    with pytest.raises(HTTPException) as exc_info:
        await _get_user_file("non-existent-file", sample_user.id, db_session)
    
    assert exc_info.value.status_code == 404
    assert "File not found or access denied" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_get_user_file_wrong_user(db_session, sample_file_record):
    """Test user file retrieval with wrong user ID."""
    db_session.add(sample_file_record)
    await db_session.commit()
    
    with pytest.raises(HTTPException) as exc_info:
        await _get_user_file(sample_file_record.id, "wrong-user-id", db_session)
    
    assert exc_info.value.status_code == 404
    assert "File not found or access denied" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_get_existing_analysis_success(db_session, sample_analysis_result):
    """Test successful existing analysis retrieval."""
    db_session.add(sample_analysis_result)
    await db_session.commit()
    
    result = await _get_existing_analysis(sample_analysis_result.file_id, db_session)
    
    assert result is not None
    assert result.id == sample_analysis_result.id
    assert result.file_id == sample_analysis_result.file_id


@pytest.mark.asyncio
async def test_get_existing_analysis_not_found(db_session):
    """Test existing analysis retrieval with no analysis."""
    result = await _get_existing_analysis("non-existent-file", db_session)
    
    assert result is None


@pytest.mark.asyncio
async def test_download_file_for_analysis_s3_failure():
    """Test download file with S3 service failure."""
    with patch('app.core.s3.s3_service.generate_presigned_url', return_value=None):
        with pytest.raises(HTTPException) as exc_info:
            await _download_file_for_analysis("test/key.jpg")
        
        assert exc_info.value.status_code == 500
        assert "Failed to generate download URL" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_download_file_for_analysis_http_error():
    """Test download file with HTTP error."""
    with patch('app.core.s3.s3_service.generate_presigned_url', return_value="https://example.com/file.jpg"):
        with patch('aiohttp.ClientSession') as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 404
            mock_response.__aenter__.return_value = mock_response
            mock_response.__aexit__.return_value = None
            
            mock_session.return_value.__aenter__.return_value.get.return_value = mock_response
            
            with pytest.raises(HTTPException) as exc_info:
                await _download_file_for_analysis("test/key.jpg")
            
            assert exc_info.value.status_code == 500
            assert "Failed to download file from S3" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_validate_and_preprocess_image_validation_failure():
    """Test image validation with validation failure."""
    with patch('app.utils.image_utils.validate_image_file', return_value={'valid': False}):
        with pytest.raises(HTTPException) as exc_info:
            await _validate_and_preprocess_image("/tmp/invalid.jpg")
        
        assert exc_info.value.status_code == 400
        assert "Invalid image file" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_validate_and_preprocess_image_normalization_failure():
    """Test image validation with normalization failure."""
    with patch('app.utils.image_utils.validate_image_file', return_value={'valid': True}):
        with patch('app.utils.image_utils.normalize_image_format', side_effect=Exception("Normalization failed")):
            with pytest.raises(HTTPException) as exc_info:
                await _validate_and_preprocess_image("/tmp/test.jpg")
            
            assert exc_info.value.status_code == 400
            assert "Image preprocessing failed" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_run_comprehensive_analysis_no_tasks():
    """Test comprehensive analysis with no analysis types."""
    result = await _run_comprehensive_analysis("/tmp/test.jpg", [])
    
    assert result.forensics_result is None
    assert result.ocr_result is None
    assert result.rule_result is None


@pytest.mark.asyncio
async def test_run_comprehensive_analysis_ocr_only():
    """Test comprehensive analysis with only OCR."""
    from app.schemas.analysis import OCRResult
    
    mock_ocr_result = OCRResult(
        payee="Test Payee",
        amount="$100.00",
        date="2024-01-15",
        signature_detected=True,
        extraction_confidence=0.9,
        field_confidences={"payee": 0.95}
    )
    
    with patch('app.api.v1.analyze.get_ocr_engine') as mock_get_ocr:
        mock_ocr_engine = AsyncMock()
        mock_ocr_engine.extract_fields.return_value = mock_ocr_result
        mock_get_ocr.return_value = mock_ocr_engine
        
        result = await _run_comprehensive_analysis("/tmp/test.jpg", ["ocr"])
        
        assert result.forensics_result is None
        assert result.ocr_result == mock_ocr_result
        assert result.rule_result is None


@pytest.mark.asyncio
async def test_run_comprehensive_analysis_task_failure():
    """Test comprehensive analysis with task failure."""
    with patch('app.api.v1.analyze.forensics_engine.analyze_image', side_effect=Exception("Forensics failed")):
        with pytest.raises(HTTPException) as exc_info:
            await _run_comprehensive_analysis("/tmp/test.jpg", ["forensics"])
        
        assert exc_info.value.status_code == 500
        assert "Analysis failed" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_store_analysis_results_database_failure(db_session):
    """Test storing analysis results with database failure."""
    from app.schemas.analysis import ForensicsResult, OCRResult, RuleEngineResult
    
    forensics_result = ForensicsResult(
        edge_score=0.8,
        compression_score=0.7,
        font_score=0.9,
        overall_score=0.8,
        detected_anomalies=[],
        edge_inconsistencies={},
        compression_artifacts={},
        font_analysis={}
    )
    
    ocr_result = OCRResult(
        payee="Test",
        amount="$100.00",
        date="2024-01-15",
        signature_detected=True,
        extraction_confidence=0.9,
        field_confidences={}
    )
    
    rule_result = RuleEngineResult(
        risk_score=0.3,
        violations=[],
        passed_rules=["rule1"],
        rule_scores={"rule1": 0.0},
        confidence_factors={"overall": 0.8},
        recommendations=[]
    )
    
    analysis_result = ComprehensiveAnalysisResult(
        forensics_result=forensics_result,
        ocr_result=ocr_result,
        rule_result=rule_result
    )
    
    # Mock commit to fail
    with patch.object(db_session, 'commit', side_effect=Exception("Database error")):
        with pytest.raises(HTTPException) as exc_info:
            await _store_analysis_results("test-file-id", analysis_result, db_session)
        
        assert exc_info.value.status_code == 500
        assert "Failed to store analysis results" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_store_analysis_results_with_none_values(db_session):
    """Test storing analysis results with None values."""
    analysis_result = ComprehensiveAnalysisResult(
        forensics_result=None,
        ocr_result=None,
        rule_result=None
    )
    
    stored_result = await _store_analysis_results("test-file-id", analysis_result, db_session)
    
    assert stored_result is not None
    assert stored_result.file_id == "test-file-id"
    assert stored_result.forensics_score == 0.0
    assert stored_result.ocr_confidence == 0.0
    assert stored_result.overall_risk_score == 0.0
    assert stored_result.extracted_fields["payee"] is None
    assert stored_result.extracted_fields["amount"] is None
    assert stored_result.extracted_fields["signature_detected"] is False


@pytest.mark.asyncio
async def test_format_analysis_response_with_none_values():
    """Test formatting analysis response with None values."""
    analysis_record = AnalysisResult(
        id="test-id",
        file_id="test-file-id",
        analysis_timestamp=datetime.now(timezone.utc),
        forensics_score=None,
        edge_inconsistencies=None,
        compression_artifacts=None,
        font_analysis=None,
        ocr_confidence=None,
        extracted_fields=None,
        overall_risk_score=None,
        rule_violations=None,
        confidence_factors=None
    )
    
    response = await _format_analysis_response(analysis_record)
    
    assert response.analysis_id == "test-id"
    assert response.file_id == "test-file-id"
    assert response.forensics.overall_score == 0.0
    assert response.ocr.extraction_confidence == 0.0
    assert response.rules.risk_score == 0.0
    assert response.overall_risk_score is None
    assert response.confidence == 0.0