import asyncio
import logging
import tempfile
import aiohttp
import aiofiles
from pathlib import Path
from typing import Optional
from datetime import datetime, timezone
from contextlib import contextmanager

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker, Session

from .celery_app import celery_app
from ..core.config import settings
from ..models.task_status import TaskStatus, TaskStatusEnum
from ..models.file import FileRecord
from ..models.analysis import AnalysisResult
from ..core.forensics import ForensicsEngine
from ..core.ocr import create_ocr_engine
from ..core.rule_engine import load_rule_engine
from ..core.scoring import RiskScoreCalculator
from ..core.s3 import s3_service
from ..utils.file_utils import (
    validate_file_for_analysis,
    prepare_file_for_analysis,
    FileValidationError,
    FileProcessingError
)
from ..utils.image_utils import cleanup_temp_files
from ..api.v1.analyze import ComprehensiveAnalysisResult, _convert_numpy_types

logger = logging.getLogger(__name__)

# Initialize engines - these will be imported at module level for Celery
forensics_engine = ForensicsEngine()
rule_engine = load_rule_engine()
risk_calculator = RiskScoreCalculator()

# Synchronous database session factory for Celery tasks
engine = create_engine(settings.DATABASE_URL.replace("+asyncpg", ""))
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@contextmanager
def get_task_db_session():
    """Create a new database session for Celery tasks."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def update_task_status(
    task_id: str, 
    status: TaskStatusEnum, 
    progress: Optional[float] = None, 
    error_message: Optional[str] = None,
    result_id: Optional[str] = None
):
    """Update task status in database."""
    try:
        with get_task_db_session() as db:
            task_status = db.execute(
                select(TaskStatus).where(TaskStatus.task_id == task_id)
            ).scalar_one_or_none()
            
            if task_status:
                task_status.status = status
                if progress is not None:
                    task_status.progress = progress
                if error_message is not None:
                    task_status.error_message = error_message
                if result_id is not None:
                    task_status.result_id = result_id
                task_status.updated_at = datetime.now(timezone.utc)
                
                db.commit()
                logger.info(f"Task {task_id} status updated to {status.value} (progress: {progress})")
            else:
                logger.warning(f"Task status not found for task_id: {task_id}")
                
    except Exception as e:
        logger.error(f"Failed to update task status for {task_id}: {str(e)}")


def get_user_file_sync(file_id: str, db: Session) -> FileRecord:
    """Get file record synchronously."""
    file_record = db.execute(
        select(FileRecord).where(FileRecord.id == file_id)
    ).scalar_one_or_none()
    
    if not file_record:
        raise ValueError(f"File not found: {file_id}")
    
    return file_record


async def download_file_sync(s3_key: str) -> str:
    """Download file from S3 asynchronously (wrapped for sync context)."""
    try:
        # Generate presigned URL for download
        download_url = await s3_service.generate_presigned_url(s3_key)
        
        if not download_url:
            raise ValueError("Failed to generate download URL")
        
        # Extract file extension from S3 key to preserve file type
        s3_path = Path(s3_key)
        file_extension = s3_path.suffix or '.tmp'
        
        # Create temporary file with correct extension
        temp_file = tempfile.NamedTemporaryFile(suffix=file_extension, delete=False)
        temp_path = temp_file.name
        temp_file.close()
        
        async with aiohttp.ClientSession() as session:
            async with session.get(download_url) as response:
                if response.status != 200:
                    raise ValueError("Failed to download file from S3")
                
                # Save to temporary file
                async with aiofiles.open(temp_path, 'wb') as f:
                    async for chunk in response.content.iter_chunked(8192):
                        await f.write(chunk)
                
                return temp_path
                
    except Exception as e:
        logger.error(f"Failed to download file {s3_key}: {str(e)}")
        raise


async def validate_and_preprocess_file_async(file_path: str, page_number: int = 1) -> str:
    """Validate and preprocess file asynchronously."""
    try:
        # Validate file (works for both images and PDFs)
        validation_result = validate_file_for_analysis(file_path)
        
        if not validation_result.get('valid', False):
            raise ValueError("Invalid file for analysis")
        
        # Prepare file for analysis (converts PDF to image if needed)
        prepared_path = prepare_file_for_analysis(file_path, page_number=page_number)
        
        return prepared_path
        
    except (FileValidationError, FileProcessingError) as e:
        logger.error(f"File preprocessing failed: {str(e)}")
        raise ValueError(f"File preprocessing failed: {str(e)}")


async def run_comprehensive_analysis_async(file_path: str, analysis_types: list) -> ComprehensiveAnalysisResult:
    """Run comprehensive analysis on the image asynchronously."""
    try:
        forensics_result = None
        ocr_result = None
        rule_result = None
        
        # Run analysis components in parallel
        tasks = []
        
        if "forensics" in analysis_types:
            tasks.append(("forensics", forensics_engine.analyze_image(file_path)))
        
        if "ocr" in analysis_types:
            ocr_engine = await create_ocr_engine()
            tasks.append(("ocr", ocr_engine.extract_fields(file_path)))
        
        # Execute tasks
        if tasks:
            task_results = await asyncio.gather(*[task[1] for task in tasks])
            
            for i, (task_name, _) in enumerate(tasks):
                if task_name == "forensics":
                    forensics_result = task_results[i]
                elif task_name == "ocr":
                    ocr_result = task_results[i]
        
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
                logger.info(f"Risk score calculated: {risk_score_data.overall_score}")
            except Exception as e:
                logger.error(f"Risk score calculation failed: {str(e)}")
        
        return ComprehensiveAnalysisResult(
            forensics_result=forensics_result,
            ocr_result=ocr_result,
            rule_result=rule_result,
            risk_score_data=risk_score_data
        )
        
    except Exception as e:
        logger.error(f"Comprehensive analysis failed: {str(e)}")
        raise


def store_analysis_results_sync(
    file_id: str, 
    analysis_result: ComprehensiveAnalysisResult, 
    db: Session
) -> AnalysisResult:
    """Store analysis results in database synchronously."""
    try:
        import uuid
        
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
            
            # Rule engine results (convert numpy types)
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
        db.commit()
        db.refresh(analysis_record)
        
        return analysis_record
        
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to store analysis results: {str(e)}")
        raise


@celery_app.task(bind=True, name='app.tasks.analysis_tasks.analyze_check_async')
def analyze_check_async(self, file_id: str, analysis_types: list, page_number: int = 1):
    """
    Background task for check analysis.
    
    This task replicates the synchronous analysis workflow but runs in the background.
    All async functions are wrapped with asyncio.run() for Celery compatibility.
    """
    task_id = self.request.id
    logger.info(f"Starting analysis task {task_id} for file {file_id}")
    
    # Update initial status
    update_task_status(task_id, TaskStatusEnum.PROCESSING, progress=0.1)
    
    temp_files_to_cleanup = []
    
    try:
        # Create new database session for task
        with get_task_db_session() as db:
            # Get file record and validate
            file_record = get_user_file_sync(file_id, db)
            logger.info(f"Found file record: {file_record.filename}")
            
            # Download file from S3
            temp_file_path = asyncio.run(download_file_sync(file_record.s3_key))
            temp_files_to_cleanup.append(temp_file_path)
            logger.info(f"Downloaded file to: {temp_file_path}")
            
            update_task_status(task_id, TaskStatusEnum.PROCESSING, progress=0.2)
            
            # Validate and preprocess file
            prepared_path = asyncio.run(
                validate_and_preprocess_file_async(temp_file_path, page_number)
            )
            if prepared_path != temp_file_path:
                temp_files_to_cleanup.append(prepared_path)
            logger.info(f"File prepared for analysis: {prepared_path}")
            
            update_task_status(task_id, TaskStatusEnum.PROCESSING, progress=0.3)
            
            # Run comprehensive analysis
            analysis_result = asyncio.run(
                run_comprehensive_analysis_async(prepared_path, analysis_types)
            )
            logger.info(f"Analysis completed for task {task_id}")
            
            update_task_status(task_id, TaskStatusEnum.PROCESSING, progress=0.8)
            
            # Store results in database
            result_record = store_analysis_results_sync(file_id, analysis_result, db)
            logger.info(f"Results stored with ID: {result_record.id}")
            
            # Update final status
            update_task_status(
                task_id, 
                TaskStatusEnum.SUCCESS, 
                progress=1.0, 
                result_id=result_record.id
            )
            
            return {
                "result_id": result_record.id, 
                "status": "completed",
                "task_id": task_id
            }
            
    except Exception as exc:
        logger.error(f"Analysis task {task_id} failed: {str(exc)}")
        
        # Update status to retry for automatic retry
        update_task_status(
            task_id, 
            TaskStatusEnum.RETRY, 
            error_message=str(exc)
        )
        
        # Automatic retry with exponential backoff
        retry_count = self.request.retries
        countdown = 60 * (2 ** retry_count)  # 60s, 120s, 240s...
        
        logger.info(f"Retrying task {task_id} in {countdown} seconds (attempt {retry_count + 1}/3)")
        
        raise self.retry(exc=exc, countdown=countdown, max_retries=3)
        
    finally:
        # Clean up temporary files
        if temp_files_to_cleanup:
            cleanup_temp_files(temp_files_to_cleanup)