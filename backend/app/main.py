from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1 import api
from app.core.config import settings
from app.core.executor_manager import ExecutorManager
from app.utils.redis_cache import RedisConnection
from app.utils.cache import start_cache_cleanup_task
import logging

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle: ProcessPoolExecutor and Redis connections."""
    # Startup
    try:
        # Initialize ProcessPoolExecutor
        logger.info("Initializing ProcessPoolExecutor for forensics analysis...")
        executor_manager = ExecutorManager()
        app.state.executor_manager = executor_manager
        logger.info("ProcessPoolExecutor initialized successfully")
        
        # Initialize Redis connection pool
        logger.info("Initializing Redis connection pool...")
        await RedisConnection.get_redis_client()
        logger.info("Redis connection pool initialized successfully")
        
        # Start cache cleanup task (no-op for Redis but maintains compatibility)
        await start_cache_cleanup_task()
        
    except Exception as e:
        logger.error(f"Failed to initialize application resources: {str(e)}")
        raise
    
    yield
    
    # Shutdown
    try:
        # Shutdown ProcessPoolExecutor
        logger.info("Shutting down ProcessPoolExecutor...")
        if hasattr(app.state, 'executor_manager'):
            app.state.executor_manager.shutdown(wait=True)
        logger.info("ProcessPoolExecutor shutdown completed")
        
        # Close Redis connections
        logger.info("Closing Redis connections...")
        await RedisConnection.close()
        logger.info("Redis connections closed successfully")
        
    except Exception as e:
        logger.error(f"Error during application shutdown: {str(e)}")


app = FastAPI(
    title="FraudCheck AI API",
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
    return {"message": "FraudCheck AI API is running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}