"""
Authentication API endpoints — login, register, refresh token.
Uses PostgreSQL for persistent user storage.
"""

from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
import hashlib

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from auth.jwt import create_token_pair, verify_token
from database.connection import get_db
from utils.logger import api_logger as logger

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ── Helpers ──────────────────────────────────────────────────────────────────

def _hash_password(password: str) -> str:
    """Hash password. Use bcrypt in production."""
    return hashlib.sha256(password.encode()).hexdigest()


def _verify_password(password: str, hashed: str) -> bool:
    return _hash_password(password) == hashed


# ── Request/Response Models ──────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: str = Field(..., min_length=5, max_length=255)
    password: str = Field(..., min_length=6, max_length=128)
    full_name: Optional[str] = None


class LoginRequest(BaseModel):
    email: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class AuthResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: dict


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/register", response_model=AuthResponse)
async def register(request: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """Register a new user account. Saves to PostgreSQL."""

    email = request.email.lower().strip()

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

    # Insert user into database
    result = await db.execute(
        text("""
            INSERT INTO users (email, password_hash, full_name, role, is_active, created_at)
            VALUES (:email, :password_hash, :full_name, 'user', TRUE, NOW())
            RETURNING id
        """),
        {
            "email": email,
            "password_hash": _hash_password(request.password),
            "full_name": request.full_name or email.split("@")[0],
        },
    )
    user_id = result.scalar_one()
    await db.commit()

    logger.info(f"User registered: {email} (id={user_id})")

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
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Login with email and password. Reads from PostgreSQL."""

    email = request.email.lower().strip()

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
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    user = dict(row._mapping)

    # Verify password
    if not _verify_password(request.password, user["password_hash"]):
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

    # Update last_login
    await db.execute(
        text("UPDATE users SET last_login = NOW() WHERE id = :id"),
        {"id": user["id"]},
    )
    await db.commit()

    logger.info(f"User logged in: {email}")

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
            detail="User not found",
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


@router.get("/users")
async def list_users(db: AsyncSession = Depends(get_db)):
    """List all registered users (for debugging/admin)."""

    result = await db.execute(
        text("SELECT id, email, full_name, role, is_active, created_at, last_login FROM users ORDER BY id")
    )
    users = [dict(row._mapping) for row in result.fetchall()]

    return {"users": users, "count": len(users)}
