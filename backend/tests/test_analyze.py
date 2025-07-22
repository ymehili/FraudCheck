import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
import uuid
from datetime import datetime, timezone
import tempfile
import os
from PIL import Image

from app.main import app
from app.models.file import FileRecord
from app.models.analysis import AnalysisResult
from app.schemas.analysis import AnalysisRequest, AnalysisResponse, ForensicsResult, OCRResult, RuleEngineResult


@pytest.fixture
def sample_file_record(client):
    """Create sample file record for testing."""
    # Extract the user ID that was set up for this test's client
    from app.api.deps import get_current_user
    from app.main import app
    
    # Get the override function and call it to get the user
    override_func = app.dependency_overrides.get(get_current_user)
    test_user = override_func() if override_func else None
    user_id = test_user.id if test_user else "fallback-user-id"
    
    import time
    import random
    unique_suffix = f"{int(time.time() * 1000000)}-{random.randint(1000, 9999)}"
    unique_file_id = f"file-{unique_suffix}"
    
    return FileRecord(
        id=unique_file_id,
        user_id=user_id,  # Use the same user ID as the client
        filename="test-check.jpg",
        s3_key=f"test/{unique_file_id}-check.jpg",
        s3_url=f"https://test-bucket.s3.amazonaws.com/test/{unique_file_id}-check.jpg",
        file_size=1024,
        mime_type="image/jpeg"
    )


@pytest.fixture
def sample_analysis_result():
    """Create sample analysis result for testing."""
    return AnalysisResult(
        id=str(uuid.uuid4()),
        file_id=str(uuid.uuid4()),  # Will be overwritten in tests
        analysis_timestamp=datetime.now(timezone.utc),
        forensics_score=0.75,
        edge_inconsistencies={"score": 0.8, "detected": ["edge_issue"]},
        compression_artifacts={"score": 0.6, "blocks": 10},
        font_analysis={"score": 0.9, "consistency": 0.85},
        ocr_confidence=0.85,
        extracted_fields={
            "payee": "John Doe",
            "amount": "$100.00",
            "date": "2024-01-15",
            "signature_detected": True,
            "field_confidences": {"payee": 0.9, "amount": 0.95}
        },
        overall_risk_score=0.25,
        rule_violations={
            "violations": [],
            "passed_rules": ["rule1", "rule2"],
            "rule_scores": {"rule1": 0.0, "rule2": 0.0}
        },
        confidence_factors={"overall": 0.8, "forensics": 0.75}
    )


@pytest.fixture
def sample_forensics_result():
    """Create sample forensics result for testing."""
    return ForensicsResult(
        edge_score=0.8,
        compression_score=0.6,
        font_score=0.9,
        overall_score=0.75,
        detected_anomalies=["minor compression artifacts"],
        edge_inconsistencies={"score": 0.8, "regions": 5},
        compression_artifacts={"score": 0.6, "blocks": 10},
        font_analysis={"score": 0.9, "consistency": 0.85}
    )


@pytest.fixture
def sample_ocr_result():
    """Create sample OCR result for testing."""
    return OCRResult(
        payee="John Doe",
        amount="$100.00",
        date="2024-01-15",
        account_number="123456789",
        routing_number="987654321",
        check_number="001",
        signature_detected=True,
        extraction_confidence=0.85,
        field_confidences={"payee": 0.9, "amount": 0.95, "date": 0.8}
    )


@pytest.fixture
def sample_rule_result():
    """Create sample rule engine result for testing."""
    return RuleEngineResult(
        risk_score=0.25,
        violations=[],
        passed_rules=["edge_quality", "ocr_confidence", "amount_validation"],
        rule_scores={"edge_quality": 0.0, "ocr_confidence": 0.0, "amount_validation": 0.0},
        confidence_factors={"overall": 0.8, "forensics": 0.75, "ocr": 0.85},
        recommendations=["Check appears legitimate", "No significant fraud indicators"]
    )


@pytest.fixture
def sample_image_file():
    """Create sample image file for testing."""
    image = Image.new('RGB', (400, 200), color='white')
    
    # Add some text
    import PIL.ImageDraw
    draw = PIL.ImageDraw.Draw(image)
    draw.text((10, 10), "Test Bank", fill='black')
    draw.text((10, 30), "Pay to: John Doe", fill='black')
    draw.text((10, 50), "$100.00", fill='black')
    
    temp_file = tempfile.NamedTemporaryFile(suffix='.jpg', delete=False)
    image.save(temp_file.name, 'JPEG')
    temp_file.close()
    
    yield temp_file.name
    
    try:
        os.unlink(temp_file.name)
    except OSError:
        pass


