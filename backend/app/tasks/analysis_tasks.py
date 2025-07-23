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
from ..core.streaming import StreamingFileProcessor, StreamProgress
from .resource_monitor import (
    create_resource_monitor_for_file,
    ResourceLimitError,
    log_resource_usage
)
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


@celery_app.task(bind=True, name='app.tasks.analysis_tasks.analyze_check_streaming')
def analyze_check_streaming(self, file_id: str, analysis_types: list, page_number: int = 1):
    """
    Streaming background task for check analysis with resource monitoring.
    
    This task uses streaming file processing and resource monitoring to prevent
    memory exhaustion and provide real-time progress updates.
    """
    task_id = self.request.id
    logger.info(f"Starting streaming analysis task {task_id} for file {file_id}")
    
    # Initialize resource monitor (will be configured based on file size)
    monitor = None
    temp_files_to_cleanup = []
    
    # Update initial status
    update_task_status(task_id, TaskStatusEnum.PROCESSING, progress=0.05)
    
    try:
        # Create new database session for task
        with get_task_db_session() as db:
            # Get file record and validate
            file_record = get_user_file_sync(file_id, db)
            logger.info(f"Found file record: {file_record.filename}")
            
            # Create resource monitor based on file size
            file_size_bytes = getattr(file_record, 'file_size', 0) or 0
            monitor = create_resource_monitor_for_file(file_size_bytes)
            logger.info(f"Resource monitor configured for {file_size_bytes} byte file")
            
            # Progress callback for streaming operations
            def progress_callback(progress: StreamProgress):
                # Convert streaming progress to task progress
                if progress.phase == "downloading":
                    task_progress = 0.1 + (progress.progress_percentage / 100.0) * 0.1  # 0.1-0.2
                elif progress.phase == "validation":
                    task_progress = 0.2 + (progress.progress_percentage / 100.0) * 0.1  # 0.2-0.3
                elif progress.phase == "preprocessing":
                    task_progress = 0.3 + (progress.progress_percentage / 100.0) * 0.1  # 0.3-0.4
                else:
                    task_progress = 0.4
                
                # Include resource usage in progress updates
                try:
                    if monitor:
                        usage = monitor.check_resources()
                        meta = {
                            'phase': progress.phase,
                            'progress': task_progress,
                            'bytes_processed': progress.bytes_processed,
                            'total_bytes': progress.total_bytes,
                            'resource_usage': {
                                'memory_mb': usage.memory_mb,
                                'peak_memory_mb': usage.peak_memory_mb,
                                'cpu_percent': usage.cpu_percent,
                                'processing_time_seconds': usage.processing_time_seconds
                            }
                        }
                    else:
                        meta = {
                            'phase': progress.phase,
                            'progress': task_progress,
                            'bytes_processed': progress.bytes_processed,
                            'total_bytes': progress.total_bytes
                        }
                    
                    self.update_state(state='PROGRESS', meta=meta)
                except Exception as e:
                    logger.warning(f"Progress update failed: {str(e)}")
            
            # Use streaming file processor and run analysis inside context
            async def process_with_streaming_and_analysis():
                async with StreamingFileProcessor(
                    file_record.s3_key,
                    page_number,
                    progress_callback
                ) as prepared_path:
                    temp_files_to_cleanup.append(prepared_path)
                    logger.info(f"File prepared for analysis: {prepared_path}")
                    
                    # Update progress after preprocessing
                    if monitor:
                        usage = monitor.check_resources()
                        log_resource_usage(usage, "preprocessing")
                    
                    update_task_status(task_id, TaskStatusEnum.PROCESSING, progress=0.4)
                    
                    # Update intermediate progress during analysis phases
                    self.update_state(
                        state='PROGRESS',
                        meta={
                            'phase': 'forensics',
                            'progress': 0.5,
                            'current_operation': 'Running forensics analysis'
                        }
                    )
                    
                    # Run comprehensive analysis with resource monitoring inside context
                    if monitor:
                        # Monitor the analysis operation
                        analysis_result = await monitor.monitor_async_operation(
                            run_comprehensive_analysis_async(prepared_path, analysis_types),
                            f"analysis-{task_id}"
                        )
                    else:
                        analysis_result = await run_comprehensive_analysis_async(prepared_path, analysis_types)
                    
                    return analysis_result
            
            analysis_result = asyncio.run(process_with_streaming_and_analysis())
            logger.info(f"Analysis completed for task {task_id}")
            
            # Log final resource usage
            if monitor:
                final_usage = monitor.check_resources()
                log_resource_usage(final_usage, "analysis_complete")
                usage_summary = monitor.get_usage_summary()
                logger.info(f"Resource usage summary: {usage_summary}")
            
            update_task_status(task_id, TaskStatusEnum.PROCESSING, progress=0.8)
            
            # Store results in database
            result_record = store_analysis_results_sync(file_id, analysis_result, db)
            logger.info(f"Results stored with ID: {result_record.id}")
            
            # Update final status with resource usage summary
            final_meta = {"result_id": result_record.id}
            if monitor:
                final_meta["resource_usage_summary"] = monitor.get_usage_summary()
            
            update_task_status(
                task_id, 
                TaskStatusEnum.SUCCESS, 
                progress=1.0, 
                result_id=result_record.id
            )
            
            return {
                "result_id": result_record.id, 
                "status": "completed",
                "task_id": task_id,
                "resource_usage": final_meta.get("resource_usage_summary")
            }
            
    except ResourceLimitError as exc:
        logger.error(f"Analysis task {task_id} terminated due to resource limits: {str(exc)}")
        
        # Log resource usage at termination
        if monitor:
            try:
                usage = monitor.check_resources()
                log_resource_usage(usage, "resource_limit_exceeded")
            except Exception:
                pass
        
        # Don't retry resource limit errors - they'll likely fail again
        update_task_status(
            task_id,
            TaskStatusEnum.FAILED,
            error_message=f"Resource limit exceeded: {str(exc)}"
        )
        
        raise exc
        
    except Exception as exc:
        logger.error(f"Analysis task {task_id} failed: {str(exc)}")
        
        # Log resource usage at failure
        if monitor:
            try:
                usage = monitor.check_resources()
                log_resource_usage(usage, "task_failed")
            except Exception:
                pass
        
        # Update status to retry for automatic retry
        update_task_status(
            task_id, 
            TaskStatusEnum.RETRY, 
            error_message=str(exc)
        )
        
        # Automatic retry with exponential backoff (but not for resource limit errors)
        if not isinstance(exc, ResourceLimitError):
            retry_count = self.request.retries
            countdown = 60 * (2 ** retry_count)  # 60s, 120s, 240s...
            
            logger.info(f"Retrying task {task_id} in {countdown} seconds (attempt {retry_count + 1}/3)")
            
            raise self.retry(exc=exc, countdown=countdown, max_retries=3)
        else:
            # Don't retry resource limit errors
            raise
        
    finally:
        # Clean up temporary files
        if temp_files_to_cleanup:
            try:
                cleanup_temp_files(temp_files_to_cleanup)
            except Exception as cleanup_error:
                logger.warning(f"Cleanup failed: {str(cleanup_error)}")
        
        # Log final resource state
        if monitor:
            try:
                final_usage = monitor.check_resources()
                logger.info(
                    f"Task {task_id} final resource usage: "
                    f"memory={final_usage.memory_mb:.1f}MB (peak={final_usage.peak_memory_mb:.1f}MB), "
                    f"time={final_usage.processing_time_seconds:.1f}s"
                )
            except Exception:
                pass


# Legacy task name for backward compatibility
@celery_app.task(bind=True, name='app.tasks.analysis_tasks.analyze_check_async')
def analyze_check_async(self, file_id: str, analysis_types: list, page_number: int = 1):
    """
    Legacy task - redirects to streaming version.
    Maintained for backward compatibility.
    """
    logger.info(f"Legacy task called, redirecting to streaming version for file {file_id}")
    return analyze_check_streaming(self, file_id, analysis_types, page_number)