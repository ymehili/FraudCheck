from fastapi import APIRouter
from .auth import router as auth_router
from .files import router as files_router

router = APIRouter()

router.include_router(auth_router, prefix="/auth", tags=["auth"])
router.include_router(files_router, prefix="/files", tags=["files"])