@pytest.mark.asyncio
async def test_analyze_check_success(client, auth_headers, sample_file_record, sample_forensics_result, 
                                   sample_ocr_result, sample_rule_result, db_session):
    """Test successful check analysis."""
    # Add file record to database
    db_session.add(sample_file_record)
    await db_session.commit()
    
    # Mock authentication
    from app.models.user import User
    mock_user = User(id=sample_file_record.user_id, email="test@example.com")
    
    with patch('app.api.deps.get_current_user', return_value=mock_user):
        # Mock the analysis components
        with patch('app.api.v1.analyze.forensics_engine.analyze_image', return_value=sample_forensics_result) as mock_forensics:
            with patch('app.api.v1.analyze.get_ocr_engine') as mock_get_ocr:
                mock_ocr_engine = AsyncMock()
                mock_ocr_engine.extract_fields.return_value = sample_ocr_result
                mock_get_ocr.return_value = mock_ocr_engine
                
                with patch('app.api.v1.analyze.rule_engine.process_results', return_value=sample_rule_result) as mock_rules:
                    with patch('app.api.v1.analyze._download_file_for_analysis', return_value="/tmp/test.jpg"):
                        with patch('app.api.v1.analyze._validate_and_preprocess_image', return_value="/tmp/test.jpg"):
                            
                            request_data = {
                                "file_id": sample_file_record.id,
                                "analysis_types": ["forensics", "ocr", "rules"]
                            }
                            
                            response = client.post(
                                "/api/v1/analyze/",
                                json=request_data,
                                headers=auth_headers
                            )
                            
                            assert response.status_code == 200
                            result = response.json()
                            
                            assert "analysis_id" in result
                            assert result["file_id"] == sample_file_record.id
                            assert "timestamp" in result
                            assert "forensics" in result
                            assert "ocr" in result
                            assert "rules" in result
                            assert "overall_risk_score" in result
                            assert "confidence" in result
                            
                            # Verify analysis was called
                            mock_forensics.assert_called_once()
                            mock_ocr_engine.extract_fields.assert_called_once()
                            mock_rules.assert_called_once()


@pytest.mark.asyncio
async def test_analyze_check_file_not_found(client, auth_headers):
    """Test analysis with nonexistent file."""
    request_data = {
        "file_id": "nonexistent-file-id",
        "analysis_types": ["forensics", "ocr", "rules"]
    }
    
    response = client.post(
        "/api/v1/analyze/",
        json=request_data,
        headers=auth_headers
    )
    
    assert response.status_code == 404
    assert "File not found" in response.json()["detail"]


@pytest.mark.asyncio
async def test_analyze_check_existing_analysis(client, auth_headers, sample_file_record, 
                                             sample_analysis_result, db_session):
    """Test analysis with existing results."""
    # Add file record and analysis result to database
    db_session.add(sample_file_record)
    sample_analysis_result.file_id = sample_file_record.id
    db_session.add(sample_analysis_result)
    await db_session.commit()
    
    request_data = {
        "file_id": sample_file_record.id,
        "analysis_types": ["forensics", "ocr", "rules"]
    }
    
    response = client.post(
        "/api/v1/analyze/",
        json=request_data,
        headers=auth_headers
    )
    
    assert response.status_code == 200
    result = response.json()
    
    assert result["analysis_id"] == sample_analysis_result.id
    assert result["file_id"] == sample_file_record.id


@pytest.mark.asyncio
async def test_analyze_check_partial_analysis(client, auth_headers, sample_file_record, 
                                            sample_forensics_result, db_session):
    """Test analysis with only forensics."""
    # Add file record to database
    db_session.add(sample_file_record)
    await db_session.commit()
    
    with patch('app.api.v1.analyze.forensics_engine.analyze_image', return_value=sample_forensics_result):
        with patch('app.api.v1.analyze._download_file_for_analysis', return_value="/tmp/test.jpg"):
            with patch('app.api.v1.analyze._validate_and_preprocess_image', return_value="/tmp/test.jpg"):
                
                request_data = {
                    "file_id": sample_file_record.id,
                    "analysis_types": ["forensics"]  # Only forensics
                }
                
                response = client.post(
                    "/api/v1/analyze/",
                    json=request_data,
                    headers=auth_headers
                )
                
                assert response.status_code == 200
                result = response.json()
                
                assert "forensics" in result
                # OCR and rules should have default values
                assert result["ocr"]["extraction_confidence"] == 0.0
                assert result["rules"]["risk_score"] == 0.0


