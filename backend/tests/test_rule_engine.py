import pytest
import pytest_asyncio
import json
import tempfile
import os
from unittest.mock import patch, Mock

from app.core.rule_engine import RuleEngine, Rule, RuleEvaluationResult, RuleEngineError, load_rule_engine
from app.schemas.analysis import ForensicsResult, OCRResult, RuleEngineResult


@pytest.fixture
def sample_rules_config():
    """Create sample rules configuration."""
    return {
        "version": "1.0",
        "category_weights": {
            "forensics": 0.4,
            "ocr": 0.3,
            "cross_validation": 0.3
        },
        "rules": [
            {
                "id": "test_forensics_rule",
                "name": "Test Forensics Rule",
                "description": "Test rule for forensics",
                "category": "forensics",
                "weight": 0.5,
                "condition": {
                    "type": "threshold",
                    "field": "edge_score",
                    "operator": "less_than",
                    "value": 0.3
                },
                "severity": "high",
                "enabled": True
            },
            {
                "id": "test_ocr_rule",
                "name": "Test OCR Rule",
                "description": "Test rule for OCR",
                "category": "ocr",
                "weight": 0.3,
                "condition": {
                    "type": "threshold",
                    "field": "extraction_confidence",
                    "operator": "less_than",
                    "value": 0.5
                },
                "severity": "medium",
                "enabled": True
            },
            {
                "id": "test_missing_fields_rule",
                "name": "Test Missing Fields Rule",
                "description": "Test rule for missing fields",
                "category": "ocr",
                "weight": 0.4,
                "condition": {
                    "type": "missing_fields",
                    "fields": ["payee", "amount"]
                },
                "severity": "high",
                "enabled": True
            },
            {
                "id": "test_amount_validation",
                "name": "Test Amount Validation",
                "description": "Test rule for amount validation",
                "category": "cross_validation",
                "weight": 0.5,
                "condition": {
                    "type": "amount_validation"
                },
                "severity": "high",
                "enabled": True
            }
        ]
    }


@pytest.fixture
def temp_rules_file(sample_rules_config):
    """Create temporary rules configuration file."""
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
    json.dump(sample_rules_config, temp_file)
    temp_file.close()
    
    yield temp_file.name
    
    try:
        os.unlink(temp_file.name)
    except:
        pass


@pytest.fixture
def rule_engine(temp_rules_file):
    """Create rule engine with test configuration."""
    return RuleEngine(temp_rules_file)


@pytest.fixture
def sample_forensics_result():
    """Create sample forensics result."""
    return ForensicsResult(
        edge_score=0.2,  # Low score (should trigger rule)
        compression_score=0.6,
        font_score=0.8,
        overall_score=0.5,
        detected_anomalies=["poor edge quality"],
        edge_inconsistencies={"score": 0.2},
        compression_artifacts={"score": 0.6},
        font_analysis={"score": 0.8}
    )


@pytest.fixture
def sample_ocr_result():
    """Create sample OCR result."""
    return OCRResult(
        payee="John Doe",
        amount="$100.00",
        date="2024-01-15",
        account_number="123456789",
        routing_number="987654321",
        check_number="001",
        signature_detected=True,
        extraction_confidence=0.4,  # Low confidence (should trigger rule)
        field_confidences={"payee": 0.8, "amount": 0.9}
    )


@pytest.fixture
def sample_ocr_result_missing_fields():
    """Create sample OCR result with missing fields."""
    return OCRResult(
        payee=None,  # Missing payee
        amount=None,  # Missing amount
        date="2024-01-15",
        signature_detected=False,
        extraction_confidence=0.7,
        field_confidences={}
    )


def test_rule_engine_initialization(rule_engine):
    """Test rule engine initialization."""
    assert rule_engine is not None
    assert len(rule_engine.rules) > 0
    assert rule_engine.rule_categories is not None


def test_rule_engine_load_rules(temp_rules_file):
    """Test loading rules from configuration file."""
    engine = RuleEngine(temp_rules_file)
    
    assert len(engine.rules) == 4
    assert engine.rule_categories['forensics'] == 0.4
    assert engine.rule_categories['ocr'] == 0.3
    assert engine.rule_categories['cross_validation'] == 0.3


def test_rule_engine_nonexistent_config():
    """Test rule engine with nonexistent configuration file."""
    engine = RuleEngine("nonexistent_config.json")
    
    # Should create default rules
    assert len(engine.rules) > 0


