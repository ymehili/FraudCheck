from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid
import asyncio
import logging
from datetime import datetime
from typing import Optional

from ...database import get_db
from ...models.user import User
from ...models.file import FileRecord
from ...models.analysis import AnalysisResult
from ...schemas.analysis import (
    AnalysisRequest, 
    AnalysisResponse, 
    AnalysisResultResponse,
    AnalysisListResponse
)
from ...core.forensics import ForensicsEngine
from ...core.ocr import OCREngine, create_ocr_engine
from ...core.rule_engine import load_rule_engine
from ...core.s3 import s3_service
from ...utils.image_utils import (
    validate_image_file, 
    normalize_image_format, 
    enhance_image_quality,
    TempImageFile,
    cleanup_temp_files
)
from ..deps import get_current_user

router = APIRouter()
logger = logging.getLogger(__name__)


# Initialize engines
forensics_engine = ForensicsEngine()
rule_engine = load_rule_engine()


async def get_ocr_engine() -> OCREngine:
    """Get OCR engine instance."""
    return await create_ocr_engine()


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
            # Validate and preprocess image
            await _validate_and_preprocess_image(temp_file_path)
            
            # Run analysis components
            analysis_result = await _run_comprehensive_analysis(
                temp_file_path, 
                request.analysis_types
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
            background_tasks.add_task(cleanup_temp_files, [temp_file_path])
            
            return response
            
        except Exception:
            # Clean up temporary files on error
            cleanup_temp_files([temp_file_path])
            raise
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Analysis failed for file {request.file_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Analysis failed: {str(e)}"
        )


@router.get("/{file_id}", response_model=AnalysisResultResponse)
async def get_analysis(
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
        
        async with aiohttp.ClientSession() as session:
            async with session.get(download_url) as response:
                if response.status != 200:
                    raise HTTPException(
                        status_code=500,
                        detail="Failed to download file from S3"
                    )
                
                # Save to temporary file
                with TempImageFile() as temp_path:
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


async def _validate_and_preprocess_image(file_path: str) -> str:
    """Validate and preprocess image for analysis."""
    try:
        # Validate image file
        validation_result = validate_image_file(file_path)
        
        if not validation_result['valid']:
            raise HTTPException(
                status_code=400,
                detail="Invalid image file"
            )
        
        # Normalize image format
        normalized_path = normalize_image_format(file_path, 'JPEG', quality=95)
        
        # Enhance image quality for better analysis
        enhanced_path = enhance_image_quality(
            normalized_path,
            enhance_contrast=True,
            enhance_sharpness=True,
            enhance_brightness=False
        )
        
        return enhanced_path
        
    except Exception as e:
        logger.error(f"Image preprocessing failed: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail=f"Image preprocessing failed: {str(e)}"
        )


async def _run_comprehensive_analysis(file_path: str, analysis_types: list) -> dict:
    """Run comprehensive analysis on the image."""
    try:
        results = {}
        
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
                results[task_name] = task_results[i]
        
        # Run rule engine if we have results
        if "rules" in analysis_types and "forensics" in results and "ocr" in results:
            rule_result = await rule_engine.process_results(
                results["forensics"],
                results["ocr"]
            )
            results["rules"] = rule_result
        
        return results
        
    except Exception as e:
        logger.error(f"Comprehensive analysis failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Analysis failed: {str(e)}"
        )


async def _store_analysis_results(file_id: str, analysis_result: dict, 
                                 db: AsyncSession) -> AnalysisResult:
    """Store analysis results in database."""
    try:
        # Extract results
        forensics_result = analysis_result.get("forensics")
        ocr_result = analysis_result.get("ocr")
        rule_result = analysis_result.get("rules")
        
        # Create analysis record
        analysis_record = AnalysisResult(
            id=str(uuid.uuid4()),
            file_id=file_id,
            analysis_timestamp=datetime.utcnow(),
            
            # Forensics results
            forensics_score=forensics_result.overall_score if forensics_result else 0.0,
            edge_inconsistencies=forensics_result.edge_inconsistencies if forensics_result else {},
            compression_artifacts=forensics_result.compression_artifacts if forensics_result else {},
            font_analysis=forensics_result.font_analysis if forensics_result else {},
            
            # OCR results
            ocr_confidence=ocr_result.extraction_confidence if ocr_result else 0.0,
            extracted_fields={
                "payee": ocr_result.payee if ocr_result else None,
                "amount": ocr_result.amount if ocr_result else None,
                "date": ocr_result.date if ocr_result else None,
                "account_number": ocr_result.account_number if ocr_result else None,
                "routing_number": ocr_result.routing_number if ocr_result else None,
                "check_number": ocr_result.check_number if ocr_result else None,
                "memo": ocr_result.memo if ocr_result else None,
                "signature_detected": ocr_result.signature_detected if ocr_result else False,
                "field_confidences": ocr_result.field_confidences if ocr_result else {}
            },
            
            # Rule engine results
            overall_risk_score=rule_result.risk_score if rule_result else 0.0,
            rule_violations={
                "violations": rule_result.violations if rule_result else [],
                "passed_rules": rule_result.passed_rules if rule_result else [],
                "rule_scores": rule_result.rule_scores if rule_result else {}
            },
            confidence_factors=rule_result.confidence_factors if rule_result else {}
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
        extracted_fields = analysis_record.extracted_fields
        rule_violations = analysis_record.rule_violations
        
        # Create response components
        from ...schemas.analysis import ForensicsResult, OCRResult, RuleEngineResult
        
        forensics_result = ForensicsResult(
            edge_score=analysis_record.forensics_score,
            compression_score=analysis_record.compression_artifacts.get('score', 0.0),
            font_score=analysis_record.font_analysis.get('score', 0.0),
            overall_score=analysis_record.forensics_score,
            detected_anomalies=analysis_record.edge_inconsistencies.get('anomalies', []),
            edge_inconsistencies=analysis_record.edge_inconsistencies,
            compression_artifacts=analysis_record.compression_artifacts,
            font_analysis=analysis_record.font_analysis
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
            extraction_confidence=analysis_record.ocr_confidence,
            field_confidences=extracted_fields.get('field_confidences', {})
        )
        
        rule_engine_result = RuleEngineResult(
            risk_score=analysis_record.overall_risk_score,
            violations=rule_violations.get('violations', []),
            passed_rules=rule_violations.get('passed_rules', []),
            rule_scores=rule_violations.get('rule_scores', {}),
            confidence_factors=analysis_record.confidence_factors,
            recommendations=rule_violations.get('recommendations', [])
        )
        
        # Calculate overall confidence
        overall_confidence = (
            analysis_record.ocr_confidence * 0.4 +
            analysis_record.forensics_score * 0.3 +
            analysis_record.confidence_factors.get('overall', 0.0) * 0.3
        )
        
        return AnalysisResponse(
            analysis_id=analysis_record.id,
            file_id=analysis_record.file_id,
            timestamp=analysis_record.analysis_timestamp,
            forensics=forensics_result,
            ocr=ocr_result,
            rules=rule_engine_result,
            overall_risk_score=analysis_record.overall_risk_score,
            confidence=overall_confidence
        )
        
    except Exception as e:
        logger.error(f"Failed to format analysis response: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to format response: {str(e)}"
        )