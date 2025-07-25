from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum


class AnalysisStatusEnum(str, Enum):
    """Enum for forensics analysis status values"""
    SUCCESS = "success"
    PARTIAL_FAILURE = "partial_failure"
    CRITICAL_FAILURE = "critical_failure"


class ForensicsResult(BaseModel):
    """Schema for forensics analysis results"""
    edge_score: float
    compression_score: float
    font_score: float
    overall_score: float
    detected_anomalies: List[str]
    edge_inconsistencies: Dict[str, Any]
    compression_artifacts: Dict[str, Any]
    font_analysis: Dict[str, Any]
    
    # New enhanced forensics fields
    analysis_status: AnalysisStatusEnum = AnalysisStatusEnum.SUCCESS
    error_details: Optional[str] = None
    ela_analysis: Optional[Dict[str, Any]] = None
    copy_move_regions: Optional[List[Dict[str, Any]]] = None
    noise_analysis: Optional[Dict[str, Any]] = None


class OCRResult(BaseModel):
    """Schema for OCR extraction results"""
    payee: Optional[str] = None
    amount: Optional[str] = None
    date: Optional[str] = None
    account_number: Optional[str] = None
    routing_number: Optional[str] = None
    check_number: Optional[str] = None
    memo: Optional[str] = None
    signature_detected: bool = False
    extraction_confidence: float
    raw_text: Optional[str] = None
    field_confidences: Dict[str, float]


class RuleEngineResult(BaseModel):
    """Schema for rule engine processing results"""
    risk_score: float
    violations: List[str]
    passed_rules: List[str]
    rule_scores: Dict[str, float]
    confidence_factors: Dict[str, float]
    recommendations: List[str]
    overall_confidence: Optional[float] = 0.0  # For test compatibility


class AnalysisRequest(BaseModel):
    """Schema for analysis request"""
    file_id: str
    analysis_types: List[str] = ["forensics", "ocr", "rules"]
    page_number: Optional[int] = 1  # For PDF files, which page to analyze
    pdf_options: Optional[Dict[str, Any]] = None  # Additional PDF processing options
    
    
class AnalysisResponse(BaseModel):
    """Schema for complete analysis response"""
    model_config = ConfigDict(from_attributes=True)
    
    analysis_id: str
    file_id: str
    timestamp: datetime
    forensics: ForensicsResult
    ocr: OCRResult
    rules: RuleEngineResult
    overall_risk_score: float
    confidence: float
    

class AnalysisResultBase(BaseModel):
    """Base schema for analysis results"""
    file_id: str
    forensics_score: float
    ocr_confidence: float
    overall_risk_score: float


class AnalysisResultCreate(AnalysisResultBase):
    """Schema for creating analysis results"""
    edge_inconsistencies: Dict[str, Any]
    compression_artifacts: Dict[str, Any]
    font_analysis: Dict[str, Any]
    extracted_fields: Dict[str, Any]
    rule_violations: Dict[str, Any]
    confidence_factors: Dict[str, Any]


class AnalysisResultUpdate(BaseModel):
    """Schema for updating analysis results"""
    forensics_score: Optional[float] = None
    ocr_confidence: Optional[float] = None
    overall_risk_score: Optional[float] = None


class AnalysisResultResponse(AnalysisResultBase):
    """Schema for analysis result response"""
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    analysis_timestamp: datetime
    edge_inconsistencies: Dict[str, Any]
    compression_artifacts: Dict[str, Any]
    font_analysis: Dict[str, Any]
    extracted_fields: Dict[str, Any]
    rule_violations: Dict[str, Any]
    confidence_factors: Dict[str, Any]


class AnalysisListResponse(BaseModel):
    """Schema for analysis list response"""
    analyses: List[AnalysisResultResponse]
    total: int
    page: int
    per_page: int


class AnalysisError(BaseModel):
    """Schema for analysis error responses"""
    error_type: str
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime


# Async Task Processing Schemas

class TaskStatusEnum(str, Enum):
    """Enum for task status values in API responses"""
    PENDING = "pending"
    PROCESSING = "processing" 
    SUCCESS = "success"
    FAILURE = "failure"
    RETRY = "retry"


class AsyncAnalysisRequest(AnalysisRequest):
    """Schema for async analysis request"""
    webhook_url: Optional[str] = None  # Optional progress webhooks


class AsyncAnalysisResponse(BaseModel):
    """Schema for async analysis response"""
    task_id: str
    status: str = "accepted"
    estimated_duration: int = 180  # seconds
    status_url: str
    result_url: Optional[str] = None


class TaskStatusResponse(BaseModel):
    """Schema for task status response"""
    task_id: str
    status: TaskStatusEnum
    progress: float
    file_id: str
    created_at: datetime
    updated_at: datetime
    estimated_duration: int
    error_message: Optional[str] = None
    result_id: Optional[str] = None
    result_url: Optional[str] = None


class TaskResultResponse(BaseModel):
    """Schema for task result response when completed"""
    task_id: str
    status: TaskStatusEnum
    result: Optional[AnalysisResponse] = None
    error_message: Optional[str] = None