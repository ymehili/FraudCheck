from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1 import api
from app.core.config import settings
from app.core.executor_manager import ExecutorManager
import logging

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage ProcessPoolExecutor lifecycle for forensics analysis."""
    # Startup
    try:
        logger.info("Initializing ProcessPoolExecutor for forensics analysis...")
        executor_manager = ExecutorManager()
        app.state.executor_manager = executor_manager
        logger.info("ProcessPoolExecutor initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize ProcessPoolExecutor: {str(e)}")
        raise
    
    yield
    
    # Shutdown
    try:
        logger.info("Shutting down ProcessPoolExecutor...")
        if hasattr(app.state, 'executor_manager'):
            app.state.executor_manager.shutdown(wait=True)
        logger.info("ProcessPoolExecutor shutdown completed")
    except Exception as e:
        logger.error(f"Error during ProcessPoolExecutor shutdown: {str(e)}")


app = FastAPI(
    title="CheckGuard AI API",
    description="AI-powered check fraud detection system",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api.router, prefix="/api/v1")

@app.get("/")
async def root():
    return {"message": "CheckGuard AI API is running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}