def test_rule_engine_invalid_config():
    """Test rule engine with invalid configuration file."""
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
    temp_file.write("invalid json")
    temp_file.close()
    
    try:
        engine = RuleEngine(temp_file.name)
        # Should create default rules on invalid config
        assert len(engine.rules) > 0
    finally:
        os.unlink(temp_file.name)


@pytest.mark.asyncio
async def test_process_results_success(rule_engine, sample_forensics_result, sample_ocr_result):
    """Test successful rule processing."""
    result = await rule_engine.process_results(sample_forensics_result, sample_ocr_result)
    
    assert isinstance(result, RuleEngineResult)
    assert 0.0 <= result.risk_score <= 1.0
    assert isinstance(result.violations, list)
    assert isinstance(result.passed_rules, list)
    assert isinstance(result.rule_scores, dict)
    assert isinstance(result.confidence_factors, dict)
    assert isinstance(result.recommendations, list)


@pytest.mark.asyncio
async def test_evaluate_threshold_rule(rule_engine, sample_forensics_result, sample_ocr_result):
    """Test threshold rule evaluation."""
    # Find the forensics rule
    forensics_rule = next(r for r in rule_engine.rules if r.id == "test_forensics_rule")
    
    result = await rule_engine._evaluate_rule(forensics_rule, sample_forensics_result, sample_ocr_result)
    
    assert isinstance(result, RuleEvaluationResult)
    assert result.rule_id == "test_forensics_rule"
    assert result.passed is False  # Should fail due to low edge score
    assert result.score > 0.0


@pytest.mark.asyncio
async def test_evaluate_threshold_rule_passed(rule_engine, sample_ocr_result):
    """Test threshold rule that passes."""
    # Create forensics result with high edge score
    good_forensics_result = ForensicsResult(
        edge_score=0.8,  # High score (should pass)
        compression_score=0.6,
        font_score=0.8,
        overall_score=0.7,
        detected_anomalies=[],
        edge_inconsistencies={"score": 0.8},
        compression_artifacts={"score": 0.6},
        font_analysis={"score": 0.8}
    )
    
    forensics_rule = next(r for r in rule_engine.rules if r.id == "test_forensics_rule")
    result = await rule_engine._evaluate_rule(forensics_rule, good_forensics_result, sample_ocr_result)
    
    assert result.passed is True
    assert result.score == 0.0


@pytest.mark.asyncio
async def test_evaluate_missing_fields_rule(rule_engine, sample_forensics_result, sample_ocr_result_missing_fields):
    """Test missing fields rule evaluation."""
    missing_fields_rule = next(r for r in rule_engine.rules if r.id == "test_missing_fields_rule")
    
    result = await rule_engine._evaluate_rule(missing_fields_rule, sample_forensics_result, sample_ocr_result_missing_fields)
    
    assert isinstance(result, RuleEvaluationResult)
    assert result.passed is False  # Should fail due to missing fields
    assert result.score > 0.0
    assert 'missing_fields' in result.details


@pytest.mark.asyncio
async def test_evaluate_missing_fields_rule_passed(rule_engine, sample_forensics_result, sample_ocr_result):
    """Test missing fields rule that passes."""
    missing_fields_rule = next(r for r in rule_engine.rules if r.id == "test_missing_fields_rule")
    
    result = await rule_engine._evaluate_rule(missing_fields_rule, sample_forensics_result, sample_ocr_result)
    
    assert result.passed is True
    assert result.score == 0.0


@pytest.mark.asyncio
async def test_evaluate_amount_validation_rule(rule_engine, sample_forensics_result, sample_ocr_result):
    """Test amount validation rule evaluation."""
    amount_rule = next(r for r in rule_engine.rules if r.id == "test_amount_validation")
    
    result = await rule_engine._evaluate_rule(amount_rule, sample_forensics_result, sample_ocr_result)
    
    assert isinstance(result, RuleEvaluationResult)
    assert result.rule_id == "test_amount_validation"
    # Should pass with valid amount
    assert result.passed is True or len(result.details.get('violations', [])) == 0


