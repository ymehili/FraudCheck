from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid

from ...database import get_db
from ...models.user import User
from ...models.file import FileRecord
from ...schemas.file import FileResponse, FileUploadResponse, FileListResponse, FileInfoResponse
from ...core.s3 import s3_service
from ..deps import get_current_user

router = APIRouter(tags=["files"])

@router.post("/upload", response_model=FileUploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload a check image file to S3 and store metadata in database."""
    
    # Validate file with comprehensive security checks
    validation_result = await s3_service.validate_file(file)
    
    try:
        # Upload to S3 with file hash for secure naming
        s3_data = await s3_service.upload_file(
            file, 
            current_user.id, 
            validation_result.get('file_hash')
        )
        
        # Create file record in database with validation metadata
        file_record = FileRecord(
            id=str(uuid.uuid4()),
            user_id=current_user.id,
            filename=file.filename,
            s3_key=s3_data['s3_key'],
            s3_url=s3_data['s3_url'],
            file_size=validation_result['file_size'],  # Use validated size
            mime_type=validation_result['actual_mime_type'],  # Use validated MIME type
        )
        
        # Store validation metadata in a separate field if needed
        # This could be added to the FileRecord model later
        # file_record.validation_hash = validation_result['file_hash']
        # file_record.validation_details = validation_result['validation_details']
        
        db.add(file_record)
        await db.commit()
        await db.refresh(file_record)
        
        return FileUploadResponse(
            file_id=file_record.id,
            s3_url=file_record.s3_url,
            upload_timestamp=file_record.upload_timestamp,
            message="File uploaded and validated successfully"
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
        files=[FileResponse.model_validate(file) for file in files],
        total=total,
        page=page,
        per_page=per_page
    )

def _determine_file_type_from_mime_type(mime_type: str) -> str:
    """Determine file type from MIME type."""
    if mime_type.startswith('image/'):
        return 'image'
    elif mime_type == 'application/pdf':
        return 'pdf'
    else:
        return 'unknown'


def _get_supported_operations(file_type: str, analysis_ready: bool) -> list:
    """Get supported operations based on file type and analysis readiness."""
    supported_operations = []
    
    if analysis_ready:
        supported_operations.extend(['analyze', 'download'])
    
    if file_type == 'pdf':
        supported_operations.append('convert_to_images')
    elif file_type == 'image':
        supported_operations.extend(['enhance', 'resize', 'crop'])
    
    return supported_operations


@router.get("/{file_id}/info", response_model=FileInfoResponse)
async def get_file_info(
    file_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get detailed file information including type-specific metadata."""
    
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
        # Get S3 metadata without downloading the file
        s3_metadata = await s3_service.get_object_metadata(file_record.s3_key)
        if not s3_metadata:
            raise HTTPException(
                status_code=404,
                detail="File not found in storage"
            )
        
        # Determine file type from MIME type
        file_type = _determine_file_type_from_mime_type(file_record.mime_type)
        
        # For basic file info, we can determine analysis readiness without downloading
        analysis_ready = file_type in ['image', 'pdf']
        
        # Estimate pages based on file type
        pages = 1  # Default for images
        if file_type == 'pdf':
            # For PDFs, we can't know exact page count without reading the file
            # but we can provide a reasonable default
            pages = 1
        
        # Build metadata from available information
        metadata = {
            'etag': s3_metadata.get('etag'),
            'last_modified': s3_metadata.get('last_modified'),
            'server_side_encryption': s3_metadata.get('server_side_encryption'),
            's3_metadata': s3_metadata.get('s3_metadata', {}),
            'content_length_s3': s3_metadata.get('content_length')
        }
        
        # Get supported operations
        supported_operations = _get_supported_operations(file_type, analysis_ready)
        
        return FileInfoResponse(
            id=file_record.id,
            filename=file_record.filename,
            file_type=file_type,
            mime_type=file_record.mime_type,
            file_size=file_record.file_size,
            upload_timestamp=file_record.upload_timestamp,
            analysis_ready=analysis_ready,
            pages=pages,
            metadata=metadata,
            supported_operations=supported_operations
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get file info: {str(e)}"
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
    
    return FileResponse.model_validate(file_record)

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
