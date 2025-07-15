from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
import uuid
from datetime import datetime

from ...database import get_db
from ...models.user import User
from ...models.file import FileRecord
from ...schemas.file import FileResponse, FileUploadResponse, FileListResponse
from ...core.s3 import s3_service
from ..deps import get_current_user

router = APIRouter()

@router.post("/upload", response_model=FileUploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload a check image file to S3 and store metadata in database."""
    
    # Validate file
    s3_service.validate_file(file)
    
    try:
        # Upload to S3
        s3_data = await s3_service.upload_file(file, current_user.id)
        
        # Create file record in database
        file_record = FileRecord(
            id=str(uuid.uuid4()),
            user_id=current_user.id,
            filename=file.filename,
            s3_key=s3_data['s3_key'],
            s3_url=s3_data['s3_url'],
            file_size=s3_data['file_size'],
            mime_type=s3_data['content_type'],
        )
        
        db.add(file_record)
        await db.commit()
        await db.refresh(file_record)
        
        return FileUploadResponse(
            file_id=file_record.id,
            s3_url=file_record.s3_url,
            upload_timestamp=file_record.upload_timestamp,
            message="File uploaded successfully"
        )
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to upload file: {str(e)}"
        )

@router.get("/", response_model=FileListResponse)
async def list_files(
    page: int = 1,
    per_page: int = 10,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List user's uploaded files with pagination."""
    
    # Calculate offset
    offset = (page - 1) * per_page
    
    # Get files with pagination
    result = await db.execute(
        select(FileRecord)
        .where(FileRecord.user_id == current_user.id)
        .order_by(FileRecord.upload_timestamp.desc())
        .offset(offset)
        .limit(per_page)
    )
    files = result.scalars().all()
    
    # Get total count
    count_result = await db.execute(
        select(FileRecord)
        .where(FileRecord.user_id == current_user.id)
    )
    total = len(count_result.scalars().all())
    
    return FileListResponse(
        files=[FileResponse.from_orm(file) for file in files],
        total=total,
        page=page,
        per_page=per_page
    )

@router.get("/{file_id}", response_model=FileResponse)
async def get_file(
    file_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get file information by ID."""
    
    result = await db.execute(
        select(FileRecord)
        .where(FileRecord.id == file_id)
        .where(FileRecord.user_id == current_user.id)
    )
    file_record = result.scalar_one_or_none()
    
    if not file_record:
        raise HTTPException(
            status_code=404,
            detail="File not found"
        )
    
    return FileResponse.from_orm(file_record)

@router.delete("/{file_id}")
async def delete_file(
    file_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a file from S3 and database."""
    
    result = await db.execute(
        select(FileRecord)
        .where(FileRecord.id == file_id)
        .where(FileRecord.user_id == current_user.id)
    )
    file_record = result.scalar_one_or_none()
    
    if not file_record:
        raise HTTPException(
            status_code=404,
            detail="File not found"
        )
    
    try:
        # Delete from S3
        await s3_service.delete_file(file_record.s3_key)
        
        # Delete from database
        await db.delete(file_record)
        await db.commit()
        
        return {"message": "File deleted successfully"}
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete file: {str(e)}"
        )

@router.get("/{file_id}/download")
async def download_file(
    file_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate a presigned URL for file download."""
    
    result = await db.execute(
        select(FileRecord)
        .where(FileRecord.id == file_id)
        .where(FileRecord.user_id == current_user.id)
    )
    file_record = result.scalar_one_or_none()
    
    if not file_record:
        raise HTTPException(
            status_code=404,
            detail="File not found"
        )
    
    # Generate presigned URL
    download_url = await s3_service.generate_presigned_url(file_record.s3_key)
    
    if not download_url:
        raise HTTPException(
            status_code=500,
            detail="Failed to generate download URL"
        )
    
    return {"download_url": download_url, "expires_in": 3600}