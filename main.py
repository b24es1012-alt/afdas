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
from config.environment import get_cors_origins, get_environment, is_production
from database.connection import DatabaseManager
from cache.manager import CacheManager
from auth.security_headers import SecurityHeadersMiddleware
from auth.rate_limiter import RateLimiter
from utils.logger import logger

# API routers
from api.navigation import router as navigation_router
from api.chat import router as chat_router
from api.flood import router as flood_router
from api.analytics import router as analytics_router
from api.health import router as health_router
from api.auth import router as auth_router
from api.visualize import router as visualize_router


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
    logger.info(f"Security: rate_limit={settings.RATE_LIMIT_REQUESTS}/min, "
                f"login_lockout={settings.LOGIN_MAX_ATTEMPTS} attempts")
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

    # Start Copernicus EMS auto-polling scheduler
    try:
        from scheduler.copernicus_job import CopernicusPollingJob
        import asyncio

        copernicus_job = CopernicusPollingJob()

        async def _polling_loop():
            """Background loop that polls Copernicus EMS for new flood data."""
            await asyncio.sleep(10)  # Wait 10s after startup before first poll
            while True:
                try:
                    await copernicus_job.run()
                except Exception as e:
                    logger.error(f"Copernicus polling error: {e}")
                await asyncio.sleep(copernicus_job.poll_interval)

        # Start as background task
        asyncio.create_task(_polling_loop())
        logger.info(
            f"Copernicus EMS auto-poller started "
            f"(interval: {settings.COPERNICUS_POLL_INTERVAL}s)"
        )
    except Exception as e:
        logger.warning(f"Copernicus scheduler failed to start (non-fatal): {e}")

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
    # Disable docs in production for security
    docs_url=None if is_production() else "/docs",
    redoc_url=None if is_production() else "/redoc",
    openapi_url=None if is_production() else "/openapi.json",
)


# ============================================================================
# MIDDLEWARE (order matters — last added = first executed in Starlette)
# So we add CORS LAST to ensure it runs FIRST
# ============================================================================

# 1. Security headers (runs second)
app.add_middleware(SecurityHeadersMiddleware)

# 2. CORS — added LAST so it runs FIRST (handles OPTIONS preflight before anything else)
_cors_origins = get_cors_origins()
_allow_all = "*" in _cors_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=not _allow_all,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-Process-Time", "X-RateLimit-Remaining", "X-RateLimit-Reset"],
    max_age=600,
)


# 3. FIRST middleware to execute — handle OPTIONS immediately with CORS headers
# This runs before rate limiter, before size check, before everything
@app.middleware("http")
async def cors_preflight_handler(request: Request, call_next):
    """
    Handle OPTIONS preflight directly — bypass all other middleware.
    This ensures CORS headers are ALWAYS present on preflight responses.
    """
    if request.method == "OPTIONS":
        from fastapi.responses import Response
        origin = request.headers.get("origin", "*")
        allowed_origin = origin if (_allow_all or origin in _cors_origins) else _cors_origins[0] if _cors_origins else "*"
        return Response(
            status_code=200,
            headers={
                "Access-Control-Allow-Origin": "*" if _allow_all else allowed_origin,
                "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
                "Access-Control-Allow-Headers": request.headers.get("access-control-request-headers", "*"),
                "Access-Control-Max-Age": "600",
            },
        )
    return await call_next(request)


# 4. Rate limiting middleware
@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """
    Global rate limiting — applied to all requests.
    Uses per-IP sliding window with Redis.
    """
    # Skip rate limiting for health checks
    if request.url.path in ("/health", "/", "/docs", "/redoc", "/openapi.json"):
        return await call_next(request)

    # Skip rate limiting for CORS preflight (OPTIONS) requests
    # Browsers send these automatically before real requests — must never be blocked
    if request.method == "OPTIONS":
        return await call_next(request)
    client_ip = RateLimiter.get_client_ip(request)

    # Determine tier based on path
    path = request.url.path
    if "/auth/login" in path or "/auth/register" in path:
        tier = "auth"
    elif "/chat" in path:
        tier = "chat"
    else:
        tier = "general"

    allowed, remaining, reset_in = await RateLimiter.check_rate_limit(
        identifier=client_ip,
        tier=tier,
    )

    if not allowed:
        logger.warning(f"Rate limit exceeded: {client_ip} on {tier} tier")
        return JSONResponse(
            status_code=429,
            content={
                "error": "Too many requests",
                "detail": f"Rate limit exceeded. Try again in {reset_in} seconds.",
                "retry_after": reset_in,
            },
            headers={
                "Retry-After": str(reset_in),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(reset_in),
            },
        )

    # Process request
    response = await call_next(request)

    # Add rate limit headers to response
    response.headers["X-RateLimit-Remaining"] = str(remaining)
    response.headers["X-RateLimit-Reset"] = str(reset_in)

    return response


# 4. Request size limit middleware
@app.middleware("http")
async def request_size_limit_middleware(request: Request, call_next):
    """Reject requests that exceed the configured body size limit."""
    content_length = request.headers.get("content-length")
    if content_length:
        max_bytes = int(settings.MAX_REQUEST_SIZE_MB * 1024 * 1024)
        if int(content_length) > max_bytes:
            return JSONResponse(
                status_code=413,
                content={
                    "error": "Request too large",
                    "detail": f"Request body exceeds {settings.MAX_REQUEST_SIZE_MB}MB limit",
                },
            )
    return await call_next(request)


# 5. Request timing middleware
@app.middleware("http")
async def add_timing_header(request: Request, call_next):
    """Add X-Process-Time header to all responses."""
    start = time.time()
    response = await call_next(request)
    process_time = time.time() - start
    response.headers["X-Process-Time"] = f"{process_time:.4f}"
    return response


# Global exception handler — hide internals in production
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch-all error handler — never expose stack traces in production."""
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
app.include_router(visualize_router, prefix="/api/v1")


# ============================================================================
# ROOT ENDPOINT
# ============================================================================

@app.get("/")
async def root():
    """API root — basic info (no sensitive data)."""
    return {
        "name": "AFDAS",
        "version": settings.APP_VERSION,
        "status": "running",
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
        # Security: limit header/body sizes at server level
        limit_max_requests=10000,
        timeout_keep_alive=5,
    )