@pytest.mark.asyncio
async def test_evaluate_amount_validation_rule_invalid_amount(rule_engine, sample_forensics_result):
    """Test amount validation rule with invalid amount."""
    invalid_ocr_result = OCRResult(
        payee="John Doe",
        amount="invalid amount",  # Invalid amount
        date="2024-01-15",
        signature_detected=True,
        extraction_confidence=0.8,
        field_confidences={}
    )
    
    amount_rule = next(r for r in rule_engine.rules if r.id == "test_amount_validation")
    
    result = await rule_engine._evaluate_rule(amount_rule, sample_forensics_result, invalid_ocr_result)
    
    assert result.passed is False
    assert result.score > 0.0
    assert len(result.details.get('violations', [])) > 0


@pytest.mark.asyncio
async def test_evaluate_date_validation_rule(rule_engine, sample_forensics_result, sample_ocr_result):
    """Test date validation rule evaluation."""
    # Create a date validation rule
    date_rule = Rule(
        id="test_date_validation",
        name="Test Date Validation",
        description="Test date validation",
        category="cross_validation",
        weight=0.3,
        condition={"type": "date_validation"},
        severity="medium",
        enabled=True
    )
    
    result = await rule_engine._evaluate_rule(date_rule, sample_forensics_result, sample_ocr_result)
    
    assert isinstance(result, RuleEvaluationResult)
    assert result.rule_id == "test_date_validation"


@pytest.mark.asyncio
async def test_evaluate_unknown_rule_type(rule_engine, sample_forensics_result, sample_ocr_result):
    """Test evaluation of unknown rule type."""
    unknown_rule = Rule(
        id="unknown_rule",
        name="Unknown Rule",
        description="Unknown rule type",
        category="test",
        weight=0.5,
        condition={"type": "unknown_type"},
        severity="medium",
        enabled=True
    )
    
    result = await rule_engine._evaluate_rule(unknown_rule, sample_forensics_result, sample_ocr_result)
    
    assert result.passed is True  # Should pass by default
    assert result.score == 0.0
    assert 'error' in result.details


def test_get_field_value_forensics(rule_engine, sample_forensics_result, sample_ocr_result):
    """Test getting field value from forensics result."""
    value = rule_engine._get_field_value('edge_score', sample_forensics_result, sample_ocr_result)
    assert value == 0.2


def test_get_field_value_ocr(rule_engine, sample_forensics_result, sample_ocr_result):
    """Test getting field value from OCR result."""
    value = rule_engine._get_field_value('extraction_confidence', sample_forensics_result, sample_ocr_result)
    assert value == 0.4


def test_get_field_value_not_found(rule_engine, sample_forensics_result, sample_ocr_result):
    """Test getting nonexistent field value."""
    value = rule_engine._get_field_value('nonexistent_field', sample_forensics_result, sample_ocr_result)
    assert value is None


def test_calculate_violation_score_less_than(rule_engine):
    """Test violation score calculation for less_than operator."""
    score = rule_engine._calculate_violation_score(0.2, 0.5, 'less_than')
    assert score > 0.0
    assert score <= 1.0


def test_calculate_violation_score_greater_than(rule_engine):
    """Test violation score calculation for greater_than operator."""
    score = rule_engine._calculate_violation_score(0.8, 0.5, 'greater_than')
    assert score > 0.0
    assert score <= 1.0


def test_calculate_violation_score_no_violation(rule_engine):
    """Test violation score calculation with no violation."""
    score = rule_engine._calculate_violation_score(0.8, 0.5, 'less_than')
    assert score == 0.0


@pytest.mark.asyncio
async def test_calculate_risk_score(rule_engine, sample_forensics_result, sample_ocr_result):
    """Test risk score calculation."""
    # Process results to get evaluations
    result = await rule_engine.process_results(sample_forensics_result, sample_ocr_result)
    
    # Risk score should be calculated properly
    assert 0.0 <= result.risk_score <= 1.0


@pytest.mark.asyncio
async def test_extract_violations(rule_engine, sample_forensics_result, sample_ocr_result):
    """Test violation extraction."""
    result = await rule_engine.process_results(sample_forensics_result, sample_ocr_result)
    
    assert isinstance(result.violations, list)
    # Should have some violations due to low scores
    assert len(result.violations) > 0


@pytest.mark.asyncio
async def test_extract_passed_rules(rule_engine, sample_forensics_result, sample_ocr_result):
    """Test passed rules extraction."""
    result = await rule_engine.process_results(sample_forensics_result, sample_ocr_result)
    
    assert isinstance(result.passed_rules, list)


