from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import logging

from ...database import get_db
from ...models.user import User
from ...models.task_status import TaskStatus, TaskStatusEnum
from ...models.analysis import AnalysisResult
from ...schemas.analysis import (
    TaskStatusResponse, 
    TaskResultResponse
)
from ..deps import get_current_user
from .analyze import _format_analysis_response

router = APIRouter(tags=["tasks"])
logger = logging.getLogger(__name__)


@router.get("/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get the status of an async analysis task.
    
    Returns current progress, status, and result information if completed.
    """
    try:
        # Get task status with user validation
        result = await db.execute(
            select(TaskStatus)
            .where(TaskStatus.task_id == task_id)
            .where(TaskStatus.user_id == current_user.id)
        )
        task_status = result.scalar_one_or_none()
        
        if not task_status:
            raise HTTPException(
                status_code=404,
                detail="Task not found or access denied"
            )
        
        # Build result URL if task is completed
        result_url = None
        if task_status.status == TaskStatusEnum.SUCCESS and task_status.result_id:
            result_url = f"/api/v1/tasks/{task_id}/result"
        
        # Convert model enum to schema enum
        from ...schemas.analysis import TaskStatusEnum as SchemaTaskStatusEnum
        schema_status = SchemaTaskStatusEnum(task_status.status.value)
        
        return TaskStatusResponse(
            task_id=task_status.task_id,
            status=schema_status,
            progress=task_status.progress,
            file_id=task_status.file_id,
            created_at=task_status.created_at,
            updated_at=task_status.updated_at,
            estimated_duration=task_status.estimated_duration,
            error_message=task_status.error_message,
            result_id=task_status.result_id,
            result_url=result_url
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get task status {task_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get task status: {str(e)}"
        )


@router.get("/{task_id}/result", response_model=TaskResultResponse)
async def get_task_result(
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get the analysis result for a completed task.
    
    Returns the full analysis result if the task completed successfully,
    or error information if the task failed.
    """
    try:
        # Get task status with user validation
        result = await db.execute(
            select(TaskStatus)
            .where(TaskStatus.task_id == task_id)
            .where(TaskStatus.user_id == current_user.id)
        )
        task_status = result.scalar_one_or_none()
        
        if not task_status:
            raise HTTPException(
                status_code=404,
                detail="Task not found or access denied"
            )
        
        # Convert model enum to schema enum
        from ...schemas.analysis import TaskStatusEnum as SchemaTaskStatusEnum
        schema_status = SchemaTaskStatusEnum(task_status.status.value)
        
        # Handle different task states
        if task_status.status == TaskStatusEnum.PENDING:
            return TaskResultResponse(
                task_id=task_id,
                status=schema_status,
                result=None,
                error_message="Task is still pending"
            )
        
        elif task_status.status == TaskStatusEnum.PROCESSING:
            return TaskResultResponse(
                task_id=task_id,
                status=schema_status,
                result=None,
                error_message="Task is still processing"
            )
        
        elif task_status.status == TaskStatusEnum.SUCCESS:
            if not task_status.result_id:
                raise HTTPException(
                    status_code=500,
                    detail="Task completed but no result found"
                )
            
            # Get the analysis result
            analysis_result = await db.execute(
                select(AnalysisResult)
                .where(AnalysisResult.id == task_status.result_id)
            )
            analysis_record = analysis_result.scalar_one_or_none()
            
            if not analysis_record:
                raise HTTPException(
                    status_code=500,
                    detail="Analysis result not found"
                )
            
            # Format the analysis response
            formatted_result = await _format_analysis_response(analysis_record)
            
            return TaskResultResponse(
                task_id=task_id,
                status=schema_status,
                result=formatted_result,
                error_message=None
            )
        
        elif task_status.status in [TaskStatusEnum.FAILURE, TaskStatusEnum.RETRY]:
            return TaskResultResponse(
                task_id=task_id,
                status=schema_status,
                result=None,
                error_message=task_status.error_message or "Task failed"
            )
        
        else:
            return TaskResultResponse(
                task_id=task_id,
                status=schema_status,
                result=None,
                error_message="Unknown task status"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get task result {task_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get task result: {str(e)}"
        )


@router.delete("/{task_id}")
async def cancel_task(
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Cancel a running task.
    
    Note: This only marks the task as cancelled in the database.
    The actual Celery task may continue running if already started.
    """
    try:
        # Get task status with user validation
        result = await db.execute(
            select(TaskStatus)
            .where(TaskStatus.task_id == task_id)
            .where(TaskStatus.user_id == current_user.id)
        )
        task_status = result.scalar_one_or_none()
        
        if not task_status:
            raise HTTPException(
                status_code=404,
                detail="Task not found or access denied"
            )
        
        # Only allow cancellation of pending or processing tasks
        if task_status.status not in [TaskStatusEnum.PENDING, TaskStatusEnum.PROCESSING]:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot cancel task with status: {task_status.status.value}"
            )
        
        # Try to revoke the Celery task
        try:
            from ...tasks.celery_app import celery_app
            celery_app.control.revoke(task_id, terminate=True)
            logger.info(f"Revoked Celery task {task_id}")
        except Exception as e:
            logger.warning(f"Failed to revoke Celery task {task_id}: {str(e)}")
        
        # Update task status to failure
        task_status.status = TaskStatusEnum.FAILURE
        task_status.error_message = "Task cancelled by user"
        task_status.progress = 0.0
        
        await db.commit()
        
        return {"message": "Task cancelled successfully", "task_id": task_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel task {task_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to cancel task: {str(e)}"
        )