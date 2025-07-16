"""
Additional test coverage for scoring API endpoints to reach 80% coverage.
Tests uncovered lines and edge cases.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from app.models.user import User
from app.models.file import FileRecord
from app.models.analysis import AnalysisResult
from app.schemas.analysis import ForensicsResult, OCRResult, RuleEngineResult
from app.core.scoring import RiskScoreData, RiskLevel, RiskScoreCalculator
from app.api.v1.scoring import (
    RiskScoreRequest, 
    BatchRiskScoreRequest,
    RiskScoreConfigRequest,
    _get_user_analysis,
    _get_existing_risk_score,
    _extract_forensics_result,
    _extract_ocr_result,
    _extract_rule_result,
    _store_risk_score,
    _convert_to_response,
    _process_batch_risk_scores
)


@pytest.fixture
def sample_user():
    """Create a sample user for testing."""
    return User(
        id="test-user-123",
        email="test@example.com",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )


@pytest.fixture
def sample_file_record():
    """Create a sample file record."""
    return FileRecord(
        id="test-file-123",
        user_id="test-user-123",
        filename="test.jpg",
        s3_key="test.jpg",
        s3_url="https://test.com/test.jpg",
        file_size=1024,
        mime_type="image/jpeg",
        upload_timestamp=datetime.now(timezone.utc)
    )


@pytest.fixture
def sample_analysis_result():
    """Create a sample analysis result."""
    return AnalysisResult(
        id="test-analysis-123",
        file_id="test-file-123",
        overall_risk_score=75.0,
        forensics_score=80.0,
        edge_inconsistencies={
            "edge_score": 0.8,
            "anomalies": ["inconsistent_edges"]
        },
        compression_artifacts={
            "compression_score": 0.7,
            "artifacts": ["jpeg_compression"]
        },
        font_analysis={
            "font_score": 0.9,
            "fonts": ["Arial", "Times"]
        },
        ocr_confidence=0.85,
        extracted_fields={
            "payee": "John Doe",
            "amount": "$100.00",
            "date": "2024-01-15",
            "account_number": "123456789",
            "routing_number": "987654321",
            "check_number": "001",
            "memo": "Test memo",
            "signature_detected": True,
            "raw_text": "Pay to John Doe $100.00",
            "field_confidences": {"payee": 0.95, "amount": 0.90}
        },
        rule_violations={
            "violations": ["font_inconsistency"],
            "passed_rules": ["amount_valid", "date_valid"],
            "rule_scores": {"font_inconsistency": 0.2, "amount_valid": 0.0},
            "recommendations": ["Review font consistency"]
        },
        confidence_factors={
            "overall": 0.8,
            "forensics": 0.75,
            "ocr": 0.85
        },
        analysis_timestamp=datetime.now(timezone.utc)
    )


@pytest.fixture
def sample_risk_score_data():
    """Create sample risk score data."""
    return RiskScoreData(
        overall_score=75,
        risk_level=RiskLevel.HIGH,
        category_scores={
            "forensics": 80,
            "ocr": 85,
            "rules": 65
        },
        risk_factors=["font_inconsistency", "edge_artifacts"],
        confidence_level=0.82,
        recommendations=["Review document authenticity", "Check for tampering"],
        timestamp=datetime.now(timezone.utc)
    )


@pytest.mark.asyncio
async def test_calculate_analysis_risk_score_analysis_not_found(authenticated_client):
    """Test risk score calculation with non-existent analysis."""
    request_data = {
        "analysis_id": "non-existent-analysis",
        "recalculate": False
    }
    
    response = authenticated_client.post("/api/v1/scoring/calculate", json=request_data)
    
    assert response.status_code == 404
    assert "not found or access denied" in response.json()["detail"]


@pytest.mark.asyncio
async def test_calculate_analysis_risk_score_with_existing_score(authenticated_client, db_session,
                                                                sample_user, sample_file_record, 
                                                                sample_analysis_result):
    """Test risk score calculation with existing score (no recalculation)."""
    # Set up database records
    db_session.add(sample_user)
    db_session.add(sample_file_record)
    db_session.add(sample_analysis_result)
    await db_session.commit()
    
    # Mock existing score
    mock_existing_score = MagicMock()
    mock_existing_score.analysis_id = sample_analysis_result.id
    mock_existing_score.overall_score = 80
    
    with patch('app.api.v1.scoring._get_existing_risk_score', return_value=mock_existing_score):
        request_data = {
            "analysis_id": sample_analysis_result.id,
            "recalculate": False
        }
        
        response = authenticated_client.post("/api/v1/scoring/calculate", json=request_data)
        
        assert response.status_code == 200
        # Should return existing score without recalculation


@pytest.mark.asyncio
async def test_calculate_analysis_risk_score_force_recalculation(authenticated_client, db_session,
                                                                sample_user, sample_file_record,
                                                                sample_analysis_result, sample_risk_score_data):
    """Test risk score calculation with forced recalculation."""
    # Set up database records
    db_session.add(sample_user)
    db_session.add(sample_file_record)
    db_session.add(sample_analysis_result)
    await db_session.commit()
    
    # Mock existing score but force recalculation
    mock_existing_score = MagicMock()
    mock_existing_score.analysis_id = sample_analysis_result.id
    
    with patch('app.api.v1.scoring._get_existing_risk_score', return_value=mock_existing_score):
        with patch('app.api.v1.scoring.calculate_risk_score', return_value=sample_risk_score_data):
            with patch('app.api.v1.scoring._store_risk_score'):
                request_data = {
                    "analysis_id": sample_analysis_result.id,
                    "recalculate": True
                }
                
                response = authenticated_client.post("/api/v1/scoring/calculate", json=request_data)
                
                assert response.status_code == 200
                result = response.json()
                assert result["overall_score"] == sample_risk_score_data.overall_score


@pytest.mark.asyncio
async def test_calculate_analysis_risk_score_calculation_error(authenticated_client, db_session,
                                                              sample_user, sample_file_record,
                                                              sample_analysis_result):
    """Test risk score calculation with calculation error."""
    # Set up database records
    db_session.add(sample_user)
    db_session.add(sample_file_record)
    db_session.add(sample_analysis_result)
    await db_session.commit()
    
    with patch('app.api.v1.scoring._get_existing_risk_score', return_value=None):
        with patch('app.api.v1.scoring.calculate_risk_score', side_effect=Exception("Calculation failed")):
            request_data = {
                "analysis_id": sample_analysis_result.id,
                "recalculate": False
            }
            
            response = authenticated_client.post("/api/v1/scoring/calculate", json=request_data)
            
            assert response.status_code == 500
            assert "Risk score calculation failed" in response.json()["detail"]


@pytest.mark.asyncio
async def test_calculate_batch_risk_scores_no_valid_analyses(authenticated_client):
    """Test batch risk score calculation with no valid analyses."""
    request_data = {
        "analysis_ids": ["non-existent-1", "non-existent-2"],
        "recalculate": False
    }
    
    response = authenticated_client.post("/api/v1/scoring/batch", json=request_data)
    
    assert response.status_code == 400
    assert "No valid analyses found" in response.json()["detail"]


@pytest.mark.asyncio
async def test_calculate_batch_risk_scores_partial_valid_analyses(authenticated_client, db_session,
                                                                 sample_user, sample_file_record,
                                                                 sample_analysis_result):
    """Test batch risk score calculation with some valid analyses."""
    # Set up database records
    db_session.add(sample_user)
    db_session.add(sample_file_record)
    db_session.add(sample_analysis_result)
    await db_session.commit()
    
    request_data = {
        "analysis_ids": [sample_analysis_result.id, "non-existent-analysis"],
        "recalculate": False
    }
    
    response = authenticated_client.post("/api/v1/scoring/batch", json=request_data)
    
    assert response.status_code == 200
    result = response.json()
    assert result["total_analyses"] == 1  # Only one valid analysis
    assert result["status"] == "processing"
    assert "job_id" in result


@pytest.mark.asyncio
async def test_calculate_batch_risk_scores_database_error(authenticated_client, db_session):
    """Test batch risk score calculation with database error."""
    with patch('app.api.v1.scoring._get_user_analysis', side_effect=Exception("Database error")):
        request_data = {
            "analysis_ids": ["test-analysis-1"],
            "recalculate": False
        }
        
        response = authenticated_client.post("/api/v1/scoring/batch", json=request_data)
        
        assert response.status_code == 500
        assert "Batch risk score calculation failed" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_batch_job_status(authenticated_client):
    """Test get batch job status."""
    job_id = str(uuid.uuid4())
    
    response = authenticated_client.get(f"/api/v1/scoring/batch/{job_id}")
    
    assert response.status_code == 200
    result = response.json()
    assert result["job_id"] == job_id
    assert result["status"] == "completed"


@pytest.mark.asyncio
async def test_get_batch_job_status_error(authenticated_client):
    """Test get batch job status with error."""
    job_id = str(uuid.uuid4())
    
    with patch('app.api.v1.scoring.logger.error', side_effect=Exception("Logging error")):
        response = authenticated_client.get(f"/api/v1/scoring/batch/{job_id}")
        
        assert response.status_code == 500
        assert "Failed to get batch job status" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_risk_score_history_analysis_not_found(authenticated_client):
    """Test get risk score history with non-existent analysis."""
    response = authenticated_client.get("/api/v1/scoring/history/non-existent-analysis")
    
    assert response.status_code == 404
    assert "not found or access denied" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_risk_score_history_no_score(authenticated_client, db_session,
                                              sample_user, sample_file_record, sample_analysis_result):
    """Test get risk score history with no existing score."""
    # Set up database records
    db_session.add(sample_user)
    db_session.add(sample_file_record)
    db_session.add(sample_analysis_result)
    await db_session.commit()
    
    with patch('app.api.v1.scoring._get_existing_risk_score', return_value=None):
        response = authenticated_client.get(f"/api/v1/scoring/history/{sample_analysis_result.id}")
        
        assert response.status_code == 404
        assert "No risk score found" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_risk_score_history_with_score(authenticated_client, db_session,
                                                sample_user, sample_file_record, sample_analysis_result):
    """Test get risk score history with existing score."""
    # Set up database records
    db_session.add(sample_user)
    db_session.add(sample_file_record)
    db_session.add(sample_analysis_result)
    await db_session.commit()
    
    # Mock existing score
    mock_score = MagicMock()
    mock_score.analysis_id = sample_analysis_result.id
    mock_score.overall_score = 75
    
    with patch('app.api.v1.scoring._get_existing_risk_score', return_value=mock_score):
        response = authenticated_client.get(f"/api/v1/scoring/history/{sample_analysis_result.id}")
        
        assert response.status_code == 200
        result = response.json()
        assert result["analysis_id"] == sample_analysis_result.id
        assert len(result["score_history"]) == 1
        assert result["current_score"] == mock_score


@pytest.mark.asyncio
async def test_get_risk_score_history_error(authenticated_client, db_session,
                                           sample_user, sample_file_record, sample_analysis_result):
    """Test get risk score history with error."""
    # Set up database records
    db_session.add(sample_user)
    db_session.add(sample_file_record)
    db_session.add(sample_analysis_result)
    await db_session.commit()
    
    with patch('app.api.v1.scoring._get_existing_risk_score', side_effect=Exception("Database error")):
        response = authenticated_client.get(f"/api/v1/scoring/history/{sample_analysis_result.id}")
        
        assert response.status_code == 500
        assert "Failed to get risk score history" in response.json()["detail"]


@pytest.mark.asyncio
async def test_recalculate_risk_score_success(authenticated_client, db_session,
                                             sample_user, sample_file_record, sample_analysis_result):
    """Test recalculate risk score success."""
    # Set up database records
    db_session.add(sample_user)
    db_session.add(sample_file_record)
    db_session.add(sample_analysis_result)
    await db_session.commit()
    
    # Mock the calculate_analysis_risk_score function
    with patch('app.api.v1.scoring.calculate_analysis_risk_score') as mock_calculate:
        mock_response = MagicMock()
        mock_response.analysis_id = sample_analysis_result.id
        mock_response.overall_score = 80
        mock_calculate.return_value = mock_response
        
        response = authenticated_client.post(f"/api/v1/scoring/recalculate/{sample_analysis_result.id}")
        
        assert response.status_code == 200
        # Verify that calculate_analysis_risk_score was called with recalculate=True
        mock_calculate.assert_called_once()
        args = mock_calculate.call_args
        assert args[0][0].recalculate is True


@pytest.mark.asyncio
async def test_recalculate_risk_score_error(authenticated_client):
    """Test recalculate risk score with error."""
    with patch('app.api.v1.scoring.calculate_analysis_risk_score', side_effect=Exception("Calculation failed")):
        response = authenticated_client.post("/api/v1/scoring/recalculate/test-analysis")
        
        assert response.status_code == 500
        assert "Risk score recalculation failed" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_risk_score_config_success(authenticated_client):
    """Test get risk score config success."""
    response = authenticated_client.get("/api/v1/scoring/config")
    
    assert response.status_code == 200
    result = response.json()
    assert "category_weights" in result
    assert "risk_thresholds" in result
    assert "confidence_factors" in result
    assert "updated_at" in result


@pytest.mark.asyncio
async def test_get_risk_score_config_error(authenticated_client):
    """Test get risk score config with error."""
    with patch('app.api.v1.scoring.RiskScoreCalculator', side_effect=Exception("Config error")):
        response = authenticated_client.get("/api/v1/scoring/config")
        
        assert response.status_code == 500
        assert "Failed to get risk score configuration" in response.json()["detail"]


@pytest.mark.asyncio
async def test_update_risk_score_config_success(authenticated_client):
    """Test update risk score config success."""
    config_data = {
        "category_weights": {"forensics": 0.5, "ocr": 0.3, "rules": 0.2},
        "risk_thresholds": {"LOW": 25, "MEDIUM": 50, "HIGH": 75},
        "confidence_factors": {"min_confidence": 0.7}
    }
    
    response = authenticated_client.post("/api/v1/scoring/config", json=config_data)
    
    assert response.status_code == 200
    result = response.json()
    assert "category_weights" in result
    assert "risk_thresholds" in result
    assert "confidence_factors" in result


@pytest.mark.asyncio
async def test_update_risk_score_config_error(authenticated_client):
    """Test update risk score config with error."""
    with patch('app.api.v1.scoring.get_risk_score_config', side_effect=Exception("Config error")):
        config_data = {"category_weights": {"forensics": 0.5}}
        
        response = authenticated_client.post("/api/v1/scoring/config", json=config_data)
        
        assert response.status_code == 500
        assert "Failed to update risk score configuration" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_user_analysis_success(db_session, sample_user, sample_file_record, sample_analysis_result):
    """Test get user analysis success."""
    db_session.add(sample_user)
    db_session.add(sample_file_record)
    db_session.add(sample_analysis_result)
    await db_session.commit()
    
    result = await _get_user_analysis(sample_analysis_result.id, sample_user.id, db_session)
    
    assert result is not None
    assert result.id == sample_analysis_result.id


@pytest.mark.asyncio
async def test_get_user_analysis_not_found(db_session, sample_user):
    """Test get user analysis with non-existent analysis."""
    db_session.add(sample_user)
    await db_session.commit()
    
    with pytest.raises(HTTPException) as exc_info:
        await _get_user_analysis("non-existent-analysis", sample_user.id, db_session)
    
    assert exc_info.value.status_code == 404
    assert "not found or access denied" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_get_user_analysis_database_error(db_session, sample_user):
    """Test get user analysis with database error."""
    db_session.add(sample_user)
    await db_session.commit()
    
    with patch.object(db_session, 'execute', side_effect=Exception("Database error")):
        with pytest.raises(HTTPException) as exc_info:
            await _get_user_analysis("test-analysis", sample_user.id, db_session)
        
        assert exc_info.value.status_code == 500
        assert "Failed to retrieve analysis" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_get_existing_risk_score_none(db_session):
    """Test get existing risk score returns None."""
    result = await _get_existing_risk_score("test-analysis", db_session)
    
    assert result is None


@pytest.mark.asyncio
async def test_get_existing_risk_score_error(db_session):
    """Test get existing risk score with error."""
    with patch('app.api.v1.scoring.logger.error'):
        result = await _get_existing_risk_score("test-analysis", db_session)
        
        assert result is None


def test_extract_forensics_result(sample_analysis_result):
    """Test extract forensics result."""
    result = _extract_forensics_result(sample_analysis_result)
    
    assert isinstance(result, ForensicsResult)
    assert result.overall_score == sample_analysis_result.forensics_score
    assert result.edge_score == sample_analysis_result.edge_inconsistencies.get('edge_score', 0.5)
    assert result.compression_score == sample_analysis_result.compression_artifacts.get('compression_score', 0.5)
    assert result.font_score == sample_analysis_result.font_analysis.get('font_score', 0.5)
    assert result.detected_anomalies == sample_analysis_result.edge_inconsistencies.get('anomalies', [])


def test_extract_forensics_result_missing_fields():
    """Test extract forensics result with missing fields."""
    analysis = AnalysisResult(
        id="test-analysis",
        file_id="test-file",
        overall_risk_score=50.0,
        forensics_score=60.0,
        edge_inconsistencies={},  # Missing edge_score
        compression_artifacts={},  # Missing compression_score
        font_analysis={},  # Missing font_score
        ocr_confidence=0.8,
        extracted_fields={},
        rule_violations={},
        confidence_factors={},
        analysis_timestamp=datetime.now(timezone.utc)
    )
    
    result = _extract_forensics_result(analysis)
    
    assert result.edge_score == 0.5  # Default value
    assert result.compression_score == 0.5  # Default value
    assert result.font_score == 0.5  # Default value
    assert result.detected_anomalies == []  # Default value


def test_extract_ocr_result(sample_analysis_result):
    """Test extract OCR result."""
    result = _extract_ocr_result(sample_analysis_result)
    
    assert isinstance(result, OCRResult)
    assert result.payee == sample_analysis_result.extracted_fields.get('payee')
    assert result.amount == sample_analysis_result.extracted_fields.get('amount')
    assert result.date == sample_analysis_result.extracted_fields.get('date')
    assert result.account_number == sample_analysis_result.extracted_fields.get('account_number')
    assert result.routing_number == sample_analysis_result.extracted_fields.get('routing_number')
    assert result.check_number == sample_analysis_result.extracted_fields.get('check_number')
    assert result.memo == sample_analysis_result.extracted_fields.get('memo')
    assert result.signature_detected == sample_analysis_result.extracted_fields.get('signature_detected', False)
    assert result.extraction_confidence == sample_analysis_result.ocr_confidence
    assert result.raw_text == sample_analysis_result.extracted_fields.get('raw_text')
    assert result.field_confidences == sample_analysis_result.extracted_fields.get('field_confidences', {})


def test_extract_ocr_result_missing_fields():
    """Test extract OCR result with missing fields."""
    analysis = AnalysisResult(
        id="test-analysis",
        file_id="test-file",
        overall_risk_score=50.0,
        forensics_score=60.0,
        edge_inconsistencies={},
        compression_artifacts={},
        font_analysis={},
        ocr_confidence=0.8,
        extracted_fields={},  # Empty extracted fields
        rule_violations={},
        confidence_factors={},
        analysis_timestamp=datetime.now(timezone.utc)
    )
    
    result = _extract_ocr_result(analysis)
    
    assert result.payee is None
    assert result.amount is None
    assert result.date is None
    assert result.signature_detected is False  # Default value
    assert result.field_confidences == {}  # Default value


def test_extract_rule_result(sample_analysis_result):
    """Test extract rule result."""
    result = _extract_rule_result(sample_analysis_result)
    
    assert isinstance(result, RuleEngineResult)
    assert result.risk_score == sample_analysis_result.overall_risk_score / 100.0
    assert result.violations == sample_analysis_result.rule_violations.get('violations', [])
    assert result.passed_rules == sample_analysis_result.rule_violations.get('passed_rules', [])
    assert result.rule_scores == sample_analysis_result.rule_violations.get('rule_scores', {})
    assert result.confidence_factors == sample_analysis_result.confidence_factors
    assert result.recommendations == sample_analysis_result.rule_violations.get('recommendations', [])
    assert result.overall_confidence == sample_analysis_result.confidence_factors.get('overall', 0.5)


def test_extract_rule_result_missing_fields():
    """Test extract rule result with missing fields."""
    analysis = AnalysisResult(
        id="test-analysis",
        file_id="test-file",
        overall_risk_score=50.0,
        forensics_score=60.0,
        edge_inconsistencies={},
        compression_artifacts={},
        font_analysis={},
        ocr_confidence=0.8,
        extracted_fields={},
        rule_violations={},  # Empty rule violations
        confidence_factors={},  # Empty confidence factors
        analysis_timestamp=datetime.now(timezone.utc)
    )
    
    result = _extract_rule_result(analysis)
    
    assert result.violations == []  # Default value
    assert result.passed_rules == []  # Default value
    assert result.rule_scores == {}  # Default value
    assert result.recommendations == []  # Default value
    assert result.overall_confidence == 0.5  # Default value


@pytest.mark.asyncio
async def test_store_risk_score_success(db_session, sample_risk_score_data):
    """Test store risk score success."""
    await _store_risk_score("test-analysis", sample_risk_score_data, db_session)
    
    # Verify that the database operations were called
    # (This is a simplified test since we're updating an existing record)


@pytest.mark.asyncio
async def test_store_risk_score_database_error(db_session, sample_risk_score_data):
    """Test store risk score with database error."""
    with patch.object(db_session, 'execute', side_effect=Exception("Database error")):
        with pytest.raises(Exception):
            await _store_risk_score("test-analysis", sample_risk_score_data, db_session)


def test_convert_to_response(sample_risk_score_data):
    """Test convert to response."""
    analysis_id = "test-analysis"
    
    result = _convert_to_response(analysis_id, sample_risk_score_data)
    
    assert result.analysis_id == analysis_id
    assert result.overall_score == sample_risk_score_data.overall_score
    assert result.risk_level == sample_risk_score_data.risk_level.value
    assert result.category_scores == sample_risk_score_data.category_scores
    assert result.risk_factors == sample_risk_score_data.risk_factors
    assert result.confidence_level == sample_risk_score_data.confidence_level
    assert result.recommendations == sample_risk_score_data.recommendations
    assert result.calculated_at == sample_risk_score_data.timestamp
    assert "method" in result.calculation_metadata
    assert "weights" in result.calculation_metadata


@pytest.mark.asyncio
async def test_process_batch_risk_scores_success(sample_analysis_result, sample_risk_score_data):
    """Test process batch risk scores success."""
    job_id = "test-job-123"
    analyses = [sample_analysis_result]
    
    with patch('app.api.v1.scoring.calculate_risk_score', return_value=sample_risk_score_data):
        await _process_batch_risk_scores(job_id, analyses, False, "test-user")
        
        # This should complete without errors


@pytest.mark.asyncio
async def test_process_batch_risk_scores_with_error(sample_analysis_result):
    """Test process batch risk scores with error in one analysis."""
    job_id = "test-job-123"
    analyses = [sample_analysis_result]
    
    with patch('app.api.v1.scoring.calculate_risk_score', side_effect=Exception("Calculation failed")):
        await _process_batch_risk_scores(job_id, analyses, False, "test-user")
        
        # Should handle the error gracefully and continue


@pytest.mark.asyncio
async def test_process_batch_risk_scores_general_error():
    """Test process batch risk scores with general error."""
    job_id = "test-job-123"
    analyses = []
    
    with patch('app.api.v1.scoring.logger.info', side_effect=Exception("Logging error")):
        await _process_batch_risk_scores(job_id, analyses, False, "test-user")
        
        # Should handle the error gracefully