"""
Risk scoring API endpoints for CheckGuard AI.

This module provides endpoints for calculating and managing risk scores:
- Real-time risk score calculation
- Batch risk scoring
- Risk score history
- Risk score recalculation
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_
from datetime import datetime
from typing import List, Optional, Dict, Any
import logging
import uuid
from pydantic import BaseModel, Field, ConfigDict

from ...database import get_db
from ...models.user import User
from ...models.file import FileRecord
from ...models.analysis import AnalysisResult
from ...schemas.analysis import (
    ForensicsResult,
    OCRResult,
    RuleEngineResult
)
from ...core.scoring import (
    calculate_risk_score,
    RiskScoreData,
    RiskScoreCalculator
)
from ..deps import get_current_user

router = APIRouter(tags=["scoring"])
logger = logging.getLogger(__name__)


class RiskScoreRequest(BaseModel):
    """Request for risk score calculation."""
    analysis_id: str = Field(description="Analysis ID to calculate risk score for")
    recalculate: bool = Field(default=False, description="Force recalculation even if score exists")


class BatchRiskScoreRequest(BaseModel):
    """Request for batch risk score calculation."""
    analysis_ids: List[str] = Field(description="List of analysis IDs to calculate risk scores for")
    recalculate: bool = Field(default=False, description="Force recalculation even if scores exist")


class RiskScoreResponse(BaseModel):
    """Response for risk score calculation."""
    model_config = ConfigDict(from_attributes=True)
    
    analysis_id: str = Field(description="Analysis ID")
    overall_score: int = Field(description="Overall risk score (0-100)")
    risk_level: str = Field(description="Risk level (LOW, MEDIUM, HIGH, CRITICAL)")
    category_scores: Dict[str, int] = Field(description="Category-specific scores")
    risk_factors: List[str] = Field(description="Identified risk factors")
    confidence_level: float = Field(description="Confidence in assessment")
    recommendations: List[str] = Field(description="Specific recommendations")
    calculated_at: datetime = Field(description="When the score was calculated")
    calculation_metadata: Dict[str, Any] = Field(description="Calculation metadata")


class BatchRiskScoreResponse(BaseModel):
    """Response for batch risk score calculation."""
    job_id: str = Field(description="Batch job ID")
    total_analyses: int = Field(description="Total number of analyses to process")
    completed_analyses: int = Field(description="Number of completed analyses")
    failed_analyses: int = Field(description="Number of failed analyses")
    results: List[RiskScoreResponse] = Field(description="Completed risk score results")
    errors: List[Dict[str, str]] = Field(description="Errors encountered")
    status: str = Field(description="Batch job status")
    started_at: datetime = Field(description="Job start time")
    completed_at: Optional[datetime] = Field(default=None, description="Job completion time")


class RiskScoreHistoryResponse(BaseModel):
    """Response for risk score history."""
    analysis_id: str = Field(description="Analysis ID")
    score_history: List[RiskScoreResponse] = Field(description="Historical risk scores")
    current_score: RiskScoreResponse = Field(description="Current risk score")
    score_changes: List[Dict[str, Any]] = Field(description="Score change events")


class RiskScoreConfigRequest(BaseModel):
    """Request for updating risk score configuration."""
    category_weights: Optional[Dict[str, float]] = Field(default=None, description="Category weights")
    risk_thresholds: Optional[Dict[str, int]] = Field(default=None, description="Risk level thresholds")
    confidence_factors: Optional[Dict[str, float]] = Field(default=None, description="Confidence factors")


class RiskScoreConfigResponse(BaseModel):
    """Response for risk score configuration."""
    category_weights: Dict[str, float] = Field(description="Category weights")
    risk_thresholds: Dict[str, int] = Field(description="Risk level thresholds")
    confidence_factors: Dict[str, float] = Field(description="Confidence factors")
    updated_at: datetime = Field(description="Last update timestamp")


@router.post("/calculate", response_model=RiskScoreResponse)
async def calculate_analysis_risk_score(
    request: RiskScoreRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Calculate risk score for a specific analysis.
    
    This endpoint calculates a comprehensive risk score based on:
    - Forensic analysis results
    - OCR extraction results
    - Rule engine violations
    """
    try:
        # Validate analysis ownership
        analysis = await _get_user_analysis(request.analysis_id, current_user.id, db)
        
        # Check if risk score already exists and recalculation is not forced
        existing_score = await _get_existing_risk_score(request.analysis_id, db)
        if existing_score and not request.recalculate:
            return existing_score
        
        # Extract analysis components
        forensics_result = _extract_forensics_result(analysis)
        ocr_result = _extract_ocr_result(analysis)
        rule_result = _extract_rule_result(analysis)
        
        # Calculate risk score
        risk_score_data = calculate_risk_score(
            forensics_result=forensics_result,
            ocr_result=ocr_result,
            rule_result=rule_result
        )
        
        # Store risk score in database
        await _store_risk_score(request.analysis_id, risk_score_data, db)
        
        # Convert to response format
        response = _convert_to_response(request.analysis_id, risk_score_data)
        
        logger.info(f"Risk score calculated for analysis {request.analysis_id}: {risk_score_data.overall_score}")
        return response
        
    except HTTPException:
        # Re-raise HTTP exceptions (like 404) without modification
        raise
    except Exception as e:
        logger.error(f"Risk score calculation failed for analysis {request.analysis_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Risk score calculation failed: {str(e)}"
        )


