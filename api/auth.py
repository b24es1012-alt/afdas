"""
Authentication API endpoints — login, register, refresh token.
Uses PostgreSQL for persistent user storage.
Security: bcrypt password hashing, brute force protection, input validation.
"""

import re
from fastapi import APIRouter, HTTPException, status, Depends, Request
from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from auth.jwt import create_token_pair, verify_token
from auth.middleware import require_admin, CurrentUser
from auth.rate_limiter import BruteForceProtection, RateLimiter
from database.connection import get_db
from config.settings import settings
from utils.logger import api_logger as logger

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ── Password Hashing (bcrypt) ────────────────────────────────────────────────

try:
    import bcrypt

    def _hash_password(password: str) -> str:
        """Hash password using bcrypt (industry standard)."""
        salt = bcrypt.gensalt(rounds=12)
        return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

    def _verify_password(password: str, hashed: str) -> bool:
        """Verify password against bcrypt hash."""
        try:
            return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
        except (ValueError, TypeError):
            return False

except ImportError:
    # Fallback to hashlib if bcrypt not installed (NOT recommended for production)
    import hashlib
    import os

    logger.warning("bcrypt not installed! Using SHA256 fallback. Install bcrypt for production!")

    def _hash_password(password: str) -> str:
        salt = os.urandom(32).hex()
        hashed = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100000).hex()
        return f"{salt}${hashed}"

    def _verify_password(password: str, stored: str) -> bool:
        try:
            salt, hashed = stored.split("$", 1)
            check = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100000).hex()
            return check == hashed
        except (ValueError, TypeError):
            # Fallback for legacy SHA256 hashes (from before this update)
            import hashlib as hl
            return hl.sha256(password.encode()).hexdigest() == stored


# ── Request/Response Models ──────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: str = Field(..., min_length=5, max_length=255)
    password: str = Field(..., min_length=8, max_length=128)
    full_name: Optional[str] = Field(None, max_length=100)

    @validator("email")
    def validate_email(cls, v):
        """Basic email format validation."""
        email_regex = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(email_regex, v):
            raise ValueError("Invalid email format")
        return v.lower().strip()

    @validator("password")
    def validate_password_strength(cls, v):
        """Enforce password complexity requirements."""
        if settings.PASSWORD_REQUIRE_UPPERCASE and not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if settings.PASSWORD_REQUIRE_NUMBER and not re.search(r"\d", v):
            raise ValueError("Password must contain at least one number")
        if len(v) < settings.PASSWORD_MIN_LENGTH:
            raise ValueError(f"Password must be at least {settings.PASSWORD_MIN_LENGTH} characters")
        # Check for common weak passwords
        weak_passwords = {"password", "12345678", "password1", "qwerty123"}
        if v.lower() in weak_passwords:
            raise ValueError("Password is too common. Choose a stronger password.")
        return v

    @validator("full_name")
    def sanitize_name(cls, v):
        """Sanitize full name to prevent injection."""
        if v:
            # Remove any HTML/script tags
            v = re.sub(r"<[^>]+>", "", v)
            # Only allow alphanumeric, spaces, hyphens, apostrophes
            v = re.sub(r"[^\w\s\-'.]", "", v)
            return v.strip()[:100]
        return v


class LoginRequest(BaseModel):
    email: str = Field(..., max_length=255)
    password: str = Field(..., max_length=128)

    @validator("email")
    def normalize_email(cls, v):
        return v.lower().strip()


class RefreshRequest(BaseModel):
    refresh_token: str = Field(..., max_length=2000)


class AuthResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: dict


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/register", response_model=AuthResponse)
async def register(
    request: RegisterRequest,
    raw_request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Register a new user account."""
    email = request.email

    # Check if email already exists
    result = await db.execute(
        text("SELECT id FROM users WHERE email = :email"),
        {"email": email},
    )
    if result.fetchone():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Hash password with bcrypt
    password_hash = _hash_password(request.password)

    # Insert user into database
    result = await db.execute(
        text("""
            INSERT INTO users (email, password_hash, full_name, role, is_active, created_at)
            VALUES (:email, :password_hash, :full_name, 'user', TRUE, NOW())
            RETURNING id
        """),
        {
            "email": email,
            "password_hash": password_hash,
            "full_name": request.full_name or email.split("@")[0],
        },
    )
    user_id = result.scalar_one()
    await db.commit()

    client_ip = RateLimiter.get_client_ip(raw_request)
    logger.info(f"User registered: {email} (id={user_id}) from {client_ip}")

    # Generate tokens
    full_name = request.full_name or email.split("@")[0]
    tokens = create_token_pair(user_id, email, "user")

    return AuthResponse(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        token_type="bearer",
        expires_in=tokens.expires_in,
        user={
            "id": user_id,
            "email": email,
            "full_name": full_name,
            "role": "user",
        },
    )


@router.post("/login", response_model=AuthResponse)
async def login(
    request: LoginRequest,
    raw_request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Login with email and password.
    Protected by brute force detection — locks out after repeated failures.
    """
    client_ip = RateLimiter.get_client_ip(raw_request)
    email = request.email

    # Check brute force lockout (by IP)
    is_locked, remaining = await BruteForceProtection.is_locked_out(client_ip)
    if is_locked:
        logger.warning(f"Login blocked (brute force lockout): {email} from {client_ip}")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many failed login attempts. Try again in {remaining} seconds.",
            headers={"Retry-After": str(remaining)},
        )

    # Also check by email (prevents distributed brute force)
    is_locked_email, remaining_email = await BruteForceProtection.is_locked_out(f"email:{email}")
    if is_locked_email:
        logger.warning(f"Login blocked (email lockout): {email}")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Account temporarily locked. Try again in {remaining_email} seconds.",
            headers={"Retry-After": str(remaining_email)},
        )

    # Find user
    result = await db.execute(
        text("""
            SELECT id, email, password_hash, full_name, role, is_active
            FROM users WHERE email = :email
        """),
        {"email": email},
    )
    row = result.fetchone()

    if not row:
        # Record failed attempt (don't reveal if email exists)
        await BruteForceProtection.record_failed_attempt(client_ip)
        await BruteForceProtection.record_failed_attempt(f"email:{email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    user = dict(row._mapping)

    # Verify password
    if not _verify_password(request.password, user["password_hash"]):
        # Record failed attempt
        attempts, locked = await BruteForceProtection.record_failed_attempt(client_ip)
        await BruteForceProtection.record_failed_attempt(f"email:{email}")
        logger.warning(f"Failed login attempt {attempts}/{settings.LOGIN_MAX_ATTEMPTS}: {email} from {client_ip}")

        if locked:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Account locked after {settings.LOGIN_MAX_ATTEMPTS} failed attempts. "
                       f"Try again in {settings.LOGIN_LOCKOUT_SECONDS // 60} minutes.",
                headers={"Retry-After": str(settings.LOGIN_LOCKOUT_SECONDS)},
            )

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # Check if active
    if not user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated",
        )

    # Successful login — clear brute force counters
    await BruteForceProtection.clear_attempts(client_ip)
    await BruteForceProtection.clear_attempts(f"email:{email}")

    # Update last_login
    await db.execute(
        text("UPDATE users SET last_login = NOW() WHERE id = :id"),
        {"id": user["id"]},
    )
    await db.commit()

    logger.info(f"User logged in: {email} from {client_ip}")

    # Generate tokens
    tokens = create_token_pair(user["id"], user["email"], user["role"])

    return AuthResponse(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        token_type="bearer",
        expires_in=tokens.expires_in,
        user={
            "id": user["id"],
            "email": user["email"],
            "full_name": user["full_name"],
            "role": user["role"],
        },
    )


@router.post("/refresh")
async def refresh_token(request: RefreshRequest, db: AsyncSession = Depends(get_db)):
    """Get a new access token using a refresh token."""
    payload = verify_token(request.refresh_token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
        )

    user_id = int(payload["sub"])

    # Find user in database
    result = await db.execute(
        text("SELECT id, email, full_name, role FROM users WHERE id = :id AND is_active = TRUE"),
        {"id": user_id},
    )
    row = result.fetchone()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or deactivated",
        )

    user = dict(row._mapping)

    # Generate new tokens
    tokens = create_token_pair(user["id"], user["email"], user["role"])

    return {
        "access_token": tokens.access_token,
        "refresh_token": tokens.refresh_token,
        "token_type": "bearer",
        "expires_in": tokens.expires_in,
    }


@router.get("/me")
async def get_current_user_info(
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_admin.__wrapped__ if hasattr(require_admin, '__wrapped__') else None),
):
    """Get current authenticated user's info."""
    from auth.middleware import require_auth
    # This is handled by the dependency
    pass


@router.get("/users")
async def list_users(
    db: AsyncSession = Depends(get_db),
    admin: CurrentUser = Depends(require_admin),
):
    """
    List all registered users.
    ADMIN ONLY — requires admin role.
    """
    result = await db.execute(
        text("""
            SELECT id, email, full_name, role, is_active, created_at, last_login
            FROM users ORDER BY created_at DESC LIMIT 100
        """)
    )
    rows = result.fetchall()
    users = []
    for row in rows:
        r = dict(row._mapping)
        users.append({
            "id": r["id"],
            "email": r["email"],
            "full_name": r["full_name"],
            "role": r["role"],
            "is_active": r["is_active"],
            "created_at": str(r["created_at"]) if r["created_at"] else None,
            "last_login": str(r["last_login"]) if r["last_login"] else None,
        })

    return {"users": users, "count": len(users)}