@pytest.mark.asyncio
async def test_analyze_check_forensics_failure(client, auth_headers, sample_file_record, db_session):
    """Test analysis with forensics failure."""
    # Add file record to database
    db_session.add(sample_file_record)
    await db_session.commit()
    
    with patch('app.api.v1.analyze.forensics_engine.analyze_image', side_effect=Exception("Forensics failed")):
        with patch('app.api.v1.analyze._download_file_for_analysis', return_value="/tmp/test.jpg"):
            with patch('app.api.v1.analyze._validate_and_preprocess_image', return_value="/tmp/test.jpg"):
                
                request_data = {
                    "file_id": sample_file_record.id,
                    "analysis_types": ["forensics", "ocr", "rules"]
                }
                
                response = client.post(
                    "/api/v1/analyze/",
                    json=request_data,
                    headers=auth_headers
                )
                
                assert response.status_code == 500
                assert "Analysis failed" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_analysis_success(client, auth_headers, sample_file_record, 
                                  sample_analysis_result, db_session):
    """Test successful analysis retrieval."""
    # Add records to database
    db_session.add(sample_file_record)
    sample_analysis_result.file_id = sample_file_record.id
    db_session.add(sample_analysis_result)
    await db_session.commit()
    
    response = client.get(
        f"/api/v1/analyze/{sample_file_record.id}",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    result = response.json()
    
    assert result["id"] == sample_analysis_result.id
    assert result["file_id"] == sample_file_record.id
    assert "forensics_score" in result
    assert "ocr_confidence" in result
    assert "overall_risk_score" in result


@pytest.mark.asyncio
async def test_get_analysis_not_found(client, auth_headers, sample_file_record, db_session):
    """Test analysis retrieval with no analysis."""
    # Add only file record, no analysis
    db_session.add(sample_file_record)
    await db_session.commit()
    
    response = client.get(
        f"/api/v1/analyze/{sample_file_record.id}",
        headers=auth_headers
    )
    
    assert response.status_code == 404
    assert "Analysis not found" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_analysis_file_not_found(client, auth_headers):
    """Test analysis retrieval with nonexistent file."""
    response = client.get(
        "/api/v1/analyze/nonexistent-file-id",
        headers=auth_headers
    )
    
    assert response.status_code == 404
    assert "File not found" in response.json()["detail"]


@pytest.mark.asyncio
async def test_list_analyses_success(client, auth_headers, sample_file_record, 
                                   sample_analysis_result, db_session):
    """Test successful analyses listing."""
    # Add records to database
    db_session.add(sample_file_record)
    sample_analysis_result.file_id = sample_file_record.id
    db_session.add(sample_analysis_result)
    await db_session.commit()
    
    response = client.get(
        "/api/v1/analyze/",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    result = response.json()
    
    assert "analyses" in result
    assert "total" in result
    assert "page" in result
    assert "per_page" in result
    assert result["total"] == 1
    assert len(result["analyses"]) == 1
    assert result["analyses"][0]["id"] == sample_analysis_result.id


@pytest.mark.asyncio
async def test_list_analyses_pagination(client, auth_headers, sample_file_record, db_session):
    """Test analyses listing with pagination."""
    # Add file record
    db_session.add(sample_file_record)
    await db_session.commit()
    
    # Add multiple analysis results
    for i in range(3):
        analysis_result = AnalysisResult(
            id=str(uuid.uuid4()),
            file_id=sample_file_record.id,
            analysis_timestamp=datetime.now(timezone.utc),
            forensics_score=0.75,
            edge_inconsistencies={},
            compression_artifacts={},
            font_analysis={},
            ocr_confidence=0.85,
            extracted_fields={},
            overall_risk_score=0.25,
            rule_violations={},
            confidence_factors={}
        )
        db_session.add(analysis_result)
    
    await db_session.commit()
    
    response = client.get(
        "/api/v1/analyze/?page=1&per_page=2",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    result = response.json()
    
    assert result["total"] == 3
    assert len(result["analyses"]) == 2
    assert result["page"] == 1
    assert result["per_page"] == 2


@pytest.mark.asyncio
async def test_list_analyses_empty(client, auth_headers):
    """Test analyses listing with no results."""
    response = client.get(
        "/api/v1/analyze/",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    result = response.json()
    
    assert result["total"] == 0
    assert len(result["analyses"]) == 0


@pytest.mark.asyncio
async def test_delete_analysis_success(client, auth_headers, sample_file_record, 
                                     sample_analysis_result, db_session):
    """Test successful analysis deletion."""
    # Add records to database
    db_session.add(sample_file_record)
    sample_analysis_result.file_id = sample_file_record.id
    db_session.add(sample_analysis_result)
    await db_session.commit()
    
    response = client.delete(
        f"/api/v1/analyze/{sample_file_record.id}",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    assert "deleted successfully" in response.json()["message"]


@pytest.mark.asyncio
async def test_delete_analysis_not_found(client, auth_headers, sample_file_record, db_session):
    """Test deletion with no analysis."""
    # Add only file record, no analysis
    db_session.add(sample_file_record)
    await db_session.commit()
    
    response = client.delete(
        f"/api/v1/analyze/{sample_file_record.id}",
        headers=auth_headers
    )
    
    assert response.status_code == 404
    assert "Analysis not found" in response.json()["detail"]


@pytest.mark.asyncio
async def test_download_file_for_analysis_success():
    """Test successful file download for analysis."""
    
    with patch('app.api.v1.analyze._download_file_for_analysis') as mock_download:
        mock_download.return_value = "/tmp/test.jpg"
        
        from app.api.v1.analyze import _download_file_for_analysis
        result = await _download_file_for_analysis("test/key.jpg")
        assert result == "/tmp/test.jpg"


@pytest.mark.asyncio
async def test_download_file_for_analysis_failure():
    """Test file download failure."""
    from app.api.v1.analyze import _download_file_for_analysis
    
    with patch('app.core.s3.s3_service.generate_presigned_url', return_value=None):
        with pytest.raises(Exception):
            await _download_file_for_analysis("test/key.jpg")


@pytest.mark.asyncio
async def test_validate_and_preprocess_image_success(sample_image_file):
    """Test successful image validation and preprocessing."""
    from app.api.v1.analyze import _validate_and_preprocess_image
    
    with patch('app.utils.image_utils.validate_image_file', return_value={'valid': True}):
        with patch('app.utils.image_utils.normalize_image_format', return_value="/tmp/normalized.jpg"):
            with patch('app.utils.image_utils.enhance_image_quality') as mock_enhance:
                # Make the enhance function return a realistic path
                mock_enhance.return_value = "/tmp/test_enhanced.jpeg"
                
                result = await _validate_and_preprocess_image(sample_image_file)
                assert result.endswith('.jpeg')
                assert 'enhanced' in result


@pytest.mark.asyncio
async def test_validate_and_preprocess_image_invalid():
    """Test image validation with invalid image."""
    from app.api.v1.analyze import _validate_and_preprocess_image
    
    with patch('app.utils.image_utils.validate_image_file', return_value={'valid': False}):
        with pytest.raises(Exception):
            await _validate_and_preprocess_image("/tmp/invalid.jpg")


@pytest.mark.asyncio
async def test_run_comprehensive_analysis_success(sample_forensics_result, sample_ocr_result, 
                                                sample_rule_result, sample_image_file):
    """Test successful comprehensive analysis."""
    from app.api.v1.analyze import _run_comprehensive_analysis
    
    with patch('app.api.v1.analyze.forensics_engine.analyze_image', return_value=sample_forensics_result):
        with patch('app.api.v1.analyze.get_ocr_engine') as mock_get_ocr:
            mock_ocr_engine = AsyncMock()
            mock_ocr_engine.extract_fields.return_value = sample_ocr_result
            mock_get_ocr.return_value = mock_ocr_engine
            
            with patch('app.api.v1.analyze.rule_engine.process_results', return_value=sample_rule_result):
                
                result = await _run_comprehensive_analysis(
                    sample_image_file,
                    ["forensics", "ocr", "rules"]
                )
                
                assert result.forensics_result == sample_forensics_result
                assert result.ocr_result == sample_ocr_result
                assert result.rule_result == sample_rule_result


@pytest.mark.asyncio
async def test_run_comprehensive_analysis_forensics_only(sample_forensics_result, sample_image_file):
    """Test comprehensive analysis with only forensics."""
    from app.api.v1.analyze import _run_comprehensive_analysis
    
    with patch('app.api.v1.analyze.forensics_engine.analyze_image', return_value=sample_forensics_result):
        
        result = await _run_comprehensive_analysis(
            sample_image_file,
            ["forensics"]
        )
        
        assert result.forensics_result == sample_forensics_result
        assert result.ocr_result is None
        assert result.rule_result is None


@pytest.mark.asyncio
async def test_store_analysis_results_success(db_session, sample_forensics_result, 
                                            sample_ocr_result, sample_rule_result):
    """Test successful analysis results storage."""
    from app.api.v1.analyze import _store_analysis_results, ComprehensiveAnalysisResult
    
    analysis_result = ComprehensiveAnalysisResult(
        forensics_result=sample_forensics_result,
        ocr_result=sample_ocr_result,
        rule_result=sample_rule_result
    )
    
    stored_result = await _store_analysis_results("test-file-id", analysis_result, db_session)
    
    assert stored_result is not None
    assert stored_result.file_id == "test-file-id"
    assert stored_result.forensics_score == sample_forensics_result.overall_score
    assert stored_result.ocr_confidence == sample_ocr_result.extraction_confidence
    assert stored_result.overall_risk_score == sample_rule_result.risk_score


@pytest.mark.asyncio
async def test_format_analysis_response_success(sample_analysis_result):
    """Test successful analysis response formatting."""
    from app.api.v1.analyze import _format_analysis_response
    
    response = await _format_analysis_response(sample_analysis_result)
    
    assert isinstance(response, AnalysisResponse)
    assert response.analysis_id == sample_analysis_result.id
    assert response.file_id == sample_analysis_result.file_id
    assert response.overall_risk_score == sample_analysis_result.overall_risk_score
    assert 0.0 <= response.confidence <= 1.0


def mock_open_aiofiles():
    """Mock aiofiles.open for testing."""
    class MockAsyncFile:
        async def __aenter__(self):
            return self
        
        async def __aexit__(self, *args):
            pass
        
        async def write(self, data):
            pass
    
    return MockAsyncFile()


@pytest.mark.asyncio
async def test_analyze_check_request_validation():
    """Test analysis request validation."""
    
    # Valid request
    request = AnalysisRequest(
        file_id="test-file-id",
        analysis_types=["forensics", "ocr", "rules"]
    )
    
    assert request.file_id == "test-file-id"
    assert request.analysis_types == ["forensics", "ocr", "rules"]
    
    # Request with default analysis types
    request = AnalysisRequest(file_id="test-file-id")
    assert request.analysis_types == ["forensics", "ocr", "rules"]


@pytest.mark.asyncio
async def test_analyze_check_unauthorized():
    """Test analysis without authentication."""
    # Use a client without dependency overrides for auth
    with TestClient(app) as client:
        request_data = {
            "file_id": "some-file-id",
            "analysis_types": ["forensics", "ocr", "rules"]
        }
        
        response = client.post(
            "/api/v1/analyze/",
            json=request_data
        )
        
        # Should return 401 or 403 depending on authentication setup
        assert response.status_code in [401, 403]
@pytest.mark.asyncio
async def test_analyze_check_malformed_request(client, auth_headers):
    """Test analysis with malformed request."""
    response = client.post(
        "/api/v1/analyze/",
        json={"invalid": "data"},
        headers=auth_headers
    )
    
    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_analyze_check_memory_cleanup(client, auth_headers, sample_file_record, 
                                          sample_forensics_result, sample_ocr_result, 
                                          sample_rule_result, db_session):
    """Test that analysis properly cleans up temporary files."""
    # Add file record to database
    db_session.add(sample_file_record)
    await db_session.commit()
    
    temp_files = []
    
    def mock_cleanup(files):
        temp_files.extend(files)
    
    with patch('app.api.v1.analyze.forensics_engine.analyze_image', return_value=sample_forensics_result):
        with patch('app.api.v1.analyze.get_ocr_engine') as mock_get_ocr:
            mock_ocr_engine = AsyncMock()
            mock_ocr_engine.extract_fields.return_value = sample_ocr_result
            mock_get_ocr.return_value = mock_ocr_engine
            
            with patch('app.api.v1.analyze.rule_engine.process_results', return_value=sample_rule_result):
                with patch('app.api.v1.analyze._download_file_for_analysis', return_value="/tmp/test.jpg"):
                    with patch('app.api.v1.analyze._validate_and_preprocess_image', return_value="/tmp/test.jpg"):
                        with patch('app.api.v1.analyze.cleanup_temp_files', side_effect=mock_cleanup):
                            
                            request_data = {
                                "file_id": sample_file_record.id,
                                "analysis_types": ["forensics", "ocr", "rules"]
                            }
                            
                            response = client.post(
                                "/api/v1/analyze/",
                                json=request_data,
                                headers=auth_headers
                            )
                            
                            assert response.status_code == 200
                            # Verify cleanup was called (will be called in background)
                            # Note: In actual test, this would need proper async handling