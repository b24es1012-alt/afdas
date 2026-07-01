"""
Security headers middleware for FastAPI.

Adds standard security headers to all responses to protect against
common web vulnerabilities (XSS, clickjacking, MIME sniffing, etc.).
"""

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from config.environment import is_production


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Adds security headers to all HTTP responses.

    Headers applied:
    - X-Content-Type-Options: nosniff (prevents MIME sniffing)
    - X-Frame-Options: DENY (prevents clickjacking)
    - X-XSS-Protection: 0 (use CSP instead, avoid quirks)
    - Strict-Transport-Security (HSTS in production)
    - Content-Security-Policy (restrict resource loading)
    - Referrer-Policy: strict-origin-when-cross-origin
    - Permissions-Policy: restrict browser features
    - Cache-Control: no-store for API responses
    """

    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)

        # ── Always-on headers ─────────────────────────────────────────
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "0"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(self), "
            "payment=(), usb=(), magnetometer=()"
        )

        # Prevent caching of API responses (contains sensitive data)
        if "/api/" in str(request.url.path):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
            response.headers["Pragma"] = "no-cache"

        # ── Production-only headers ───────────────────────────────────
        if is_production():
            # HSTS: force HTTPS for 1 year, include subdomains
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )
            # Strict CSP for production
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https://*.tile.openstreetmap.org; "
                "connect-src 'self' https://nominatim.openstreetmap.org; "
                "frame-ancestors 'none';"
            )
        else:
            # Relaxed CSP for development
            response.headers["Content-Security-Policy"] = (
                "default-src 'self' http://localhost:*; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src * data:; "
                "connect-src *; "
                "frame-ancestors 'self';"
            )

        # Remove server identification header
        if "server" in response.headers:
            del response.headers["server"]

        return response