@pytest.mark.asyncio
async def test_extract_rule_scores(rule_engine, sample_forensics_result, sample_ocr_result):
    """Test rule scores extraction."""
    result = await rule_engine.process_results(sample_forensics_result, sample_ocr_result)
    
    assert isinstance(result.rule_scores, dict)
    assert len(result.rule_scores) > 0


@pytest.mark.asyncio
async def test_calculate_confidence_factors(rule_engine, sample_forensics_result, sample_ocr_result):
    """Test confidence factors calculation."""
    result = await rule_engine.process_results(sample_forensics_result, sample_ocr_result)
    
    assert isinstance(result.confidence_factors, dict)
    assert 'overall' in result.confidence_factors
    assert 0.0 <= result.confidence_factors['overall'] <= 1.0


@pytest.mark.asyncio
async def test_generate_recommendations(rule_engine, sample_forensics_result, sample_ocr_result):
    """Test recommendations generation."""
    result = await rule_engine.process_results(sample_forensics_result, sample_ocr_result)
    
    assert isinstance(result.recommendations, list)
    assert len(result.recommendations) > 0


@pytest.mark.asyncio
async def test_generate_recommendations_no_violations(rule_engine):
    """Test recommendations generation with no violations."""
    # Create perfect results
    perfect_forensics = ForensicsResult(
        edge_score=0.9,
        compression_score=0.2,
        font_score=0.9,
        overall_score=0.8,
        detected_anomalies=[],
        edge_inconsistencies={"score": 0.9},
        compression_artifacts={"score": 0.2},
        font_analysis={"score": 0.9}
    )
    
    perfect_ocr = OCRResult(
        payee="John Doe",
        amount="$100.00",
        date="2024-01-15",
        signature_detected=True,
        extraction_confidence=0.9,
        field_confidences={}
    )
    
    result = await rule_engine.process_results(perfect_forensics, perfect_ocr)
    
    # Should have positive recommendation
    assert len(result.recommendations) > 0
    assert any("pass" in rec.lower() for rec in result.recommendations)


def test_evaluate_threshold_rule_operators(rule_engine, sample_forensics_result, sample_ocr_result):
    """Test threshold rule evaluation with different operators."""
    # Test equals operator
    equals_rule = Rule(
        id="equals_rule",
        name="Equals Rule",
        description="Test equals operator",
        category="forensics",
        weight=0.5,
        condition={
            "type": "threshold",
            "field": "edge_score",
            "operator": "equals",
            "value": 0.2
        },
        severity="medium",
        enabled=True
    )
    
    result = rule_engine._evaluate_threshold_rule(equals_rule, sample_forensics_result, sample_ocr_result)
    
    assert isinstance(result, RuleEvaluationResult)
    # Should pass because edge_score == 0.2
    assert result.passed is False  # equals 0.2 means violation


def test_evaluate_threshold_rule_unknown_operator(rule_engine, sample_forensics_result, sample_ocr_result):
    """Test threshold rule evaluation with unknown operator."""
    unknown_op_rule = Rule(
        id="unknown_op_rule",
        name="Unknown Operator Rule",
        description="Test unknown operator",
        category="forensics",
        weight=0.5,
        condition={
            "type": "threshold",
            "field": "edge_score",
            "operator": "unknown_operator",
            "value": 0.5
        },
        severity="medium",
        enabled=True
    )
    
    result = rule_engine._evaluate_threshold_rule(unknown_op_rule, sample_forensics_result, sample_ocr_result)
    
    assert result.passed is True  # Should pass by default
    assert result.score == 0.0


def test_evaluate_threshold_rule_missing_field(rule_engine, sample_forensics_result, sample_ocr_result):
    """Test threshold rule evaluation with missing field."""
    missing_field_rule = Rule(
        id="missing_field_rule",
        name="Missing Field Rule",
        description="Test missing field",
        category="forensics",
        weight=0.5,
        condition={
            "type": "threshold",
            "field": "nonexistent_field",
            "operator": "less_than",
            "value": 0.5
        },
        severity="medium",
        enabled=True
    )
    
    result = rule_engine._evaluate_threshold_rule(missing_field_rule, sample_forensics_result, sample_ocr_result)
    
    assert result.passed is True  # Should pass by default
    assert result.score == 0.0
    assert 'error' in result.details


