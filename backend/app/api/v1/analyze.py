from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid
import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional, Any
from dataclasses import dataclass
import numpy as np

from ...database import get_db
from ...models.user import User
from ...models.file import FileRecord
from ...models.analysis import AnalysisResult
from ...models.task_status import TaskStatus, TaskStatusEnum
from ...schemas.analysis import (
    AnalysisRequest, 
    AnalysisResponse, 
    AnalysisResultResponse,
    AnalysisListResponse,
    ForensicsResult,
    OCRResult,
    RuleEngineResult,
    AsyncAnalysisRequest,
    AsyncAnalysisResponse
)
from ...core.forensics import ForensicsEngine
from ...core.ocr import OCREngine, create_ocr_engine
from ...core.rule_engine import load_rule_engine
from ...core.scoring import RiskScoreCalculator, RiskScoreData
from ...core.s3 import s3_service
from ...utils.file_utils import (
    validate_file_for_analysis,
    prepare_file_for_analysis,
    FileValidationError,
    FileProcessingError
)
from ...utils.image_utils import cleanup_temp_files
from ..deps import get_current_user

router = APIRouter(tags=["analysis"])
logger = logging.getLogger(__name__)


@dataclass
class ComprehensiveAnalysisResult:
    """Data class for comprehensive analysis results."""
    forensics_result: Optional[ForensicsResult] = None
    ocr_result: Optional[OCRResult] = None
    rule_result: Optional[RuleEngineResult] = None
    risk_score_data: Optional[RiskScoreData] = None


# Initialize engines
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


@router.post("/", response_model=AnalysisResponse)
async def analyze_check(
    request: AnalysisRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    background_tasks: BackgroundTasks = BackgroundTasks(),
):
    """
    Analyze a check image for fraud detection.
    
    This endpoint performs comprehensive analysis including:
    - Image forensics (edge detection, compression artifacts, font consistency)
    - OCR field extraction using Gemini API
    - Rule-based fraud detection with risk scoring
    """
    try:
        # Validate file ownership and existence
        file_record = await _get_user_file(request.file_id, current_user.id, db)
        
        # Check if analysis already exists
        existing_analysis = await _get_existing_analysis(request.file_id, db)
        if existing_analysis:
            logger.info(f"Returning existing analysis for file {request.file_id}")
            return await _format_analysis_response(existing_analysis)
        
        # Download file from S3 for analysis
        temp_file_path = await _download_file_for_analysis(file_record.s3_key)
        
        try:
            # Validate and preprocess file (handles both images and PDFs)
            prepared_file_path = await _validate_and_preprocess_file(temp_file_path, request.page_number or 1)
            
            # Run analysis components with timeout
            try:
                analysis_result = await asyncio.wait_for(
                    _run_comprehensive_analysis(prepared_file_path, request.analysis_types),
                    timeout=120.0  # 2 minutes timeout
                )
            except asyncio.TimeoutError:
                logger.error(f"Analysis timeout for file {request.file_id} after 120 seconds")
                raise HTTPException(
                    status_code=408,
                    detail="Analysis timeout - file may be too complex or large for processing"
                )
            
            # Store analysis results in database
            analysis_record = await _store_analysis_results(
                request.file_id,
                analysis_result,
                db
            )
            
            # Format response
            response = await _format_analysis_response(analysis_record)
            
            # Clean up temporary files in background
            files_to_cleanup = [temp_file_path]
            if prepared_file_path != temp_file_path:
                files_to_cleanup.append(prepared_file_path)
            background_tasks.add_task(cleanup_temp_files, files_to_cleanup)
            
            return response
            
        except Exception:
            # Clean up temporary files on error
            files_to_cleanup = [temp_file_path]
            if 'prepared_file_path' in locals() and prepared_file_path != temp_file_path:
                files_to_cleanup.append(prepared_file_path)
            cleanup_temp_files(files_to_cleanup)
            raise
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Analysis failed for file {request.file_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Analysis failed: {str(e)}"
        )


