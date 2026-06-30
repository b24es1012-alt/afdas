"""
Authentication API endpoints — login, register, refresh token.
"""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field, EmailStr
from typing import Optional
from datetime import datetime
import hashlib

from auth.jwt import create_token_pair, verify_token
from utils.logger import api_logger as logger

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ── In-memory user store (replace with PostgreSQL in production) ──────────────
# This allows testing without a database connection
_users_db = {}  # email → { id, email, password_hash, full_name, role, created_at }
_user_counter = 0


def _hash_password(password: str) -> str:
    """Simple hash for demo. Use bcrypt/passlib in production."""
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
async def register(request: RegisterRequest):
    """Register a new user account."""
    global _user_counter

    # Check if email already exists
    if request.email.lower() in _users_db:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Create user
    _user_counter += 1
    user_id = _user_counter

    user = {
        "id": user_id,
        "email": request.email.lower(),
        "password_hash": _hash_password(request.password),
        "full_name": request.full_name or request.email.split("@")[0],
        "role": "user",
        "is_active": True,
        "created_at": datetime.utcnow().isoformat(),
    }

    _users_db[request.email.lower()] = user
    logger.info(f"User registered: {request.email} (id={user_id})")

    # Generate tokens
    tokens = create_token_pair(user_id, user["email"], user["role"])

    return AuthResponse(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        token_type="bearer",
        expires_in=tokens.expires_in,
        user={
            "id": user_id,
            "email": user["email"],
            "full_name": user["full_name"],
            "role": user["role"],
        },
    )


@router.post("/login", response_model=AuthResponse)
async def login(request: LoginRequest):
    """Login with email and password."""
    email = request.email.lower()

    # Find user
    user = _users_db.get(email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

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
async def refresh_token(request: RefreshRequest):
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

    # Find user by ID
    user = next((u for u in _users_db.values() if u["id"] == user_id), None)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    # Generate new tokens
    tokens = create_token_pair(user["id"], user["email"], user["role"])

    return {
        "access_token": tokens.access_token,
        "refresh_token": tokens.refresh_token,
        "token_type": "bearer",
        "expires_in": tokens.expires_in,
    }


@router.get("/me")
async def get_current_user_info():
    """Get current user info (requires auth header)."""
    # This would normally use Depends(require_auth)
    # For now, return info about the endpoint
    return {"message": "Send Authorization: Bearer <token> header to get user info"}
