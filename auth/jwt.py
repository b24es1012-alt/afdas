"""
JWT token creation and verification.
"""

from datetime import datetime, timedelta
from typing import Optional
import jwt as pyjwt
from pydantic import BaseModel

from config.settings import settings
from utils.logger import logger


class TokenData(BaseModel):
    """Data encoded in a JWT token."""
    user_id: int
    email: str
    role: str = "user"
    exp: Optional[datetime] = None


class TokenPair(BaseModel):
    """Access + refresh token pair."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


def create_access_token(user_id: int, email: str, role: str = "user") -> str:
    """
    Create a JWT access token.
    
    Args:
        user_id: User's database ID
        email: User's email
        role: User role (user, admin, responder)
    
    Returns:
        Encoded JWT string
    """
    expires = datetime.utcnow() + timedelta(minutes=settings.JWT_EXPIRY_MINUTES)
    payload = {
        "sub": str(user_id),
        "email": email,
        "role": role,
        "exp": expires,
        "iat": datetime.utcnow(),
        "type": "access",
    }
    return pyjwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(user_id: int) -> str:
    """Create a longer-lived refresh token."""
    expires = datetime.utcnow() + timedelta(days=7)
    payload = {
        "sub": str(user_id),
        "exp": expires,
        "iat": datetime.utcnow(),
        "type": "refresh",
    }
    return pyjwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_token_pair(user_id: int, email: str, role: str = "user") -> TokenPair:
    """Create both access and refresh tokens."""
    return TokenPair(
        access_token=create_access_token(user_id, email, role),
        refresh_token=create_refresh_token(user_id),
        expires_in=settings.JWT_EXPIRY_MINUTES * 60,
    )


def verify_token(token: str) -> Optional[dict]:
    """
    Verify and decode a JWT token.
    
    Returns:
        Decoded payload dict, or None if invalid/expired
    """
    try:
        payload = pyjwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        return payload
    except pyjwt.ExpiredSignatureError:
        logger.warning("Token expired")
        return None
    except pyjwt.InvalidTokenError as e:
        logger.warning(f"Invalid token: {e}")
        return None