@router.post("/async", response_model=AsyncAnalysisResponse)
async def analyze_check_async_endpoint(
    request: AsyncAnalysisRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Start asynchronous check analysis.
    
    This endpoint immediately returns a task ID and processes the analysis in the background.
    Use the returned status_url to poll for completion status.
    """
    try:
        # Validate file ownership and existence (reuse existing validation)
        file_record = await _get_user_file(request.file_id, current_user.id, db)
        
        # Check if analysis already exists - return immediately if found
        existing_analysis = await _get_existing_analysis(request.file_id, db)
        if existing_analysis:
            logger.info(f"Returning existing analysis for file {request.file_id}")
            return AsyncAnalysisResponse(
                task_id="completed",
                status="completed",
                estimated_duration=0,
                status_url=f"/api/v1/tasks/completed",
                result_url=f"/api/v1/analyze/{existing_analysis.id}"
            )
        
        # Import Celery task
        from ...tasks.analysis_tasks import analyze_check_async
        
        # Dispatch to background task
        task = analyze_check_async.delay(
            file_id=request.file_id,
            analysis_types=request.analysis_types,
            page_number=request.page_number or 1
        )
        
        # Create task status record
        task_status = TaskStatus(
            task_id=task.id,
            file_id=request.file_id,
            user_id=current_user.id,
            status=TaskStatusEnum.PENDING,
            progress=0.0,
            estimated_duration=180,
            retry_count=0
        )
        db.add(task_status)
        await db.commit()
        
        logger.info(f"Started async analysis task {task.id} for file {request.file_id}")
        
        return AsyncAnalysisResponse(
            task_id=task.id,
            status="accepted",
            estimated_duration=180,
            status_url=f"/api/v1/tasks/{task.id}",
            result_url=None  # Will be available once task completes
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start async analysis for file {request.file_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start analysis: {str(e)}"
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


async def _download_file_for_analysis(s3_key: str) -> str:
    """Download file from S3 for analysis."""
    try:
        # Generate presigned URL for download
        download_url = await s3_service.generate_presigned_url(s3_key)
        
        if not download_url:
            raise HTTPException(
                status_code=500,
                detail="Failed to generate download URL"
            )
        
        # Download file to temporary location
        import aiohttp
        import aiofiles
        import tempfile
        from pathlib import Path
        
        # Extract file extension from S3 key to preserve file type
        s3_path = Path(s3_key)
        file_extension = s3_path.suffix or '.tmp'
        
        # Create temporary file with correct extension
        temp_file = tempfile.NamedTemporaryFile(suffix=file_extension, delete=False)
        temp_path = temp_file.name
        temp_file.close()  # Close the file handle but don't delete the file
        
        async with aiohttp.ClientSession() as session:
            async with session.get(download_url) as response:
                if response.status != 200:
                    raise HTTPException(
                        status_code=500,
                        detail="Failed to download file from S3"
                    )
                
                # Save to temporary file
                async with aiofiles.open(temp_path, 'wb') as f:
                    async for chunk in response.content.iter_chunked(8192):
                        await f.write(chunk)
                
                return temp_path
                    
    except Exception as e:
        logger.error(f"Failed to download file {s3_key}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to download file: {str(e)}"
        )


async def _validate_and_preprocess_file(file_path: str, page_number: int = 1) -> str:
    """Validate and preprocess file for analysis."""
    try:
        # Validate file (works for both images and PDFs)
        validation_result = validate_file_for_analysis(file_path)
        
        if not validation_result.get('valid', False):
            raise HTTPException(
                status_code=400,
                detail="Invalid file for analysis"
            )
        
        # Prepare file for analysis (converts PDF to image if needed)
        prepared_path = prepare_file_for_analysis(file_path, page_number=page_number)
        
        return prepared_path
        
    except (FileValidationError, FileProcessingError) as e:
        logger.error(f"File preprocessing failed: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail=f"File preprocessing failed: {str(e)}"
        )
    except Exception as e:
        logger.error(f"File preprocessing failed: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail=f"File preprocessing failed: {str(e)}"
        )


async def _run_comprehensive_analysis(file_path: str, analysis_types: list) -> ComprehensiveAnalysisResult:
    """Run comprehensive analysis on the image."""
    try:
        forensics_result = None
        ocr_result = None
        rule_result = None
        
        # Run analysis components in parallel
        tasks = []
        
        if "forensics" in analysis_types:
            tasks.append(("forensics", forensics_engine.analyze_image(file_path)))
        
        if "ocr" in analysis_types:
            ocr_engine = await get_ocr_engine()
            tasks.append(("ocr", ocr_engine.extract_fields(file_path)))
        
        # Execute tasks
        if tasks:
            task_results = await asyncio.gather(*[task[1] for task in tasks])
            
            for i, (task_name, _) in enumerate(tasks):
                if task_name == "forensics":
                    forensics_result = task_results[i]  # type: ignore
                elif task_name == "ocr":
                    ocr_result = task_results[i]  # type: ignore
        
        # Run rule engine if we have results
        if "rules" in analysis_types and forensics_result and ocr_result:
            rule_result = await rule_engine.process_results(
                forensics_result,
                ocr_result
            )
        
        # Calculate enhanced risk score if we have all components
        risk_score_data = None
        if forensics_result and ocr_result and rule_result:
            try:
                risk_score_data = risk_calculator.calculate_risk_score(
                    forensics_result,
                    ocr_result,
                    rule_result
                )
                logger.info(f"Risk score calculated: {risk_score_data.overall_score} ({risk_score_data.risk_level.value})")
            except Exception as e:
                logger.error(f"Risk score calculation failed: {str(e)}")
                # Continue without enhanced scoring if it fails
        
        return ComprehensiveAnalysisResult(
            forensics_result=forensics_result,
            ocr_result=ocr_result,
            rule_result=rule_result,
            risk_score_data=risk_score_data
        )
        
    except Exception as e:
        logger.error(f"Comprehensive analysis failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Analysis failed: {str(e)}"
        )


async def _store_analysis_results(file_id: str, analysis_result: ComprehensiveAnalysisResult, 
                                 db: AsyncSession) -> AnalysisResult:
    """Store analysis results in database."""
    try:
        # Extract results
        forensics_result = analysis_result.forensics_result
        ocr_result = analysis_result.ocr_result
        rule_result = analysis_result.rule_result
        risk_score_data = analysis_result.risk_score_data
        
        # Create analysis record with numpy type conversion
        analysis_record = AnalysisResult(
            id=str(uuid.uuid4()),
            file_id=file_id,
            analysis_timestamp=datetime.now(timezone.utc),
            
            # Forensics results (convert numpy types)
            forensics_score=_convert_numpy_types(forensics_result.overall_score if forensics_result else 0.0),
            edge_inconsistencies=_convert_numpy_types(forensics_result.edge_inconsistencies if forensics_result else {}),
            compression_artifacts=_convert_numpy_types(forensics_result.compression_artifacts if forensics_result else {}),
            font_analysis=_convert_numpy_types(forensics_result.font_analysis if forensics_result else {}),
            
            # OCR results (convert numpy types)
            ocr_confidence=_convert_numpy_types(ocr_result.extraction_confidence if ocr_result else 0.0),
            extracted_fields=_convert_numpy_types({
                "payee": ocr_result.payee if ocr_result else None,
                "amount": ocr_result.amount if ocr_result else None,
                "date": ocr_result.date if ocr_result else None,
                "account_number": ocr_result.account_number if ocr_result else None,
                "routing_number": ocr_result.routing_number if ocr_result else None,
                "check_number": ocr_result.check_number if ocr_result else None,
                "memo": ocr_result.memo if ocr_result else None,
                "signature_detected": ocr_result.signature_detected if ocr_result else False,
                "field_confidences": ocr_result.field_confidences if ocr_result else {}
            }),
            
            # Rule engine results (convert numpy types) - use enhanced risk score if available
            overall_risk_score=_convert_numpy_types(
                float(risk_score_data.overall_score) if risk_score_data else 
                (rule_result.risk_score if rule_result else 0.0)
            ),
            rule_violations=_convert_numpy_types({
                "violations": rule_result.violations if rule_result else [],
                "passed_rules": rule_result.passed_rules if rule_result else [],
                "rule_scores": rule_result.rule_scores if rule_result else {},
                # Add enhanced scoring data if available
                "enhanced_scoring": {
                    "category_scores": risk_score_data.category_scores,
                    "risk_factors": risk_score_data.risk_factors,
                    "risk_level": risk_score_data.risk_level.value,
                    "detailed_breakdown": risk_score_data.detailed_breakdown,
                    "recommendations": risk_score_data.recommendations,
                    "timestamp": risk_score_data.timestamp.isoformat()
                } if risk_score_data else None
            }),
            confidence_factors=_convert_numpy_types(
                {"overall": risk_score_data.confidence_level} if risk_score_data else 
                (rule_result.confidence_factors if rule_result else {})
            )
        )
        
        db.add(analysis_record)
        await db.commit()
        await db.refresh(analysis_record)
        
        return analysis_record
        
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to store analysis results: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to store analysis results: {str(e)}"
        )


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
