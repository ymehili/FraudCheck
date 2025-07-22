from fastapi import APIRouter
from .auth import router as auth_router
from .files import router as files_router
from .analyze import router as analyze_router
from .dashboard import router as dashboard_router

router = APIRouter()

router.include_router(auth_router, prefix="/auth", tags=["auth"])
router.include_router(files_router, prefix="/files", tags=["files"])
router.include_router(analyze_router, prefix="/analyze", tags=["analysis"])
router.include_router(dashboard_router, prefix="/dashboard", tags=["dashboard"])

# Alias for tests
api_router = router