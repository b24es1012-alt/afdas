"""
AFDAS Backend — FastAPI Application Entry Point

AI Flood Disaster Assistance System
Main application with lifecycle management, middleware, and router registration.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import time

from config.settings import settings
from config.environment import get_cors_origins, get_environment
from database.connection import DatabaseManager
from cache.manager import CacheManager
from utils.logger import logger

# API routers
from api.navigation import router as navigation_router
from api.chat import router as chat_router
from api.flood import router as flood_router
from api.analytics import router as analytics_router
from api.health import router as health_router
from api.auth import router as auth_router


# ============================================================================
# LIFESPAN (startup/shutdown)
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifecycle management.
    
    Startup:
    - Connect PostgreSQL/PostGIS
    - Connect Redis
    - Start scheduler (if enabled)
    
    Shutdown:
    - Close database connections
    - Close Redis
    - Cleanup resources
    """
    logger.info("=" * 60)
    logger.info(f"AFDAS Backend v{settings.APP_VERSION} starting...")
    logger.info(f"Environment: {get_environment().value}")
    logger.info("=" * 60)

    # ── Startup ──────────────────────────────────────────────────────────
    try:
        # Connect PostgreSQL
        await DatabaseManager.initialize()
        logger.info("PostgreSQL/PostGIS connected")
    except Exception as e:
        logger.warning(f"Database connection failed (non-fatal): {e}")

    try:
        # Connect Redis
        await CacheManager.initialize()
        logger.info("Redis connected")
    except Exception as e:
        logger.warning(f"Redis connection failed (non-fatal): {e}")

    logger.info("AFDAS Backend ready to serve requests")
    logger.info(f"Listening on {settings.HOST}:{settings.PORT}")

    yield  # Application is running

    # ── Shutdown ─────────────────────────────────────────────────────────
    logger.info("AFDAS Backend shutting down...")

    try:
        await DatabaseManager.close()
    except Exception:
        pass

    try:
        await CacheManager.close()
    except Exception:
        pass

    logger.info("AFDAS Backend stopped.")


# ============================================================================
# APP CREATION
# ============================================================================

app = FastAPI(
    title="AFDAS - AI Flood Disaster Assistance System",
    description=(
        "AI-powered flood navigation and emergency assistance platform. "
        "Integrates Copernicus EMS flood data, OpenStreetMap infrastructure, "
        "graph-based routing algorithms, and AI agents for intelligent "
        "flood-safe navigation."
    ),
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)


# ============================================================================
# MIDDLEWARE
# ============================================================================

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request timing middleware
@app.middleware("http")
async def add_timing_header(request: Request, call_next):
    """Add X-Process-Time header to all responses."""
    start = time.time()
    response = await call_next(request)
    process_time = time.time() - start
    response.headers["X-Process-Time"] = f"{process_time:.4f}"
    return response


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch-all error handler."""
    logger.error(f"Unhandled error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc) if settings.DEBUG else "An unexpected error occurred",
        },
    )


# ============================================================================
# REGISTER ROUTERS
# ============================================================================

app.include_router(health_router)
app.include_router(auth_router, prefix="/api/v1")
app.include_router(navigation_router, prefix="/api/v1")
app.include_router(chat_router, prefix="/api/v1")
app.include_router(flood_router, prefix="/api/v1")
app.include_router(analytics_router, prefix="/api/v1")


# ============================================================================
# ROOT ENDPOINT
# ============================================================================

@app.get("/")
async def root():
    """API root — basic info."""
    return {
        "name": "AFDAS - AI Flood Disaster Assistance System",
        "version": settings.APP_VERSION,
        "status": "running",
        "docs": "/docs",
        "health": "/health",
    }


# ============================================================================
# RUN
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        workers=1 if settings.DEBUG else 4,
    )
