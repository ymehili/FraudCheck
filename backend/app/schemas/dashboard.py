"""
Dashboard API schemas for CheckGuard AI.

This module defines Pydantic schemas for dashboard-related API endpoints,
including dashboard statistics, analysis history, filtering, and pagination.
"""

from pydantic import BaseModel, ConfigDict, Field, validator
from datetime import datetime
from typing import List, Optional, Dict, Any, Union
from enum import Enum

from .analysis import AnalysisResultResponse


class RiskLevel(str, Enum):
    """Risk level enumeration for API responses."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class TimeRange(str, Enum):
    """Time range options for filtering."""
    LAST_7_DAYS = "last_7_days"
    LAST_30_DAYS = "last_30_days"
    LAST_90_DAYS = "last_90_days"
    LAST_YEAR = "last_year"
    CUSTOM = "custom"


class SortField(str, Enum):
    """Available sorting fields."""
    UPLOAD_TIMESTAMP = "upload_timestamp"
    ANALYSIS_TIMESTAMP = "analysis_timestamp"
    FILENAME = "filename"
    FILE_SIZE = "file_size"
    RISK_SCORE = "risk_score"
    OVERALL_RISK_SCORE = "overall_risk_score"


class SortDirection(str, Enum):
    """Sort direction options."""
    ASC = "asc"
    DESC = "desc"


class RiskScoreRange(BaseModel):
    """Risk score range for filtering."""
    min: int = Field(ge=0, le=100, description="Minimum risk score")
    max: int = Field(ge=0, le=100, description="Maximum risk score")
    
    @validator('max')
    def validate_max_greater_than_min(cls, v, values):
        if 'min' in values and v < values['min']:
            raise ValueError('max must be greater than or equal to min')
        return v


class DateRange(BaseModel):
    """Date range for filtering."""
    start: datetime = Field(description="Start date (inclusive)")
    end: datetime = Field(description="End date (inclusive)")
    
    @validator('end')
    def validate_end_after_start(cls, v, values):
        if 'start' in values and v < values['start']:
            raise ValueError('end date must be after start date')
        return v


class DashboardFilter(BaseModel):
    """Dashboard filtering options."""
    time_range: Optional[TimeRange] = Field(default=None, description="Predefined time range")
    custom_date_range: Optional[DateRange] = Field(default=None, description="Custom date range")
    risk_score_range: Optional[RiskScoreRange] = Field(default=None, description="Risk score range filter")
    risk_levels: Optional[List[RiskLevel]] = Field(default=None, description="Risk level filter")
    file_types: Optional[List[str]] = Field(default=None, description="File type filter (e.g., ['image/jpeg', 'application/pdf'])")
    has_violations: Optional[bool] = Field(default=None, description="Filter by presence of violations")
    min_confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Minimum confidence threshold")
    
    @validator('custom_date_range')
    def validate_custom_date_range(cls, v, values):
        if values.get('time_range') == TimeRange.CUSTOM and v is None:
            raise ValueError('custom_date_range is required when time_range is CUSTOM')
        return v


class PaginationParams(BaseModel):
    """Pagination parameters."""
    page: int = Field(default=1, ge=1, description="Page number (1-based)")
    per_page: int = Field(default=20, ge=1, le=100, description="Items per page")
    sort_field: Optional[SortField] = Field(default=SortField.ANALYSIS_TIMESTAMP, description="Field to sort by")
    sort_direction: Optional[SortDirection] = Field(default=SortDirection.DESC, description="Sort direction")


class RiskDistribution(BaseModel):
    """Risk distribution statistics."""
    low: int = Field(description="Number of low risk analyses")
    medium: int = Field(description="Number of medium risk analyses")
    high: int = Field(description="Number of high risk analyses")
    critical: int = Field(description="Number of critical risk analyses")
    total: int = Field(description="Total number of analyses")


class TrendDataPoint(BaseModel):
    """Single data point for trend analysis."""
    date: datetime = Field(description="Date of the data point")
    count: int = Field(description="Number of analyses on this date")
    average_risk_score: float = Field(description="Average risk score for this date")
    risk_distribution: RiskDistribution = Field(description="Risk distribution for this date")


class CategoryScore(BaseModel):
    """Category-specific score breakdown."""
    forensics: float = Field(description="Forensics analysis score")
    ocr: float = Field(description="OCR analysis score")
    rules: float = Field(description="Rule engine score")


class RiskScoreDetails(BaseModel):
    """Detailed risk score information."""
    overall_score: int = Field(description="Overall risk score (0-100)")
    risk_level: RiskLevel = Field(description="Risk level classification")
    category_scores: CategoryScore = Field(description="Category-specific scores")
    risk_factors: List[str] = Field(description="List of identified risk factors")
    confidence_level: float = Field(description="Confidence in the assessment")
    recommendations: List[str] = Field(description="Specific recommendations")


class EnhancedAnalysisResult(BaseModel):
    """Enhanced analysis result with risk scoring."""
    model_config = ConfigDict(from_attributes=True)
    
    # Basic analysis information
    id: str = Field(description="Analysis ID")
    file_id: str = Field(description="Associated file ID")
    filename: str = Field(description="Original filename")
    file_size: int = Field(description="File size in bytes")
    mime_type: str = Field(description="File MIME type")
    upload_timestamp: datetime = Field(description="File upload timestamp")
    analysis_timestamp: datetime = Field(description="Analysis completion timestamp")
    
    # Risk scoring information
    risk_score_details: RiskScoreDetails = Field(description="Detailed risk scoring")
    
    # Analysis results
    forensics_score: float = Field(description="Forensics analysis score")
    ocr_confidence: float = Field(description="OCR extraction confidence")
    overall_risk_score: float = Field(description="Overall risk score")
    
    # Rule violations
    violations: List[str] = Field(description="List of rule violations")
    
    # Processing status
    processing_time: Optional[float] = Field(default=None, description="Processing time in seconds")


class DashboardStats(BaseModel):
    """Dashboard overview statistics."""
    total_analyses: int = Field(description="Total number of analyses")
    analyses_today: int = Field(description="Number of analyses today")
    analyses_this_week: int = Field(description="Number of analyses this week")
    analyses_this_month: int = Field(description="Number of analyses this month")
    
    risk_distribution: RiskDistribution = Field(description="Overall risk distribution")
    
    average_risk_score: float = Field(description="Average risk score across all analyses")
    average_confidence: float = Field(description="Average confidence level")
    
    most_common_violations: List[Dict[str, Any]] = Field(description="Most common rule violations")
    
    trend_data: List[TrendDataPoint] = Field(description="Trend data for the last 30 days")
    
    processing_stats: Dict[str, Any] = Field(description="Processing performance statistics")


class AnalysisHistoryResponse(BaseModel):
    """Response for analysis history endpoint."""
    analyses: List[EnhancedAnalysisResult] = Field(description="List of analysis results")
    pagination: Dict[str, Any] = Field(description="Pagination information")
    filters_applied: DashboardFilter = Field(description="Applied filters")
    summary: Dict[str, Any] = Field(description="Summary statistics for filtered results")


class FilterOptionsResponse(BaseModel):
    """Available filter options for the dashboard."""
    available_risk_levels: List[RiskLevel] = Field(description="Available risk levels")
    available_file_types: List[str] = Field(description="Available file types")
    date_range_options: List[TimeRange] = Field(description="Available time range options")
    risk_score_range: Dict[str, int] = Field(description="Min/max risk score range")
    confidence_range: Dict[str, float] = Field(description="Min/max confidence range")


class DashboardExportRequest(BaseModel):
    """Request for exporting dashboard data."""
    filters: Optional[DashboardFilter] = Field(default=None, description="Filters to apply")
    export_format: str = Field(default="csv", description="Export format (csv, json, pdf)")
    include_detailed_breakdown: bool = Field(default=False, description="Include detailed breakdown")
    fields: Optional[List[str]] = Field(default=None, description="Specific fields to include")


class DashboardExportResponse(BaseModel):
    """Response for dashboard export request."""
    export_id: str = Field(description="Export job ID")
    download_url: str = Field(description="Download URL for the exported data")
    file_size: int = Field(description="Size of the exported file")
    record_count: int = Field(description="Number of records exported")
    expires_at: datetime = Field(description="URL expiration timestamp")


class BulkActionRequest(BaseModel):
    """Request for bulk actions on analyses."""
    analysis_ids: List[str] = Field(description="List of analysis IDs")
    action: str = Field(description="Action to perform (delete, re-analyze, export)")
    parameters: Optional[Dict[str, Any]] = Field(default=None, description="Action-specific parameters")


class BulkActionResponse(BaseModel):
    """Response for bulk action request."""
    job_id: str = Field(description="Bulk action job ID")
    total_items: int = Field(description="Total number of items to process")
    status: str = Field(description="Job status")
    created_at: datetime = Field(description="Job creation timestamp")
    estimated_completion: Optional[datetime] = Field(default=None, description="Estimated completion time")


class DashboardSearchRequest(BaseModel):
    """Request for searching analyses."""
    query: str = Field(description="Search query")
    search_fields: List[str] = Field(default=["filename", "violations", "risk_factors"], description="Fields to search in")
    filters: Optional[DashboardFilter] = Field(default=None, description="Additional filters")
    pagination: Optional[PaginationParams] = Field(default=None, description="Pagination parameters")
    highlight_matches: bool = Field(default=True, description="Highlight search matches in results")


class DashboardSearchResponse(BaseModel):
    """Response for dashboard search."""
    results: List[EnhancedAnalysisResult] = Field(description="Search results")
    total_matches: int = Field(description="Total number of matches")
    search_time: float = Field(description="Search execution time in seconds")
    pagination: Dict[str, Any] = Field(description="Pagination information")
    query_info: Dict[str, Any] = Field(description="Query processing information")


class DashboardAlertRule(BaseModel):
    """Dashboard alert rule configuration."""
    id: str = Field(description="Alert rule ID")
    name: str = Field(description="Alert rule name")
    description: str = Field(description="Alert rule description")
    conditions: Dict[str, Any] = Field(description="Alert conditions")
    actions: List[Dict[str, Any]] = Field(description="Actions to take when triggered")
    enabled: bool = Field(description="Whether the rule is enabled")
    created_at: datetime = Field(description="Rule creation timestamp")
    last_triggered: Optional[datetime] = Field(default=None, description="Last trigger timestamp")


class DashboardAlert(BaseModel):
    """Dashboard alert instance."""
    id: str = Field(description="Alert ID")
    rule_id: str = Field(description="Associated rule ID")
    severity: str = Field(description="Alert severity")
    message: str = Field(description="Alert message")
    details: Dict[str, Any] = Field(description="Alert details")
    triggered_at: datetime = Field(description="Alert trigger timestamp")
    acknowledged: bool = Field(description="Whether the alert has been acknowledged")
    acknowledged_by: Optional[str] = Field(default=None, description="User who acknowledged the alert")
    acknowledged_at: Optional[datetime] = Field(default=None, description="Acknowledgment timestamp")


class DashboardInsight(BaseModel):
    """Dashboard insight or recommendation."""
    type: str = Field(description="Insight type")
    title: str = Field(description="Insight title")
    description: str = Field(description="Insight description")
    priority: str = Field(description="Insight priority")
    data: Dict[str, Any] = Field(description="Supporting data")
    actions: List[Dict[str, Any]] = Field(description="Recommended actions")
    created_at: datetime = Field(description="Insight generation timestamp")


class DashboardResponse(BaseModel):
    """Main dashboard response containing all dashboard data."""
    stats: DashboardStats = Field(description="Dashboard statistics")
    recent_analyses: List[EnhancedAnalysisResult] = Field(description="Recent analyses")
    active_alerts: List[DashboardAlert] = Field(description="Active alerts")
    insights: List[DashboardInsight] = Field(description="Dashboard insights")
    system_health: Dict[str, Any] = Field(description="System health information")
    updated_at: datetime = Field(description="Last update timestamp")


# Error schemas
class DashboardError(BaseModel):
    """Dashboard error response."""
    error_type: str = Field(description="Error type")
    message: str = Field(description="Error message")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Error details")
    timestamp: datetime = Field(description="Error timestamp")
    request_id: Optional[str] = Field(default=None, description="Request ID for tracking")


class ValidationError(BaseModel):
    """Validation error details."""
    field: str = Field(description="Field that failed validation")
    message: str = Field(description="Validation error message")
    value: Optional[Any] = Field(default=None, description="Invalid value")


class DashboardValidationError(BaseModel):
    """Dashboard validation error response."""
    message: str = Field(description="Validation error message")
    errors: List[ValidationError] = Field(description="List of validation errors")
    timestamp: datetime = Field(description="Error timestamp")