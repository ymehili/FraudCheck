from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1 import api
from app.core.config import settings

app = FastAPI(
    title="CheckGuard AI",
    description="AI-powered check fraud detection system",
    version="1.0.0",
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