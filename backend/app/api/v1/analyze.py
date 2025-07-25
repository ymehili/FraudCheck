from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import logging
from typing import Optional, Any
import numpy as np

from ...database import get_db
from ...models.user import User
from ...models.file import FileRecord
from ...models.analysis import AnalysisResult
from ...models.task_status import TaskStatus, TaskStatusEnum
from ...schemas.analysis import (
    AnalysisResponse, 
    AnalysisResultResponse,
    AnalysisListResponse,
    AsyncAnalysisRequest,
    AsyncAnalysisResponse
)
from ...core.forensics import ForensicsEngine
from ...core.ocr import OCREngine, create_ocr_engine
from ...core.rule_engine import load_rule_engine
from ...core.scoring import RiskScoreCalculator
# Removed unused imports - functions only used by deprecated sync endpoint
from ..deps import get_current_user

router = APIRouter(tags=["analysis"])
logger = logging.getLogger(__name__)


# Initialize engines for async analysis
forensics_engine = ForensicsEngine()
rule_engine = load_rule_engine()
risk_calculator = RiskScoreCalculator()


async def get_ocr_engine() -> OCREngine:
    """Get OCR engine instance."""
    return await create_ocr_engine()


def _convert_numpy_types(obj: Any) -> Any:
    """Convert numpy types to JSON-serializable Python types."""
    if isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {key: _convert_numpy_types(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [_convert_numpy_types(item) for item in obj]
    else:
        return obj


@router.post("/", status_code=410)
async def analyze_check_deprecated():
    """
    Deprecated synchronous analysis endpoint.
    
    This endpoint has been removed to prevent memory exhaustion issues.
    Use the /async endpoint instead for reliable analysis.
    """
    raise HTTPException(
        status_code=410,
        detail={
            "error": "Synchronous analysis endpoint deprecated",
            "message": "Use /async endpoint for reliable analysis with streaming support",
            "migration_guide": {
                "old_endpoint": "POST /api/v1/analyze/",
                "new_endpoint": "POST /api/v1/analyze/async",
                "new_flow": [
                    "1. Submit analysis request to /async endpoint",
                    "2. Receive task_id in response",
                    "3. Poll /api/v1/tasks/{task_id} for progress",
                    "4. Retrieve results when completed"
                ]
            }
        }
    )


@router.post("/async", response_model=AsyncAnalysisResponse)
async def analyze_check_async_endpoint(
    request: AsyncAnalysisRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Start asynchronous check analysis with streaming support.
    
    This endpoint uses streaming file processing and resource monitoring to prevent
    memory exhaustion. Returns a task ID for monitoring progress via WebSocket
    or polling.
    
    Features:
    - Streaming file download and preprocessing
    - Memory usage monitoring with automatic termination
    - Real-time progress updates with resource usage
    - Support for large files up to 50MB
    """
    try:
        # Comprehensive input validation
        if not request.file_id:
            raise HTTPException(
                status_code=400,
                detail="file_id is required"
            )
        
        if not request.analysis_types:
            raise HTTPException(
                status_code=400,
                detail="At least one analysis type must be specified"
            )
        
        # Validate analysis types
        valid_analysis_types = {"forensics", "ocr", "rules"}
        invalid_types = set(request.analysis_types) - valid_analysis_types
        if invalid_types:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid analysis types: {list(invalid_types)}. Valid types: {list(valid_analysis_types)}"
            )
        
        # Validate page number for PDFs
        if request.page_number is not None and request.page_number < 1:
            raise HTTPException(
                status_code=400,
                detail="page_number must be >= 1"
            )
        
        # Validate file ownership and existence with resource checking
        file_record = await _get_user_file(request.file_id, current_user.id, db)
        
        # Check file size limits before processing
        file_size = getattr(file_record, 'file_size', 0) or 0
        max_file_size = 50 * 1024 * 1024  # 50MB limit as per PRP success criteria
        
        if file_size > max_file_size:
            raise HTTPException(
                status_code=413,
                detail={
                    "error": "File too large for streaming analysis",
                    "file_size_mb": file_size / (1024 * 1024),
                    "max_size_mb": max_file_size / (1024 * 1024),
                    "recommendation": "Please upload a smaller file or contact support for large file processing"
                }
            )
        
        # Check system resources before starting analysis
        from ...tasks.resource_monitor import SystemResourceMonitor
        system_health = SystemResourceMonitor.check_system_health()
        
        if system_health["status"] == "critical":
            logger.warning(f"System resources critical, deferring analysis: {system_health}")
            raise HTTPException(
                status_code=503,
                detail={
                    "error": "System resources temporarily unavailable",
                    "message": "Analysis service is under high load. Please try again in a few minutes.",
                    "retry_after": 300  # 5 minutes
                }
            )
        
        # Check if analysis already exists - return immediately if found
        existing_analysis = await _get_existing_analysis(request.file_id, db)
        if existing_analysis:
            logger.info(f"Returning existing analysis for file {request.file_id}")
            return AsyncAnalysisResponse(
                task_id="completed",
                status="completed",
                estimated_duration=0,
                status_url="/api/v1/tasks/completed",
                result_url=f"/api/v1/analyze/{existing_analysis.id}"
            )
        
        # Calculate estimated duration based on file size and analysis types
        base_duration = 60  # Base 1 minute
        size_factor = min(2.0, file_size / (10 * 1024 * 1024))  # Up to 2x for files >10MB
        type_factor = len(request.analysis_types) * 0.5  # 0.5x per analysis type
        estimated_duration = int(base_duration * (1 + size_factor + type_factor))
        
        # Import new streaming Celery task
        from ...tasks.analysis_tasks import analyze_check_streaming
        
        # Dispatch to streaming background task
        task = analyze_check_streaming.delay(
            file_id=request.file_id,
            analysis_types=request.analysis_types,
            page_number=request.page_number or 1
        )
        
        # Create enhanced task status record
        task_status = TaskStatus(
            task_id=task.id,
            file_id=request.file_id,
            user_id=current_user.id,
            status=TaskStatusEnum.PENDING,
            progress=0.0,
            estimated_duration=estimated_duration,
            retry_count=0
        )
        db.add(task_status)
        await db.commit()
        
        logger.info(
            f"Started streaming analysis task {task.id} for file {request.file_id} "
            f"({file_size / (1024 * 1024):.1f}MB, {len(request.analysis_types)} analysis types, "
            f"estimated {estimated_duration}s)"
        )
        
        return AsyncAnalysisResponse(
            task_id=task.id,
            status="accepted",
            estimated_duration=estimated_duration,
            status_url=f"/api/v1/tasks/{task.id}",
            result_url=None  # Will be available once task completes
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start streaming analysis for file {request.file_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start streaming analysis: {str(e)}"
        )


@router.get("/file/{file_id}", response_model=AnalysisResultResponse)
async def get_analysis_by_file(
    file_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get analysis results for a specific file."""
    try:
        # Validate file ownership
        await _get_user_file(file_id, current_user.id, db)
        
        # Get analysis results
        analysis_result = await _get_existing_analysis(file_id, db)
        if not analysis_result:
            raise HTTPException(
                status_code=404,
                detail="Analysis not found for this file"
            )
        
        return AnalysisResultResponse.model_validate(analysis_result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get analysis for file {file_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get analysis: {str(e)}"
        )


@router.get("/{analysis_id}", response_model=AnalysisResponse)
async def get_analysis_by_id(
    analysis_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get analysis results by analysis ID."""
    try:
        # Get analysis results by ID
        result = await db.execute(
            select(AnalysisResult)
            .join(FileRecord)
            .where(AnalysisResult.id == analysis_id)
            .where(FileRecord.user_id == current_user.id)
        )
        analysis_result = result.scalar_one_or_none()
        
        if not analysis_result:
            raise HTTPException(
                status_code=404,
                detail="Analysis not found or access denied"
            )
        
        return await _format_analysis_response(analysis_result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get analysis {analysis_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get analysis: {str(e)}"
        )


@router.get("/", response_model=AnalysisListResponse)
async def list_analyses(
    page: int = 1,
    per_page: int = 10,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all analyses for the current user."""
    try:
        # Calculate offset
        offset = (page - 1) * per_page
        
        # Get analyses with pagination
        result = await db.execute(
            select(AnalysisResult)
            .join(FileRecord)
            .where(FileRecord.user_id == current_user.id)
            .order_by(AnalysisResult.analysis_timestamp.desc())
            .offset(offset)
            .limit(per_page)
        )
        analyses = result.scalars().all()
        
        # Get total count
        count_result = await db.execute(
            select(AnalysisResult)
            .join(FileRecord)
            .where(FileRecord.user_id == current_user.id)
        )
        total = len(count_result.scalars().all())
        
        return AnalysisListResponse(
            analyses=[AnalysisResultResponse.model_validate(analysis) for analysis in analyses],
            total=total,
            page=page,
            per_page=per_page
        )
        
    except Exception as e:
        logger.error(f"Failed to list analyses: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list analyses: {str(e)}"
        )


@router.delete("/{file_id}")
async def delete_analysis(
    file_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete analysis results for a specific file."""
    try:
        # Validate file ownership
        await _get_user_file(file_id, current_user.id, db)
        
        # Get analysis results
        analysis_result = await _get_existing_analysis(file_id, db)
        if not analysis_result:
            raise HTTPException(
                status_code=404,
                detail="Analysis not found for this file"
            )
        
        # Delete analysis
        await db.delete(analysis_result)
        await db.commit()
        
        return {"message": "Analysis deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete analysis for file {file_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete analysis: {str(e)}"
        )


async def _get_user_file(file_id: str, user_id: str, db: AsyncSession) -> FileRecord:
    """Get file record and validate ownership."""
    result = await db.execute(
        select(FileRecord)
        .where(FileRecord.id == file_id)
        .where(FileRecord.user_id == user_id)
    )
    file_record = result.scalar_one_or_none()
    
    if not file_record:
        raise HTTPException(
            status_code=404,
            detail="File not found or access denied"
        )
    
    return file_record


async def _get_existing_analysis(file_id: str, db: AsyncSession) -> Optional[AnalysisResult]:
    """Check if analysis already exists for this file."""
    result = await db.execute(
        select(AnalysisResult)
        .where(AnalysisResult.file_id == file_id)
        .order_by(AnalysisResult.analysis_timestamp.desc())
    )
    return result.scalar_one_or_none()


# Removed helper functions - only used by deprecated sync endpoint
# These functions have been replaced by streaming equivalents




async def _format_analysis_response(analysis_record: AnalysisResult) -> AnalysisResponse:
    """Format analysis record into response."""
    try:
        # Extract stored data
        extracted_fields = analysis_record.extracted_fields or {}
        rule_violations = analysis_record.rule_violations or {}
        
        # Create response components
        from ...schemas.analysis import ForensicsResult, OCRResult, RuleEngineResult
        
        forensics_result = ForensicsResult(
            edge_score=analysis_record.forensics_score or 0.0,
            compression_score=(analysis_record.compression_artifacts or {}).get('score', 0.0),
            font_score=(analysis_record.font_analysis or {}).get('score', 0.0),
            overall_score=analysis_record.forensics_score or 0.0,
            detected_anomalies=(analysis_record.edge_inconsistencies or {}).get('anomalies', []),
            edge_inconsistencies=analysis_record.edge_inconsistencies or {},
            compression_artifacts=analysis_record.compression_artifacts or {},
            font_analysis=analysis_record.font_analysis or {}
        )
        
        ocr_result = OCRResult(
            payee=extracted_fields.get('payee'),
            amount=extracted_fields.get('amount'),
            date=extracted_fields.get('date'),
            account_number=extracted_fields.get('account_number'),
            routing_number=extracted_fields.get('routing_number'),
            check_number=extracted_fields.get('check_number'),
            memo=extracted_fields.get('memo'),
            signature_detected=extracted_fields.get('signature_detected', False),
            extraction_confidence=analysis_record.ocr_confidence or 0.0,
            field_confidences=extracted_fields.get('field_confidences', {})
        )
        
        # Check if enhanced scoring data is available
        enhanced_scoring = rule_violations.get('enhanced_scoring')
        recommendations = rule_violations.get('recommendations', [])
        
        # Use enhanced recommendations if available
        if enhanced_scoring and enhanced_scoring.get('recommendations'):
            recommendations = enhanced_scoring['recommendations']
        
        rule_engine_result = RuleEngineResult(
            risk_score=analysis_record.overall_risk_score or 0.0,
            violations=rule_violations.get('violations', []),
            passed_rules=rule_violations.get('passed_rules', []),
            rule_scores=rule_violations.get('rule_scores', {}),
            confidence_factors=analysis_record.confidence_factors or {},
            recommendations=recommendations
        )
        
        # Calculate overall confidence - use enhanced confidence if available
        if enhanced_scoring:
            # Use the confidence level from enhanced scoring (already calculated by RiskScoreCalculator)
            overall_confidence = analysis_record.confidence_factors.get('overall', 0.0)
        else:
            # Fall back to legacy confidence calculation
            overall_confidence = (
                (analysis_record.ocr_confidence or 0.0) * 0.4 +
                (analysis_record.forensics_score or 0.0) * 0.3 +
                (analysis_record.confidence_factors or {}).get('overall', 0.0) * 0.3
            )
        
        return AnalysisResponse(
            analysis_id=analysis_record.id,
            file_id=analysis_record.file_id,
            timestamp=analysis_record.analysis_timestamp,
            forensics=forensics_result,
            ocr=ocr_result,
            rules=rule_engine_result,
            overall_risk_score=analysis_record.overall_risk_score or 0.0,
            confidence=overall_confidence
        )
        
    except Exception as e:
        logger.error(f"Failed to format analysis response: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to format response: {str(e)}"
        )
