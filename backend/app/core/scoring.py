"""
Risk scoring logic for CheckGuard AI fraud detection.

This module provides comprehensive risk scoring functionality that evaluates
forensic analysis results, OCR data, and rule engine violations to produce
a 0-100 risk score with detailed breakdown and recommendations.
"""

import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

from ..schemas.analysis import ForensicsResult, OCRResult, RuleEngineResult

logger = logging.getLogger(__name__)


class RiskLevel(Enum):
    """Risk level enumeration."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass
class RiskScoreData:
    """Data structure for comprehensive risk scoring results."""
    overall_score: int  # 0-100 final risk score
    category_scores: Dict[str, int]  # forensics, ocr, rules category scores
    risk_factors: List[str]  # List of triggered risk factors
    confidence_level: float  # 0.0-1.0 confidence in assessment
    recommendation: str  # LOW, MEDIUM, HIGH, CRITICAL
    risk_level: RiskLevel  # Enumerated risk level
    detailed_breakdown: Dict[str, Any]  # Detailed analysis breakdown
    recommendations: List[str]  # Specific recommendations
    timestamp: datetime  # When score was calculated


class RiskScoreCalculator:
    """
    Main risk scoring engine that evaluates all analysis components.
    
    Features:
    - Weighted scoring across forensics, OCR, and rule categories
    - Confidence level calculation
    - Risk level determination
    - Detailed recommendations
    - Configurable thresholds
    """
    
    def __init__(self, category_weights: Optional[Dict[str, float]] = None):
        """
        Initialize risk score calculator.
        
        Args:
            category_weights: Custom category weights (forensics, ocr, rules)
        """
        # Default category weights based on PRP requirements
        self.category_weights = category_weights or {
            'forensics': 0.4,  # 40% weight for forensics analysis
            'ocr': 0.3,        # 30% weight for OCR analysis
            'rules': 0.3       # 30% weight for rule violations
        }
        
        # Risk level thresholds (0-100 scale)
        self.risk_thresholds = {
            RiskLevel.LOW: 30,
            RiskLevel.MEDIUM: 60,
            RiskLevel.HIGH: 80,
            RiskLevel.CRITICAL: 90
        }
        
        # Confidence calculation parameters
        self.confidence_factors = {
            'forensics_confidence': 0.4,
            'ocr_confidence': 0.3,
            'rules_confidence': 0.3
        }
    
    def calculate_risk_score(self, forensics_result: ForensicsResult, 
                           ocr_result: OCRResult, 
                           rule_result: RuleEngineResult) -> RiskScoreData:
        """
        Calculate comprehensive risk score from all analysis components.
        
        Args:
            forensics_result: Results from forensic analysis
            ocr_result: Results from OCR extraction
            rule_result: Results from rule engine processing
            
        Returns:
            RiskScoreData with comprehensive risk assessment
        """
        try:
            # Calculate individual category scores
            forensics_score = self._calculate_forensics_score(forensics_result)
            ocr_score = self._calculate_ocr_score(ocr_result)
            rules_score = self._calculate_rules_score(rule_result)
            
            # Calculate overall weighted score
            overall_score = self._calculate_overall_score(
                forensics_score, ocr_score, rules_score
            )
            
            # Extract risk factors
            risk_factors = self._extract_risk_factors(
                forensics_result, ocr_result, rule_result
            )
            
            # Calculate confidence level
            confidence_level = self._calculate_confidence_level(
                forensics_result, ocr_result, rule_result
            )
            
            # Determine risk level and recommendations
            risk_level = self._determine_risk_level(overall_score)
            recommendations = self._generate_recommendations(
                overall_score, risk_level, forensics_result, ocr_result, rule_result
            )
            
            # Create detailed breakdown
            detailed_breakdown = self._create_detailed_breakdown(
                forensics_result, ocr_result, rule_result,
                forensics_score, ocr_score, rules_score
            )
            
            return RiskScoreData(
                overall_score=overall_score,
                category_scores={
                    'forensics': forensics_score,
                    'ocr': ocr_score,
                    'rules': rules_score
                },
                risk_factors=risk_factors,
                confidence_level=confidence_level,
                recommendation=risk_level.value,
                risk_level=risk_level,
                detailed_breakdown=detailed_breakdown,
                recommendations=recommendations,
                timestamp=datetime.utcnow()
            )
            
        except Exception as e:
            logger.error(f"Risk score calculation failed: {str(e)}")
            raise RiskScoringError(f"Failed to calculate risk score: {str(e)}")
    
    def _calculate_forensics_score(self, forensics_result: ForensicsResult) -> int:
        """
        Calculate forensics risk score (0-100).
        
        Lower forensics scores indicate higher risk.
        """
        try:
            # Edge score component (lower is riskier)
            edge_risk = max(0, (1.0 - forensics_result.edge_score) * 100)
            
            # Compression artifacts (higher is riskier)
            compression_risk = forensics_result.compression_score * 100
            
            # Font analysis (lower is riskier)
            font_risk = max(0, (1.0 - forensics_result.font_score) * 100)
            
            # Overall forensics score (lower is riskier)
            overall_risk = max(0, (1.0 - forensics_result.overall_score) * 100)
            
            # Weighted average of forensics components
            forensics_score = int(
                edge_risk * 0.25 +
                compression_risk * 0.25 +
                font_risk * 0.25 +
                overall_risk * 0.25
            )
            
            # Boost score for detected anomalies
            anomaly_boost = len(forensics_result.detected_anomalies) * 5
            forensics_score = min(100, forensics_score + anomaly_boost)
            
            logger.debug(f"Forensics score calculated: {forensics_score}")
            return forensics_score
            
        except Exception as e:
            logger.error(f"Forensics score calculation failed: {str(e)}")
            return 50  # Default moderate risk
    
    def _calculate_ocr_score(self, ocr_result: OCRResult) -> int:
        """
        Calculate OCR risk score (0-100).
        
        Lower confidence and missing fields indicate higher risk.
        """
        try:
            # Base score from extraction confidence (lower confidence = higher risk)
            confidence_risk = max(0, (1.0 - ocr_result.extraction_confidence) * 100)
            
            # Missing critical fields penalty
            critical_fields = ['payee', 'amount', 'date']
            missing_fields = []
            
            for field in critical_fields:
                field_value = getattr(ocr_result, field, None)
                if field_value is None or field_value == "":
                    missing_fields.append(field)
            
            missing_fields_penalty = len(missing_fields) * 25  # 25 points per missing field
            
            # Field confidence analysis
            field_confidence_risk = 0
            if ocr_result.field_confidences:
                avg_field_confidence = sum(ocr_result.field_confidences.values()) / len(ocr_result.field_confidences)
                field_confidence_risk = int(max(0, (1.0 - avg_field_confidence) * 30))
            
            # Signature detection (missing signature increases risk)
            signature_risk = 0 if ocr_result.signature_detected else 20
            
            ocr_score = min(100, int(
                confidence_risk * 0.4 +
                missing_fields_penalty +
                field_confidence_risk +
                signature_risk
            ))
            
            logger.debug(f"OCR score calculated: {ocr_score}")
            return ocr_score
            
        except Exception as e:
            logger.error(f"OCR score calculation failed: {str(e)}")
            return 50  # Default moderate risk
    
    def _calculate_rules_score(self, rule_result: RuleEngineResult) -> int:
        """
        Calculate rules risk score (0-100).
        
        More violations and higher rule scores indicate higher risk.
        """
        try:
            # Base score from rule engine risk score
            base_score = int(rule_result.risk_score * 100)
            
            # Violations penalty (each violation adds risk)
            violations_penalty = len(rule_result.violations) * 10
            
            # Rule scores analysis
            rule_scores_risk = 0
            if rule_result.rule_scores:
                high_risk_rules = [score for score in rule_result.rule_scores.values() if score > 0.7]
                rule_scores_risk = len(high_risk_rules) * 5
            
            # Confidence factor adjustment
            confidence_adjustment = 0
            if rule_result.confidence_factors:
                overall_confidence = rule_result.confidence_factors.get('overall', 0.5)
                confidence_adjustment = int(max(0, (1.0 - overall_confidence) * 20))
            
            rules_score = min(100, int(
                base_score +
                violations_penalty +
                rule_scores_risk +
                confidence_adjustment
            ))
            
            logger.debug(f"Rules score calculated: {rules_score}")
            return rules_score
            
        except Exception as e:
            logger.error(f"Rules score calculation failed: {str(e)}")
            return 50  # Default moderate risk
    
    def _calculate_overall_score(self, forensics_score: int, 
                               ocr_score: int, rules_score: int) -> int:
        """Calculate weighted overall risk score."""
        overall_score = int(
            forensics_score * self.category_weights['forensics'] +
            ocr_score * self.category_weights['ocr'] +
            rules_score * self.category_weights['rules']
        )
        
        return min(100, max(0, overall_score))
    
    def _extract_risk_factors(self, forensics_result: ForensicsResult,
                            ocr_result: OCRResult, 
                            rule_result: RuleEngineResult) -> List[str]:
        """Extract specific risk factors from analysis results."""
        risk_factors = []
        
        # Forensics risk factors
        if forensics_result.edge_score < 0.3:
            risk_factors.append("Poor edge quality detected")
        if forensics_result.compression_score > 0.7:
            risk_factors.append("High compression artifacts")
        if forensics_result.font_score < 0.4:
            risk_factors.append("Font inconsistencies detected")
        if forensics_result.detected_anomalies:
            risk_factors.extend(forensics_result.detected_anomalies)
        
        # OCR risk factors
        if ocr_result.extraction_confidence < 0.5:
            risk_factors.append("Low OCR extraction confidence")
        if not ocr_result.payee:
            risk_factors.append("Missing payee information")
        if not ocr_result.amount:
            risk_factors.append("Missing amount information")
        if not ocr_result.signature_detected:
            risk_factors.append("No signature detected")
        
        # Rule violations
        risk_factors.extend(rule_result.violations)
        
        return risk_factors
    
    def _calculate_confidence_level(self, forensics_result: ForensicsResult,
                                  ocr_result: OCRResult, 
                                  rule_result: RuleEngineResult) -> float:
        """Calculate overall confidence level in the assessment."""
        
        # Forensics confidence (higher scores = higher confidence)
        forensics_confidence = (
            forensics_result.edge_score * 0.25 +
            (1.0 - forensics_result.compression_score) * 0.25 +
            forensics_result.font_score * 0.25 +
            forensics_result.overall_score * 0.25
        )
        
        # OCR confidence
        ocr_confidence = ocr_result.extraction_confidence
        
        # Rules confidence
        rules_confidence = rule_result.confidence_factors.get('overall', 0.5)
        
        # Overall weighted confidence
        overall_confidence = (
            forensics_confidence * self.confidence_factors['forensics_confidence'] +
            ocr_confidence * self.confidence_factors['ocr_confidence'] +
            rules_confidence * self.confidence_factors['rules_confidence']
        )
        
        return min(1.0, max(0.0, overall_confidence))
    
    def _determine_risk_level(self, overall_score: int) -> RiskLevel:
        """Determine risk level based on overall score."""
        if overall_score >= self.risk_thresholds[RiskLevel.CRITICAL]:
            return RiskLevel.CRITICAL
        elif overall_score >= self.risk_thresholds[RiskLevel.HIGH]:
            return RiskLevel.HIGH
        elif overall_score >= self.risk_thresholds[RiskLevel.MEDIUM]:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW
    
    def _generate_recommendations(self, overall_score: int, risk_level: RiskLevel,
                                forensics_result: ForensicsResult,
                                ocr_result: OCRResult, 
                                rule_result: RuleEngineResult) -> List[str]:
        """Generate specific recommendations based on risk assessment."""
        recommendations = []
        
        # Base recommendations by risk level
        if risk_level == RiskLevel.CRITICAL:
            recommendations.extend([
                "CRITICAL: DO NOT PROCESS - Manual review required",
                "Potential fraud detected - Contact security team immediately",
                "Full forensic investigation recommended"
            ])
        elif risk_level == RiskLevel.HIGH:
            recommendations.extend([
                "HIGH RISK: Manual review required before processing",
                "Verify with additional documentation",
                "Consider enhanced authentication procedures"
            ])
        elif risk_level == RiskLevel.MEDIUM:
            recommendations.extend([
                "MEDIUM RISK: Additional verification recommended",
                "Review flagged areas manually",
                "Consider secondary verification"
            ])
        else:
            recommendations.extend([
                "LOW RISK: Standard processing acceptable",
                "Check appears legitimate based on analysis"
            ])
        
        # Specific recommendations based on analysis results
        if forensics_result.edge_score < 0.3:
            recommendations.append("Investigate edge quality anomalies")
        if forensics_result.compression_score > 0.7:
            recommendations.append("Review compression artifacts for tampering")
        if ocr_result.extraction_confidence < 0.5:
            recommendations.append("Manually verify OCR extracted fields")
        if not ocr_result.signature_detected:
            recommendations.append("Verify signature presence and authenticity")
        
        # Rule-specific recommendations
        recommendations.extend(rule_result.recommendations)
        
        return recommendations
    
    def _create_detailed_breakdown(self, forensics_result: ForensicsResult,
                                 ocr_result: OCRResult, rule_result: RuleEngineResult,
                                 forensics_score: int, ocr_score: int, 
                                 rules_score: int) -> Dict[str, Any]:
        """Create detailed breakdown of risk assessment."""
        return {
            'forensics_analysis': {
                'score': forensics_score,
                'edge_score': forensics_result.edge_score,
                'compression_score': forensics_result.compression_score,
                'font_score': forensics_result.font_score,
                'overall_score': forensics_result.overall_score,
                'detected_anomalies': forensics_result.detected_anomalies,
                'weight': self.category_weights['forensics']
            },
            'ocr_analysis': {
                'score': ocr_score,
                'extraction_confidence': ocr_result.extraction_confidence,
                'field_confidences': ocr_result.field_confidences,
                'signature_detected': ocr_result.signature_detected,
                'extracted_fields': {
                    'payee': ocr_result.payee,
                    'amount': ocr_result.amount,
                    'date': ocr_result.date,
                    'account_number': ocr_result.account_number,
                    'routing_number': ocr_result.routing_number
                },
                'weight': self.category_weights['ocr']
            },
            'rules_analysis': {
                'score': rules_score,
                'risk_score': rule_result.risk_score,
                'violations': rule_result.violations,
                'passed_rules': rule_result.passed_rules,
                'rule_scores': rule_result.rule_scores,
                'confidence_factors': rule_result.confidence_factors,
                'weight': self.category_weights['rules']
            },
            'scoring_metadata': {
                'category_weights': self.category_weights,
                'risk_thresholds': {level.value: threshold for level, threshold in self.risk_thresholds.items()},
                'calculation_method': 'weighted_average'
            }
        }


class RiskScoringError(Exception):
    """Custom exception for risk scoring errors."""
    pass


# Helper functions
def calculate_risk_score(forensics_result: ForensicsResult, 
                        ocr_result: OCRResult, 
                        rule_result: RuleEngineResult,
                        category_weights: Optional[Dict[str, float]] = None) -> RiskScoreData:
    """
    Convenience function to calculate risk score.
    
    Args:
        forensics_result: Forensic analysis results
        ocr_result: OCR extraction results
        rule_result: Rule engine results
        category_weights: Optional custom weights
        
    Returns:
        RiskScoreData with comprehensive risk assessment
    """
    calculator = RiskScoreCalculator(category_weights)
    return calculator.calculate_risk_score(forensics_result, ocr_result, rule_result)


def get_risk_level_color(risk_level: RiskLevel) -> str:
    """Get color code for risk level visualization."""
    color_map = {
        RiskLevel.LOW: '#10B981',      # Green
        RiskLevel.MEDIUM: '#F59E0B',   # Yellow
        RiskLevel.HIGH: '#EF4444',     # Red
        RiskLevel.CRITICAL: '#DC2626'  # Dark Red
    }
    return color_map.get(risk_level, '#6B7280')  # Default gray


def get_risk_level_description(risk_level: RiskLevel) -> str:
    """Get human-readable description for risk level."""
    descriptions = {
        RiskLevel.LOW: "Low risk - Standard processing acceptable",
        RiskLevel.MEDIUM: "Medium risk - Additional verification recommended",
        RiskLevel.HIGH: "High risk - Manual review required",
        RiskLevel.CRITICAL: "Critical risk - Do not process, security review required"
    }
    return descriptions.get(risk_level, "Unknown risk level")