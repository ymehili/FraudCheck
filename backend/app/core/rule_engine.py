import json
import logging
import os
from typing import Dict, List, Any, Optional
from datetime import datetime
import re
from dataclasses import dataclass

from ..schemas.analysis import ForensicsResult, OCRResult, RuleEngineResult

logger = logging.getLogger(__name__)


@dataclass
class Rule:
    """Individual rule definition"""
    id: str
    name: str
    description: str
    category: str
    weight: float
    condition: Dict[str, Any]
    severity: str  # 'low', 'medium', 'high', 'critical'
    enabled: bool = True


@dataclass
class RuleEvaluationResult:
    """Result of evaluating a single rule"""
    rule_id: str
    rule_name: str
    passed: bool
    score: float
    confidence: float
    details: Dict[str, Any]


class RuleEngine:
    """
    JSON-based rule processing system for check fraud detection.
    
    Features:
    - Configurable rules loaded from JSON
    - Weighted scoring system
    - Confidence calculations
    - Multiple rule categories
    - Detailed violation reporting
    """
    
    def __init__(self, rules_config_path: str = "config/detection_rules.json"):
        """
        Initialize rule engine with configuration.
        
        Args:
            rules_config_path: Path to JSON rules configuration file
        """
        self.rules_config_path = rules_config_path
        self.rules: List[Rule] = []
        self.rule_categories = {
            'forensics': 0.4,  # Weight for forensics rules
            'ocr': 0.3,        # Weight for OCR rules
            'cross_validation': 0.3  # Weight for cross-validation rules
        }
        
        # Load rules from configuration
        self._load_rules()
    
    def _load_rules(self):
        """Load rules from JSON configuration file."""
        try:
            if not os.path.exists(self.rules_config_path):
                logger.warning(f"Rules config file not found: {self.rules_config_path}")
                self._create_default_rules()
                return
            
            with open(self.rules_config_path, 'r') as f:
                config = json.load(f)
            
            # Parse rules from configuration
            self.rules = []
            for rule_data in config.get('rules', []):
                rule = Rule(
                    id=rule_data['id'],
                    name=rule_data['name'],
                    description=rule_data['description'],
                    category=rule_data['category'],
                    weight=rule_data['weight'],
                    condition=rule_data['condition'],
                    severity=rule_data['severity'],
                    enabled=rule_data.get('enabled', True)
                )
                self.rules.append(rule)
            
            # Update category weights if specified
            if 'category_weights' in config:
                self.rule_categories.update(config['category_weights'])
            
            logger.info(f"Loaded {len(self.rules)} rules from {self.rules_config_path}")
            
        except Exception as e:
            logger.error(f"Failed to load rules: {str(e)}")
            self._create_default_rules()
    
    def _create_default_rules(self):
        """Create default rules if no configuration file exists."""
        logger.info("Creating default rules configuration")
        
        default_rules = [
            # Forensics rules
            {
                "id": "forensics_edge_quality",
                "name": "Edge Quality Check",
                "description": "Checks for poor edge quality indicating potential tampering",
                "category": "forensics",
                "weight": 0.3,
                "condition": {
                    "type": "threshold",
                    "field": "edge_score",
                    "operator": "less_than",
                    "value": 0.3
                },
                "severity": "high"
            },
            {
                "id": "forensics_compression_artifacts",
                "name": "Compression Artifacts",
                "description": "Detects high compression artifacts suggesting manipulation",
                "category": "forensics",
                "weight": 0.25,
                "condition": {
                    "type": "threshold",
                    "field": "compression_score",
                    "operator": "greater_than",
                    "value": 0.7
                },
                "severity": "medium"
            },
            {
                "id": "forensics_font_inconsistency",
                "name": "Font Inconsistency",
                "description": "Detects font inconsistencies indicating potential alteration",
                "category": "forensics",
                "weight": 0.2,
                "condition": {
                    "type": "threshold",
                    "field": "font_score",
                    "operator": "less_than",
                    "value": 0.4
                },
                "severity": "medium"
            },
            # OCR rules
            {
                "id": "ocr_low_confidence",
                "name": "Low OCR Confidence",
                "description": "Flags low confidence OCR extraction",
                "category": "ocr",
                "weight": 0.2,
                "condition": {
                    "type": "threshold",
                    "field": "extraction_confidence",
                    "operator": "less_than",
                    "value": 0.5
                },
                "severity": "medium"
            },
            {
                "id": "ocr_missing_critical_fields",
                "name": "Missing Critical Fields",
                "description": "Checks for missing payee or amount fields",
                "category": "ocr",
                "weight": 0.3,
                "condition": {
                    "type": "missing_fields",
                    "fields": ["payee", "amount"]
                },
                "severity": "high"
            },
            # Cross-validation rules
            {
                "id": "cross_amount_validation",
                "name": "Amount Cross-Validation",
                "description": "Validates amount format and reasonableness",
                "category": "cross_validation",
                "weight": 0.25,
                "condition": {
                    "type": "amount_validation"
                },
                "severity": "high"
            },
            {
                "id": "cross_date_validation",
                "name": "Date Validation",
                "description": "Validates date format and reasonableness",
                "category": "cross_validation",
                "weight": 0.15,
                "condition": {
                    "type": "date_validation"
                },
                "severity": "medium"
            }
        ]
        
        # Create rules from default configuration
        self.rules = []
        for rule_data in default_rules:
            rule = Rule(
                id=rule_data['id'],
                name=rule_data['name'],
                description=rule_data['description'],
                category=rule_data['category'],
                weight=rule_data['weight'],
                condition=rule_data['condition'],
                severity=rule_data['severity'],
                enabled=True
            )
            self.rules.append(rule)
    
    async def process_results(self, forensics_result: ForensicsResult, 
                            ocr_result: OCRResult) -> RuleEngineResult:
        """
        Process forensics and OCR results through the rule engine.
        
        Args:
            forensics_result: Results from forensics analysis
            ocr_result: Results from OCR extraction
            
        Returns:
            RuleEngineResult with risk assessment and violations
        """
        try:
            # Evaluate all rules
            rule_evaluations = []
            
            for rule in self.rules:
                if not rule.enabled:
                    continue
                
                evaluation = await self._evaluate_rule(rule, forensics_result, ocr_result)
                rule_evaluations.append(evaluation)
            
            # Calculate scores and violations
            risk_score = self._calculate_risk_score(rule_evaluations)
            violations = self._extract_violations(rule_evaluations)
            passed_rules = self._extract_passed_rules(rule_evaluations)
            rule_scores = self._extract_rule_scores(rule_evaluations)
            confidence_factors = self._calculate_confidence_factors(rule_evaluations)
            recommendations = self._generate_recommendations(rule_evaluations)
            
            return RuleEngineResult(
                risk_score=risk_score,
                violations=violations,
                passed_rules=passed_rules,
                rule_scores=rule_scores,
                confidence_factors=confidence_factors,
                recommendations=recommendations,
                overall_confidence=1.0 - risk_score  # Calculate from risk score
            )
            
        except Exception as e:
            logger.error(f"Rule processing failed: {str(e)}")
            raise RuleEngineError(f"Failed to process results: {str(e)}")
    
    async def _evaluate_rule(self, rule: Rule, forensics_result: ForensicsResult, 
                           ocr_result: OCRResult) -> RuleEvaluationResult:
        """Evaluate a single rule against the analysis results."""
        try:
            condition = rule.condition
            condition_type = condition.get('type')
            
            if condition_type == 'threshold':
                return self._evaluate_threshold_rule(rule, forensics_result, ocr_result)
            elif condition_type == 'missing_fields':
                return self._evaluate_missing_fields_rule(rule, ocr_result)
            elif condition_type == 'amount_validation':
                return self._evaluate_amount_validation_rule(rule, ocr_result)
            elif condition_type == 'date_validation':
                return self._evaluate_date_validation_rule(rule, ocr_result)
            else:
                logger.warning(f"Unknown rule condition type: {condition_type}")
                return RuleEvaluationResult(
                    rule_id=rule.id,
                    rule_name=rule.name,
                    passed=True,
                    score=0.0,
                    confidence=0.0,
                    details={'error': f'Unknown condition type: {condition_type}'}
                )
                
        except Exception as e:
            logger.error(f"Rule evaluation failed for {rule.id}: {str(e)}")
            return RuleEvaluationResult(
                rule_id=rule.id,
                rule_name=rule.name,
                passed=True,
                score=0.0,
                confidence=0.0,
                details={'error': str(e)}
            )
    
    def _evaluate_threshold_rule(self, rule: Rule, forensics_result: ForensicsResult, 
                               ocr_result: OCRResult) -> RuleEvaluationResult:
        """Evaluate a threshold-based rule."""
        condition = rule.condition
        field = condition['field']
        operator = condition['operator']
        threshold_value = condition['value']
        
        # Get field value
        field_value = self._get_field_value(field, forensics_result, ocr_result)
        
        if field_value is None:
            return RuleEvaluationResult(
                rule_id=rule.id,
                rule_name=rule.name,
                passed=True,
                score=0.0,
                confidence=0.0,
                details={'error': f'Field {field} not found'}
            )
        
        # Evaluate condition
        if operator == 'less_than':
            violated = field_value < threshold_value
        elif operator == 'greater_than':
            violated = field_value > threshold_value
        elif operator == 'equals':
            violated = field_value == threshold_value
        else:
            logger.warning(f"Unknown operator: {operator}")
            violated = False
        
        # Calculate score and confidence
        if violated:
            score = self._calculate_violation_score(field_value, threshold_value, operator)
            confidence = 0.8  # High confidence for threshold violations
        else:
            score = 0.0
            confidence = 0.7  # Medium confidence for passed rules
        
        return RuleEvaluationResult(
            rule_id=rule.id,
            rule_name=rule.name,
            passed=not violated,
            score=score,
            confidence=confidence,
            details={
                'field': field,
                'value': field_value,
                'threshold': threshold_value,
                'operator': operator
            }
        )
    
    def _evaluate_missing_fields_rule(self, rule: Rule, ocr_result: OCRResult) -> RuleEvaluationResult:
        """Evaluate a missing fields rule."""
        required_fields = rule.condition['fields']
        missing_fields = []
        
        for field in required_fields:
            field_value = getattr(ocr_result, field, None)
            if field_value is None or field_value == "":
                missing_fields.append(field)
        
        violated = len(missing_fields) > 0
        
        if violated:
            score = len(missing_fields) / len(required_fields)
            confidence = 0.9  # High confidence for missing fields
        else:
            score = 0.0
            confidence = 0.8
        
        return RuleEvaluationResult(
            rule_id=rule.id,
            rule_name=rule.name,
            passed=not violated,
            score=score,
            confidence=confidence,
            details={
                'required_fields': required_fields,
                'missing_fields': missing_fields
            }
        )
    
    def _evaluate_amount_validation_rule(self, rule: Rule, ocr_result: OCRResult) -> RuleEvaluationResult:
        """Evaluate amount validation rule."""
        amount = ocr_result.amount
        violations = []
        
        if not amount:
            violations.append('Amount field is empty')
        else:
            # Check for valid amount format
            if not re.search(r'\d', amount):
                violations.append('Amount contains no digits')
            
            # Extract numerical value
            numerical_match = re.search(r'[\d,]+\.?\d*', amount)
            if numerical_match:
                try:
                    numerical_value = float(numerical_match.group().replace(',', ''))
                    
                    # Check for reasonable amount ranges
                    if numerical_value <= 0:
                        violations.append('Amount is zero or negative')
                    elif numerical_value > 100000:  # $100,000 threshold
                        violations.append('Amount is unusually high')
                    elif numerical_value > 10000:  # $10,000 threshold
                        violations.append('Amount is high - requires verification')
                        
                except ValueError:
                    violations.append('Amount format is invalid')
            else:
                violations.append('No valid numerical amount found')
        
        violated = len(violations) > 0
        score = len(violations) * 0.25  # Each violation adds 25% to score
        confidence = 0.7 if amount else 0.9
        
        return RuleEvaluationResult(
            rule_id=rule.id,
            rule_name=rule.name,
            passed=not violated,
            score=min(1.0, score),
            confidence=confidence,
            details={
                'amount': amount,
                'violations': violations
            }
        )
    
    def _evaluate_date_validation_rule(self, rule: Rule, ocr_result: OCRResult) -> RuleEvaluationResult:
        """Evaluate date validation rule."""
        date_str = ocr_result.date
        violations = []
        
        if not date_str:
            violations.append('Date field is empty')
        else:
            # Check for basic date patterns
            date_patterns = [
                r'\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4}',  # MM/DD/YYYY or MM-DD-YYYY
                r'\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2}',     # MM/DD/YY or MM-DD-YY
                r'[A-Za-z]{3,9}\s+\d{1,2},?\s+\d{2,4}', # Month DD, YYYY
            ]
            
            has_valid_format = any(re.search(pattern, date_str) for pattern in date_patterns)
            
            if not has_valid_format:
                violations.append('Date format is not recognized')
            
            # Check for future dates (basic check)
            current_year = datetime.now().year
            year_match = re.search(r'\b(19|20)\d{2}\b', date_str)
            if year_match:
                try:
                    year = int(year_match.group())
                    if year > current_year:
                        violations.append('Date is in the future')
                    elif year < current_year - 10:
                        violations.append('Date is very old')
                except ValueError:
                    pass
        
        violated = len(violations) > 0
        score = len(violations) * 0.3  # Each violation adds 30% to score
        confidence = 0.6 if date_str else 0.8
        
        return RuleEvaluationResult(
            rule_id=rule.id,
            rule_name=rule.name,
            passed=not violated,
            score=min(1.0, score),
            confidence=confidence,
            details={
                'date': date_str,
                'violations': violations
            }
        )
    
    def _get_field_value(self, field: str, forensics_result: ForensicsResult, 
                        ocr_result: OCRResult) -> Optional[float]:
        """Get field value from analysis results."""
        # Try forensics result first
        if hasattr(forensics_result, field):
            return getattr(forensics_result, field)
        
        # Try OCR result
        if hasattr(ocr_result, field):
            return getattr(ocr_result, field)
        
        return None
    
    def _calculate_violation_score(self, field_value: float, threshold: float, 
                                 operator: str) -> float:
        """Calculate violation score based on how far the value is from threshold."""
        if operator == 'less_than':
            # The lower the value, the higher the score
            if field_value < threshold:
                return min(1.0, (threshold - field_value) / threshold)
        elif operator == 'greater_than':
            # The higher the value, the higher the score
            if field_value > threshold:
                return min(1.0, (field_value - threshold) / (1.0 - threshold))
        
        return 0.0
    
    def _calculate_risk_score(self, rule_evaluations: List[RuleEvaluationResult]) -> float:
        """Calculate overall risk score from rule evaluations."""
        if not rule_evaluations:
            return 0.0
        
        # Group evaluations by category
        category_scores: Dict[str, List[float]] = {}
        category_weights: Dict[str, List[float]] = {}
        
        for evaluation in rule_evaluations:
            rule = next(r for r in self.rules if r.id == evaluation.rule_id)
            category = rule.category
            
            if category not in category_scores:
                category_scores[category] = []
                category_weights[category] = []
            
            category_scores[category].append(evaluation.score)
            category_weights[category].append(rule.weight)
        
        # Calculate weighted average for each category
        category_risk_scores = {}
        for category, scores in category_scores.items():
            weights = category_weights[category]
            
            if scores and weights:
                weighted_sum = sum(score * weight for score, weight in zip(scores, weights))
                total_weight = sum(weights)
                category_risk_scores[category] = weighted_sum / total_weight if total_weight > 0 else 0.0
        
        # Calculate overall risk score
        overall_risk = 0.0
        for category, risk_score in category_risk_scores.items():
            category_weight = self.rule_categories.get(category, 0.1)
            overall_risk += risk_score * category_weight
        
        return min(1.0, overall_risk)
    
    def _extract_violations(self, rule_evaluations: List[RuleEvaluationResult]) -> List[str]:
        """Extract violations from rule evaluations."""
        violations = []
        
        for evaluation in rule_evaluations:
            if not evaluation.passed:
                violations.append(f"{evaluation.rule_name}: {evaluation.details}")
        
        return violations
    
    def _extract_passed_rules(self, rule_evaluations: List[RuleEvaluationResult]) -> List[str]:
        """Extract passed rules from evaluations."""
        passed_rules = []
        
        for evaluation in rule_evaluations:
            if evaluation.passed:
                passed_rules.append(evaluation.rule_name)
        
        return passed_rules
    
    def _extract_rule_scores(self, rule_evaluations: List[RuleEvaluationResult]) -> Dict[str, float]:
        """Extract individual rule scores."""
        rule_scores = {}
        
        for evaluation in rule_evaluations:
            rule_scores[evaluation.rule_name] = evaluation.score
        
        return rule_scores
    
    def _calculate_confidence_factors(self, rule_evaluations: List[RuleEvaluationResult]) -> Dict[str, float]:
        """Calculate confidence factors for the analysis."""
        confidence_factors: Dict[str, float] = {}
        
        if not rule_evaluations:
            return confidence_factors
        
        # Overall confidence
        total_confidence = sum(eval.confidence for eval in rule_evaluations)
        confidence_factors['overall'] = total_confidence / len(rule_evaluations)
        
        # Category-specific confidence
        category_confidences: Dict[str, List[float]] = {}
        for evaluation in rule_evaluations:
            rule = next(r for r in self.rules if r.id == evaluation.rule_id)
            category = rule.category
            
            if category not in category_confidences:
                category_confidences[category] = []
            
            category_confidences[category].append(evaluation.confidence)
        
        for category, confidences in category_confidences.items():
            confidence_factors[f'{category}_confidence'] = sum(confidences) / len(confidences)
        
        return confidence_factors
    
    def _generate_recommendations(self, rule_evaluations: List[RuleEvaluationResult]) -> List[str]:
        """Generate recommendations based on rule evaluations."""
        recommendations = []
        
        # Analyze failed rules and generate recommendations
        failed_rules = [eval for eval in rule_evaluations if not eval.passed]
        
        if not failed_rules:
            recommendations.append("Check appears to pass all fraud detection rules")
            return recommendations
        
        # Generate specific recommendations based on failed rules
        for evaluation in failed_rules:
            rule = next(r for r in self.rules if r.id == evaluation.rule_id)
            
            if rule.category == 'forensics':
                recommendations.append("Consider additional forensic analysis")
            elif rule.category == 'ocr':
                recommendations.append("Verify OCR extracted fields manually")
            elif rule.category == 'cross_validation':
                recommendations.append("Cross-validate extracted information")
        
        # Add severity-based recommendations
        critical_violations = [eval for eval in failed_rules 
                             if next(r for r in self.rules if r.id == eval.rule_id).severity == 'critical']
        
        if critical_violations:
            recommendations.append("CRITICAL: Manual review required before processing")
        
        high_violations = [eval for eval in failed_rules 
                          if next(r for r in self.rules if r.id == eval.rule_id).severity == 'high']
        
        if high_violations:
            recommendations.append("HIGH RISK: Additional verification recommended")
        
        return recommendations


class RuleEngineError(Exception):
    """Custom exception for rule engine errors."""
    pass


# Helper functions
def load_rule_engine(config_path: str = "config/detection_rules.json") -> RuleEngine:
    """
    Load and initialize rule engine.
    
    Args:
        config_path: Path to rules configuration file
        
    Returns:
        Configured rule engine instance
    """
    return RuleEngine(config_path)