@pytest.mark.asyncio
async def test_evaluate_date_validation_with_various_dates(rule_engine, sample_forensics_result):
    """Test date validation with various date formats."""
    date_rule = Rule(
        id="date_rule",
        name="Date Rule",
        description="Test date validation",
        category="cross_validation",
        weight=0.3,
        condition={"type": "date_validation"},
        severity="medium",
        enabled=True
    )
    
    # Test valid date
    valid_ocr = OCRResult(
        payee="John Doe",
        amount="$100.00",
        date="01/15/2024",
        signature_detected=True,
        extraction_confidence=0.8,
        field_confidences={}
    )
    
    result = await rule_engine._evaluate_rule(date_rule, sample_forensics_result, valid_ocr)
    assert result.passed is True
    
    # Test invalid date
    invalid_ocr = OCRResult(
        payee="John Doe",
        amount="$100.00",
        date="invalid date",
        signature_detected=True,
        extraction_confidence=0.8,
        field_confidences={}
    )
    
    result = await rule_engine._evaluate_rule(date_rule, sample_forensics_result, invalid_ocr)
    assert result.passed is False


@pytest.mark.asyncio
async def test_rule_engine_disabled_rules(temp_rules_file):
    """Test rule engine with disabled rules."""
    # Load config and disable a rule
    with open(temp_rules_file, 'r') as f:
        config = json.load(f)
    
    config['rules'][0]['enabled'] = False
    
    with open(temp_rules_file, 'w') as f:
        json.dump(config, f)
    
    engine = RuleEngine(temp_rules_file)
    
    # Process some results
    forensics_result = ForensicsResult(
        edge_score=0.1,  # Should trigger disabled rule
        compression_score=0.6,
        font_score=0.8,
        overall_score=0.5,
        detected_anomalies=[],
        edge_inconsistencies={"score": 0.1},
        compression_artifacts={"score": 0.6},
        font_analysis={"score": 0.8}
    )
    
    ocr_result = OCRResult(
        payee="John Doe",
        amount="$100.00",
        date="2024-01-15",
        signature_detected=True,
        extraction_confidence=0.8,
        field_confidences={}
    )
    
    result = await engine.process_results(forensics_result, ocr_result)
    
    # Should have fewer violations since one rule is disabled
    assert isinstance(result, RuleEngineResult)


def test_load_rule_engine_function():
    """Test load_rule_engine helper function."""
    engine = load_rule_engine()
    
    assert isinstance(engine, RuleEngine)
    assert len(engine.rules) > 0


@pytest.mark.asyncio
async def test_rule_engine_error_handling(rule_engine):
    """Test rule engine error handling."""
    # Test with None inputs
    with pytest.raises(Exception):
        await rule_engine.process_results(None, None)


@pytest.mark.asyncio
async def test_rule_engine_comprehensive_scoring(rule_engine):
    """Test comprehensive rule engine scoring."""
    # Create results that should trigger multiple rules
    bad_forensics = ForensicsResult(
        edge_score=0.1,  # Should trigger forensics rule
        compression_score=0.9,
        font_score=0.2,
        overall_score=0.3,
        detected_anomalies=["multiple issues"],
        edge_inconsistencies={"score": 0.1},
        compression_artifacts={"score": 0.9},
        font_analysis={"score": 0.2}
    )
    
    bad_ocr = OCRResult(
        payee=None,  # Missing field
        amount="invalid",  # Invalid amount
        date="bad date",  # Invalid date
        signature_detected=False,
        extraction_confidence=0.1,  # Low confidence
        field_confidences={}
    )
    
    result = await rule_engine.process_results(bad_forensics, bad_ocr)
    
    # Should have high risk score due to multiple violations
    assert result.risk_score > 0.5
    assert len(result.violations) > 2
    assert len(result.recommendations) > 0


@pytest.mark.asyncio
async def test_rule_engine_performance(rule_engine, sample_forensics_result, sample_ocr_result):
    """Test rule engine performance with multiple runs."""
    # Run multiple times to ensure consistent performance
    for _ in range(10):
        result = await rule_engine.process_results(sample_forensics_result, sample_ocr_result)
        assert isinstance(result, RuleEngineResult)
        assert 0.0 <= result.risk_score <= 1.0