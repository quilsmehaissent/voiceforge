"""
VoiceForge API - Main Application
Text-to-Speech API using Qwen3-TTS models.
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.app.api.routes import router as api_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup and shutdown events."""
    # Startup
    logger.info("=" * 60)
    logger.info("VoiceForge API Starting...")
    logger.info("=" * 60)
    
    # Import engine to trigger initialization log
    from backend.app.core.tts_engine import tts_engine
    logger.info(f"TTS Engine initialized on device: {tts_engine.device}")
    logger.info("Models will be loaded on first request (lazy loading)")
    logger.info("=" * 60)
    
    yield
    
    # Shutdown
    logger.info("VoiceForge API Shutting down...")
    try:
        from backend.app.core.tts_engine import tts_engine
        tts_engine.unload_all_models()
        logger.info("All models unloaded successfully")
    except Exception as e:
        logger.warning(f"Error during shutdown: {e}")


# Create FastAPI app
app = FastAPI(
    title="VoiceForge API",
    description="""
## Text-to-Speech API powered by Qwen3-TTS

VoiceForge provides three modes of speech synthesis:

### 🎭 Preset Voices
Generate speech using pre-configured voice characters with emotion control.

### ✨ Voice Design
Create custom voices from natural language descriptions.
Describe the voice you want: age, gender, tone, accent, emotion, etc.

### 🎤 Voice Cloning
Clone any voice from a reference audio sample and synthesize new content.

---

**Powered by Alibaba Qwen3-TTS**
    """,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",      # Next.js dev server
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router, prefix="/api", tags=["TTS"])


# ============================================================================
# Static Files
# ============================================================================

from fastapi.staticfiles import StaticFiles
import os

# Ensure static directories exist
os.makedirs("backend/static/generations", exist_ok=True)

# Mount static files
app.mount("/static", StaticFiles(directory="backend/static"), name="static")



# ============================================================================
# Root Endpoints
# ============================================================================

@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "VoiceForge API",
        "version": "1.0.0",
        "description": "Text-to-Speech API powered by Qwen3-TTS",
        "docs": "/docs",
        "health": "/health",
        "api_prefix": "/api"
    }


@app.get("/health")
async def health_check():
    """
    Health check endpoint.
    Returns the operational status of the API and TTS engine.
    """
    try:
        from backend.app.core.tts_engine import tts_engine
        engine_status = tts_engine.get_status()
        
        return JSONResponse(content={
            "status": "healthy",
            "engine": {
                "device": engine_status["device"],
                "models_loaded": engine_status["models_loaded"],
                "available_presets": len(engine_status["available_presets"]),
            }
        })
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e)
            }
        )


# ============================================================================
# Error Handlers
# ============================================================================

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler for unhandled errors."""
    logger.error(f"Unhandled error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": "An unexpected error occurred. Please try again."
        }
    )


# ============================================================================
# Run with Uvicorn
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
