"""
Tests for risk scoring functionality.

This module tests the risk scoring logic and API endpoints to ensure
accurate risk assessment and proper error handling.
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime
from fastapi.testclient import TestClient

from app.core.scoring import (
    RiskScoreCalculator,
    calculate_risk_score,
    RiskLevel,
    RiskScoreData
)
from app.schemas.analysis import ForensicsResult, OCRResult, RuleEngineResult
from app.main import app


class TestRiskScoreCalculator:
    """Test the RiskScoreCalculator class."""
    
    def test_default_initialization(self):
        """Test default calculator initialization."""
        calculator = RiskScoreCalculator()
        
        assert calculator.category_weights == {
            'forensics': 0.4,
            'ocr': 0.3,
            'rules': 0.3
        }
        assert RiskLevel.LOW in calculator.risk_thresholds
        assert RiskLevel.MEDIUM in calculator.risk_thresholds
        assert RiskLevel.HIGH in calculator.risk_thresholds
        assert RiskLevel.CRITICAL in calculator.risk_thresholds
    
    def test_custom_weights_initialization(self):
        """Test calculator with custom weights."""
        custom_weights = {'forensics': 0.5, 'ocr': 0.3, 'rules': 0.2}
        calculator = RiskScoreCalculator(custom_weights)
        
        assert calculator.category_weights == custom_weights
    
    def test_calculate_forensics_score_low_risk(self):
        """Test forensics score calculation for low risk."""
        calculator = RiskScoreCalculator()
        
        forensics_result = ForensicsResult(
            edge_score=0.9,
            compression_score=0.1,
            font_score=0.9,
            overall_score=0.9,
            detected_anomalies=[],
            edge_inconsistencies={},
            compression_artifacts={},
            font_analysis={}
        )
        
        score = calculator._calculate_forensics_score(forensics_result)
        
        # Should be low risk (low score)
        assert 0 <= score <= 30
    
    def test_calculate_forensics_score_high_risk(self):
        """Test forensics score calculation for high risk."""
        calculator = RiskScoreCalculator()
        
        forensics_result = ForensicsResult(
            edge_score=0.1,
            compression_score=0.9,
            font_score=0.1,
            overall_score=0.1,
            detected_anomalies=['edge_tampering', 'compression_artifacts'],
            edge_inconsistencies={},
            compression_artifacts={},
            font_analysis={}
        )
        
        score = calculator._calculate_forensics_score(forensics_result)
        
        # Should be high risk (high score)
        assert score >= 70
    
    def test_calculate_ocr_score_low_risk(self):
        """Test OCR score calculation for low risk."""
        calculator = RiskScoreCalculator()
        
        ocr_result = OCRResult(
            payee="John Doe",
            amount="$100.00",
            date="2024-01-15",
            account_number="123456789",
            routing_number="021000021",
            check_number="1001",
            memo="Test payment",
            signature_detected=True,
            extraction_confidence=0.95,
            raw_text="Sample text",
            field_confidences={
                'payee': 0.9,
                'amount': 0.95,
                'date': 0.9
            }
        )
        
        score = calculator._calculate_ocr_score(ocr_result)
        
        # Should be low risk (low score)
        assert 0 <= score <= 30
    
    def test_calculate_ocr_score_high_risk(self):
        """Test OCR score calculation for high risk."""
        calculator = RiskScoreCalculator()
        
        ocr_result = OCRResult(
            payee=None,
            amount=None,
            date=None,
            account_number=None,
            routing_number=None,
            check_number=None,
            memo=None,
            signature_detected=False,
            extraction_confidence=0.2,
            raw_text="",
            field_confidences={}
        )
        
        score = calculator._calculate_ocr_score(ocr_result)
        
        # Should be high risk (high score)
        assert score >= 70
    
    def test_calculate_rules_score_low_risk(self):
        """Test rules score calculation for low risk."""
        calculator = RiskScoreCalculator()
        
        rule_result = RuleEngineResult(
            risk_score=0.1,
            violations=[],
            passed_rules=['all_checks_passed'],
            rule_scores={'basic_check': 0.0},
            confidence_factors={'overall': 0.9},
            recommendations=['Check appears legitimate'],
            overall_confidence=0.9
        )
        
        score = calculator._calculate_rules_score(rule_result)
        
        # Should be low risk (low score)
        assert 0 <= score <= 30
    
    def test_calculate_rules_score_high_risk(self):
        """Test rules score calculation for high risk."""
        calculator = RiskScoreCalculator()
        
        rule_result = RuleEngineResult(
            risk_score=0.9,
            violations=['suspicious_amount', 'missing_signature', 'invalid_date'],
            passed_rules=[],
            rule_scores={'amount_check': 0.8, 'signature_check': 0.9},
            confidence_factors={'overall': 0.5},
            recommendations=['Manual review required'],
            overall_confidence=0.5
        )
        
        score = calculator._calculate_rules_score(rule_result)
        
        # Should be high risk (high score)
        assert score >= 70
    
    def test_calculate_overall_score(self):
        """Test overall score calculation."""
        calculator = RiskScoreCalculator()
        
        forensics_score = 20
        ocr_score = 30
        rules_score = 40
        
        overall_score = calculator._calculate_overall_score(
            forensics_score, ocr_score, rules_score
        )
        
        expected_score = int(
            forensics_score * 0.4 + ocr_score * 0.3 + rules_score * 0.3
        )
        
        assert overall_score == expected_score
        assert 0 <= overall_score <= 100
    
    def test_determine_risk_level(self):
        """Test risk level determination."""
        calculator = RiskScoreCalculator()
        
        assert calculator._determine_risk_level(10) == RiskLevel.LOW
        assert calculator._determine_risk_level(65) == RiskLevel.MEDIUM
        assert calculator._determine_risk_level(85) == RiskLevel.HIGH
        assert calculator._determine_risk_level(95) == RiskLevel.CRITICAL
    
    def test_extract_risk_factors(self):
        """Test risk factor extraction."""
        calculator = RiskScoreCalculator()
        
        forensics_result = ForensicsResult(
            edge_score=0.2,
            compression_score=0.8,
            font_score=0.3,
            overall_score=0.4,
            detected_anomalies=['edge_tampering'],
            edge_inconsistencies={},
            compression_artifacts={},
            font_analysis={}
        )
        
        ocr_result = OCRResult(
            payee=None,
            amount="$100.00",
            date="2024-01-15",
            signature_detected=False,
            extraction_confidence=0.4,
            raw_text="",
            field_confidences={}
        )
        
        rule_result = RuleEngineResult(
            risk_score=0.6,
            violations=['suspicious_pattern'],
            passed_rules=[],
            rule_scores={},
            confidence_factors={},
            recommendations=[],
            overall_confidence=0.6
        )
        
        risk_factors = calculator._extract_risk_factors(
            forensics_result, ocr_result, rule_result
        )
        
        assert 'Poor edge quality detected' in risk_factors
        assert 'High compression artifacts' in risk_factors
        assert 'Font inconsistencies detected' in risk_factors
        assert 'edge_tampering' in risk_factors
        assert 'Low OCR extraction confidence' in risk_factors
        assert 'Missing payee information' in risk_factors
        assert 'No signature detected' in risk_factors
        assert 'suspicious_pattern' in risk_factors
    
    def test_calculate_confidence_level(self):
        """Test confidence level calculation."""
        calculator = RiskScoreCalculator()
        
        forensics_result = ForensicsResult(
            edge_score=0.8,
            compression_score=0.2,
            font_score=0.9,
            overall_score=0.85,
            detected_anomalies=[],
            edge_inconsistencies={},
            compression_artifacts={},
            font_analysis={}
        )
        
        ocr_result = OCRResult(
            payee="John Doe",
            amount="$100.00",
            date="2024-01-15",
            signature_detected=True,
            extraction_confidence=0.9,
            raw_text="Sample text",
            field_confidences={}
        )
        
        rule_result = RuleEngineResult(
            risk_score=0.1,
            violations=[],
            passed_rules=['all_checks'],
            rule_scores={},
            confidence_factors={'overall': 0.9},
            recommendations=[],
            overall_confidence=0.9
        )
        
        confidence = calculator._calculate_confidence_level(
            forensics_result, ocr_result, rule_result
        )
        
        assert 0.0 <= confidence <= 1.0
        assert confidence >= 0.8  # Should be high confidence
    
    def test_complete_risk_score_calculation(self):
        """Test complete risk score calculation."""
        calculator = RiskScoreCalculator()
        
        forensics_result = ForensicsResult(
            edge_score=0.5,
            compression_score=0.4,
            font_score=0.6,
            overall_score=0.55,
            detected_anomalies=['minor_compression'],
            edge_inconsistencies={},
            compression_artifacts={},
            font_analysis={}
        )
        
        ocr_result = OCRResult(
            payee="John Doe",
            amount="$100.00",
            date="2024-01-15",
            signature_detected=True,
            extraction_confidence=0.8,
            raw_text="Sample text",
            field_confidences={'payee': 0.8, 'amount': 0.9}
        )
        
        rule_result = RuleEngineResult(
            risk_score=0.4,
            violations=['minor_issue'],
            passed_rules=['basic_checks'],
            rule_scores={'basic': 0.2},
            confidence_factors={'overall': 0.7},
            recommendations=['Review recommended'],
            overall_confidence=0.7
        )
        
        result = calculator.calculate_risk_score(
            forensics_result, ocr_result, rule_result
        )
        
        assert isinstance(result, RiskScoreData)
        assert 0 <= result.overall_score <= 100
        assert result.risk_level in [RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL]
        assert 0.0 <= result.confidence_level <= 1.0
        assert isinstance(result.category_scores, dict)
        assert 'forensics' in result.category_scores
        assert 'ocr' in result.category_scores
        assert 'rules' in result.category_scores
        assert isinstance(result.risk_factors, list)
        assert isinstance(result.recommendations, list)
        assert isinstance(result.timestamp, datetime)


class TestRiskScoringAPI:
    """Test the risk scoring API endpoints."""
    
    @patch('app.api.v1.scoring._get_user_analysis')
    def test_calculate_risk_score_endpoint(self, mock_get_analysis, client):
        """Test risk score calculation endpoint."""
        # Mock analysis
        mock_analysis = Mock()
        mock_analysis.id = "test-analysis-id"
        mock_analysis.edge_inconsistencies = {'edge_score': 0.5}
        mock_analysis.compression_artifacts = {'compression_score': 0.5}
        mock_analysis.font_analysis = {'font_score': 0.5}
        mock_analysis.forensics_score = 0.5
        mock_analysis.extracted_fields = {
            'payee': 'John Doe',
            'amount': '$100.00',
            'signature_detected': True
        }
        mock_analysis.ocr_confidence = 0.8
        mock_analysis.overall_risk_score = 45.0
        mock_analysis.rule_violations = {
            'violations': ['minor_issue'],
            'passed_rules': ['basic_checks'],
            'rule_scores': {'basic': 0.2}
        }
        mock_analysis.confidence_factors = {'overall': 0.7}
        mock_get_analysis.return_value = mock_analysis
        
        # Test request
        response = client.post(
            "/api/v1/scoring/calculate",
            json={"analysis_id": "test-analysis-id"},
            headers={"Authorization": "Bearer test-token"}
        )
        
        # Assert response
        assert response.status_code == 200
        data = response.json()
        assert data['analysis_id'] == "test-analysis-id"
        assert 'overall_score' in data
        assert 'risk_level' in data
        assert 'category_scores' in data
        assert 'risk_factors' in data
        assert 'confidence_level' in data
        assert 'recommendations' in data
    
    def test_get_risk_score_config(self, client):
        """Test risk score configuration endpoint."""
        # Test request
        response = client.get(
            "/api/v1/scoring/config",
            headers={"Authorization": "Bearer test-token"}
        )
        
        # Assert response
        assert response.status_code == 200
        data = response.json()
        assert 'category_weights' in data
        assert 'risk_thresholds' in data
        assert 'confidence_factors' in data
        assert 'updated_at' in data
    
    def test_unauthorized_access(self):
        """Test unauthorized access to scoring endpoints."""
        # Create a client without dependency overrides
        
        client = TestClient(app)
        
        # Test without authorization header
        response = client.post(
            "/api/v1/scoring/calculate",
            json={"analysis_id": "test-analysis-id"}
        )
        
        assert response.status_code == 401  # Should be unauthorized


class TestRiskScoringHelpers:
    """Test helper functions for risk scoring."""
    
    def test_calculate_risk_score_helper(self):
        """Test the calculate_risk_score helper function."""
        forensics_result = ForensicsResult(
            edge_score=0.7,
            compression_score=0.3,
            font_score=0.8,
            overall_score=0.75,
            detected_anomalies=[],
            edge_inconsistencies={},
            compression_artifacts={},
            font_analysis={}
        )
        
        ocr_result = OCRResult(
            payee="John Doe",
            amount="$100.00",
            date="2024-01-15",
            signature_detected=True,
            extraction_confidence=0.9,
            raw_text="Sample text",
            field_confidences={}
        )
        
        rule_result = RuleEngineResult(
            risk_score=0.2,
            violations=[],
            passed_rules=['all_checks'],
            rule_scores={},
            confidence_factors={'overall': 0.8},
            recommendations=[],
            overall_confidence=0.8
        )
        
        result = calculate_risk_score(forensics_result, ocr_result, rule_result)
        
        assert isinstance(result, RiskScoreData)
        assert result.risk_level == RiskLevel.LOW  # Should be low risk
    
    def test_calculate_risk_score_with_custom_weights(self):
        """Test risk score calculation with custom weights."""
        custom_weights = {'forensics': 0.6, 'ocr': 0.2, 'rules': 0.2}
        
        forensics_result = ForensicsResult(
            edge_score=0.1,
            compression_score=0.9,
            font_score=0.1,
            overall_score=0.2,
            detected_anomalies=['tampering'],
            edge_inconsistencies={},
            compression_artifacts={},
            font_analysis={}
        )
        
        ocr_result = OCRResult(
            payee="John Doe",
            amount="$100.00",
            date="2024-01-15",
            signature_detected=True,
            extraction_confidence=0.9,
            raw_text="Sample text",
            field_confidences={}
        )
        
        rule_result = RuleEngineResult(
            risk_score=0.1,
            violations=[],
            passed_rules=['basic_checks'],
            rule_scores={},
            confidence_factors={'overall': 0.8},
            recommendations=[],
            overall_confidence=0.8
        )
        
        result = calculate_risk_score(
            forensics_result, ocr_result, rule_result, custom_weights
        )
        
        assert isinstance(result, RiskScoreData)
        # Should be higher risk due to forensics weight increase
        assert result.overall_score > 50
    
    def test_error_handling(self):
        """Test error handling in risk scoring."""
        # Test with invalid data
        forensics_result = ForensicsResult(
            edge_score=0.5,
            compression_score=0.5,
            font_score=0.5,
            overall_score=0.5,
            detected_anomalies=[],
            edge_inconsistencies={},
            compression_artifacts={},
            font_analysis={}
        )
        
        # Create invalid OCR result
        ocr_result = OCRResult(
            extraction_confidence=0.5,
            raw_text="",
            field_confidences={}
        )
        
        rule_result = RuleEngineResult(
            risk_score=0.5,
            violations=[],
            passed_rules=[],
            rule_scores={},
            confidence_factors={},
            recommendations=[],
            overall_confidence=0.5
        )
        
        # Should not raise an exception
        result = calculate_risk_score(forensics_result, ocr_result, rule_result)
        assert isinstance(result, RiskScoreData)


if __name__ == "__main__":
    pytest.main([__file__])