@router.post("/batch", response_model=BatchRiskScoreResponse)
async def calculate_batch_risk_scores(
    request: BatchRiskScoreRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Calculate risk scores for multiple analyses in batch.
    
    This endpoint processes multiple analyses and calculates risk scores
    for each one. Processing is done in the background.
    """
    try:
        # Generate job ID
        job_id = str(uuid.uuid4())
        
        # Validate all analyses belong to the user
        valid_analyses = []
        for analysis_id in request.analysis_ids:
            try:
                analysis = await _get_user_analysis(analysis_id, current_user.id, db)
                valid_analyses.append(analysis)
            except Exception as e:
                logger.warning(f"Skipping invalid analysis {analysis_id}: {str(e)}")
                continue
        
        if not valid_analyses:
            raise HTTPException(
                status_code=400,
                detail="No valid analyses found for batch processing"
            )
        
        # Start batch processing in background
        background_tasks.add_task(
            _process_batch_risk_scores,
            job_id=job_id,
            analyses=valid_analyses,
            recalculate=request.recalculate,
            user_id=current_user.id
        )
        
        # Return initial response
        return BatchRiskScoreResponse(
            job_id=job_id,
            total_analyses=len(valid_analyses),
            completed_analyses=0,
            failed_analyses=0,
            results=[],
            errors=[],
            status="processing",
            started_at=datetime.utcnow()
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions (like 400, 404) without modification
        raise
    except Exception as e:
        logger.error(f"Batch risk score calculation failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Batch risk score calculation failed: {str(e)}"
        )


@router.get("/batch/{job_id}", response_model=BatchRiskScoreResponse)
async def get_batch_job_status(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get status of a batch risk scoring job.
    
    Returns the current status and results of a batch job.
    """
    try:
        # TODO: Implement actual job status tracking
        # For now, return a placeholder response
        return BatchRiskScoreResponse(
            job_id=job_id,
            total_analyses=0,
            completed_analyses=0,
            failed_analyses=0,
            results=[],
            errors=[],
            status="completed",
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow()
        )
        
    except Exception as e:
        logger.error(f"Failed to get batch job status: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get batch job status: {str(e)}"
        )


@router.get("/history/{analysis_id}", response_model=RiskScoreHistoryResponse)
async def get_risk_score_history(
    analysis_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get risk score history for an analysis.
    
    Returns the historical risk scores and changes for an analysis.
    """
    try:
        # Validate analysis ownership
        await _get_user_analysis(analysis_id, current_user.id, db)
        
        # Get current risk score
        current_score = await _get_existing_risk_score(analysis_id, db)
        if not current_score:
            raise HTTPException(
                status_code=404,
                detail="No risk score found for this analysis"
            )
        
        # TODO: Implement actual risk score history tracking
        # For now, return current score as history
        return RiskScoreHistoryResponse(
            analysis_id=analysis_id,
            score_history=[current_score],
            current_score=current_score,
            score_changes=[]
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions (like 404) without modification
        raise
    except Exception as e:
        logger.error(f"Failed to get risk score history: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get risk score history: {str(e)}"
        )


@router.post("/recalculate/{analysis_id}", response_model=RiskScoreResponse)
async def recalculate_risk_score(
    analysis_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Force recalculation of risk score for an analysis.
    
    This endpoint recalculates the risk score using the latest
    scoring algorithm and configuration.
    """
    try:
        request = RiskScoreRequest(analysis_id=analysis_id, recalculate=True)
        return await calculate_analysis_risk_score(request, current_user, db)
        
    except HTTPException:
        # Re-raise HTTP exceptions (like 404) without modification
        raise
    except Exception as e:
        logger.error(f"Risk score recalculation failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Risk score recalculation failed: {str(e)}"
        )


@router.get("/config", response_model=RiskScoreConfigResponse)
async def get_risk_score_config(
    current_user: User = Depends(get_current_user)
):
    """
    Get current risk scoring configuration.
    
    Returns the current weights, thresholds, and other configuration
    parameters used for risk score calculation.
    """
    try:
        # Get default configuration from RiskScoreCalculator
        calculator = RiskScoreCalculator()
        
        return RiskScoreConfigResponse(
            category_weights=calculator.category_weights,
            risk_thresholds={level.value: threshold for level, threshold in calculator.risk_thresholds.items()},
            confidence_factors=calculator.confidence_factors,
            updated_at=datetime.utcnow()
        )
        
    except Exception as e:
        logger.error(f"Failed to get risk score config: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get risk score configuration: {str(e)}"
        )


@router.post("/config", response_model=RiskScoreConfigResponse)
async def update_risk_score_config(
    request: RiskScoreConfigRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Update risk scoring configuration.
    
    Allows updating weights, thresholds, and other parameters
    used for risk score calculation.
    """
    try:
        # TODO: Implement user-specific configuration storage
        # For now, return the current configuration
        return await get_risk_score_config(current_user)
        
    except Exception as e:
        logger.error(f"Failed to update risk score config: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update risk score configuration: {str(e)}"
        )


# Helper functions
async def _get_user_analysis(analysis_id: str, user_id: str, db: AsyncSession) -> AnalysisResult:
    """Get analysis result ensuring user ownership."""
    try:
        query = (
            select(AnalysisResult)
            .join(FileRecord)
            .where(
                and_(
                    AnalysisResult.id == analysis_id,
                    FileRecord.user_id == user_id
                )
            )
        )
        
        result = await db.execute(query)
        analysis = result.scalar_one_or_none()
        
        if not analysis:
            raise HTTPException(
                status_code=404,
                detail=f"Analysis {analysis_id} not found or access denied"
            )
        
        return analysis
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get user analysis: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve analysis: {str(e)}"
        )


async def _get_existing_risk_score(analysis_id: str, db: AsyncSession) -> Optional[RiskScoreResponse]:
    """Get existing risk score for an analysis."""
    try:
        # TODO: Implement actual risk score storage
        # For now, return None to force calculation
        return None
        
    except Exception as e:
        logger.error(f"Failed to get existing risk score: {str(e)}")
        return None


def _extract_forensics_result(analysis: AnalysisResult) -> ForensicsResult:
    """Extract forensics result from analysis."""
    return ForensicsResult(
        edge_score=analysis.edge_inconsistencies.get('edge_score', 0.5),
        compression_score=analysis.compression_artifacts.get('compression_score', 0.5),
        font_score=analysis.font_analysis.get('font_score', 0.5),
        overall_score=analysis.forensics_score,
        detected_anomalies=analysis.edge_inconsistencies.get('anomalies', []),
        edge_inconsistencies=analysis.edge_inconsistencies,
        compression_artifacts=analysis.compression_artifacts,
        font_analysis=analysis.font_analysis
    )


def _extract_ocr_result(analysis: AnalysisResult) -> OCRResult:
    """Extract OCR result from analysis."""
    return OCRResult(
        payee=analysis.extracted_fields.get('payee'),
        amount=analysis.extracted_fields.get('amount'),
        date=analysis.extracted_fields.get('date'),
        account_number=analysis.extracted_fields.get('account_number'),
        routing_number=analysis.extracted_fields.get('routing_number'),
        check_number=analysis.extracted_fields.get('check_number'),
        memo=analysis.extracted_fields.get('memo'),
        signature_detected=analysis.extracted_fields.get('signature_detected', False),
        extraction_confidence=analysis.ocr_confidence,
        raw_text=analysis.extracted_fields.get('raw_text'),
        field_confidences=analysis.extracted_fields.get('field_confidences', {})
    )


def _extract_rule_result(analysis: AnalysisResult) -> RuleEngineResult:
    """Extract rule engine result from analysis."""
    return RuleEngineResult(
        risk_score=analysis.overall_risk_score / 100.0,  # Convert to 0-1 scale
        violations=analysis.rule_violations.get('violations', []),
        passed_rules=analysis.rule_violations.get('passed_rules', []),
        rule_scores=analysis.rule_violations.get('rule_scores', {}),
        confidence_factors=analysis.confidence_factors,
        recommendations=analysis.rule_violations.get('recommendations', []),
        overall_confidence=analysis.confidence_factors.get('overall', 0.5)
    )


async def _store_risk_score(analysis_id: str, risk_score_data: RiskScoreData, db: AsyncSession):
    """Store risk score in the database."""
    try:
        # TODO: Implement actual risk score storage
        # For now, we'll update the analysis result with the new score
        await db.execute(
            update(AnalysisResult)
            .where(AnalysisResult.id == analysis_id)
            .values(
                overall_risk_score=risk_score_data.overall_score,
                rule_violations={
                    'violations': risk_score_data.risk_factors,
                    'recommendations': risk_score_data.recommendations,
                    'risk_level': risk_score_data.risk_level.value
                }
            )
        )
        await db.commit()
        
    except Exception as e:
        logger.error(f"Failed to store risk score: {str(e)}")
        await db.rollback()
        raise


def _convert_to_response(analysis_id: str, risk_score_data: RiskScoreData) -> RiskScoreResponse:
    """Convert RiskScoreData to API response format."""
    return RiskScoreResponse(
        analysis_id=analysis_id,
        overall_score=risk_score_data.overall_score,
        risk_level=risk_score_data.risk_level.value,
        category_scores=risk_score_data.category_scores,
        risk_factors=risk_score_data.risk_factors,
        confidence_level=risk_score_data.confidence_level,
        recommendations=risk_score_data.recommendations,
        calculated_at=risk_score_data.timestamp,
        calculation_metadata={
            'method': 'weighted_average',
            'weights': {
                'forensics': 0.4,
                'ocr': 0.3,
                'rules': 0.3
            }
        }
    )


async def _process_batch_risk_scores(job_id: str, analyses: List[AnalysisResult], 
                                   recalculate: bool, user_id: str):
    """Process batch risk scores in background."""
    try:
        # TODO: Implement actual batch processing with job tracking
        # This would involve:
        # 1. Processing each analysis
        # 2. Storing results
        # 3. Updating job status
        # 4. Handling errors
        
        logger.info(f"Starting batch risk score processing for job {job_id}")
        
        # Simulate processing for now
        for analysis in analyses:
            try:
                # Extract components and calculate risk score
                forensics_result = _extract_forensics_result(analysis)
                ocr_result = _extract_ocr_result(analysis)
                rule_result = _extract_rule_result(analysis)
                
                risk_score_data = calculate_risk_score(
                    forensics_result=forensics_result,
                    ocr_result=ocr_result,
                    rule_result=rule_result
                )
                
                # Store the result
                # TODO: Store in database
                
                logger.info(f"Processed analysis {analysis.id} with score {risk_score_data.overall_score}")
                
            except Exception as e:
                logger.error(f"Failed to process analysis {analysis.id}: {str(e)}")
                continue
        
        logger.info(f"Completed batch risk score processing for job {job_id}")
        
    except Exception as e:
        logger.error(f"Batch processing failed for job {job_id}: {str(e)}")


from sqlalchemy import and_