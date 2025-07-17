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

@router.post("/upload-debug", response_model=FileUploadResponse)
async def upload_file_debug(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Debug upload endpoint without authentication."""
    
    # Validate file
    s3_service.validate_file(file)
    
    try:
        # Use a test user ID for debugging
        test_user_id = "debug_user_123"
        
        # Get or create test user
        result = await db.execute(select(User).where(User.id == test_user_id))
        user = result.scalar_one_or_none()
        
        if not user:
            user = User(id=test_user_id, email="debug@test.com")
            db.add(user)
            await db.commit()
            await db.refresh(user)
        
        # Upload to S3
        s3_data = await s3_service.upload_file(file, user.id)
        
        # Create file record in database
        file_record = FileRecord(
            id=str(uuid.uuid4()),
            user_id=user.id,
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
            message="File uploaded successfully (debug mode)"
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
        # Download file temporarily to analyze
        download_url = await s3_service.generate_presigned_url(file_record.s3_key)
        if not download_url:
            raise HTTPException(
                status_code=500,
                detail="Failed to generate download URL for analysis"
            )
        
        import aiohttp
        import tempfile
        import aiofiles
        from ...utils.file_utils import get_file_info, get_file_type
        
        # Download to temporary file
        temp_file = tempfile.NamedTemporaryFile(suffix='.tmp', delete=False)
        temp_path = temp_file.name
        temp_file.close()
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(download_url) as response:
                    if response.status == 200:
                        async with aiofiles.open(temp_path, 'wb') as f:
                            async for chunk in response.content.iter_chunked(8192):
                                await f.write(chunk)
            
            # Get detailed file information
            file_info = get_file_info(temp_path)
            file_type = file_info.get('file_type', 'unknown')
            
            # Determine supported operations
            supported_operations = []
            if file_info.get('analysis_ready', False):
                supported_operations.extend(['analyze', 'download'])
            
            if file_type == 'pdf':
                supported_operations.append('convert_to_images')
            elif file_type == 'image':
                supported_operations.extend(['enhance', 'resize', 'crop'])
            
            return FileInfoResponse(
                id=file_record.id,
                filename=file_record.filename,
                file_type=file_type,
                mime_type=file_record.mime_type,
                file_size=file_record.file_size,
                upload_timestamp=file_record.upload_timestamp,
                analysis_ready=file_info.get('analysis_ready', False),
                pages=file_info.get('pages', 1),
                metadata=file_info.get('metadata', {}),
                supported_operations=supported_operations
            )
            
        finally:
            # Clean up temporary file
            import os
            if os.path.exists(temp_path):
                os.remove(temp_path)
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to analyze file: {str(e)}"
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


@router.get("/debug", response_model=FileListResponse)
async def list_files_debug(
    page: int = 1,
    per_page: int = 10,
    db: AsyncSession = Depends(get_db),
):
    """Debug endpoint to list files without authentication."""
    
    # Use debug user ID
    debug_user_id = "debug_user_123"
    
    # Get or create debug user
    result = await db.execute(select(User).where(User.id == debug_user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        user = User(id=debug_user_id, email="debug@test.com")
        db.add(user)
        await db.commit()
        await db.refresh(user)
    
    # Calculate offset
    offset = (page - 1) * per_page
    
    # Get files with pagination
    result = await db.execute(
        select(FileRecord)
        .where(FileRecord.user_id == debug_user_id)
        .order_by(FileRecord.upload_timestamp.desc())
        .offset(offset)
        .limit(per_page)
    )
    files = result.scalars().all()
    
    # Get total count
    count_result = await db.execute(
        select(FileRecord)
        .where(FileRecord.user_id == debug_user_id)
    )
    total = len(count_result.scalars().all())
    
    return FileListResponse(
        files=[FileResponse.model_validate(file) for file in files],
        total=total,
        page=page,
        per_page=per_page
    )