"""
AFDAS Global Settings
Loads all configuration from environment variables with sensible defaults.
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional


class Settings(BaseSettings):
    """Application-wide settings loaded from .env or environment."""

    # ── Application ──────────────────────────────────────────────────────
    APP_NAME: str = "AFDAS"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # ── PostgreSQL / PostGIS ─────────────────────────────────────────────
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "afdas"
    DB_USER: str = "afdas_user"
    DB_PASSWORD: str = "afdas_password"
    DB_POOL_MIN: int = 5
    DB_POOL_MAX: int = 20

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    @property
    def DATABASE_URL_SYNC(self) -> str:
        return (
            f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    # ── Redis Cache ──────────────────────────────────────────────────────
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: Optional[str] = None
    REDIS_DB: int = 0
    REDIS_GRAPH_TTL: int = 21600         # 6 hours — non-flooded city graphs expire after this
    REDIS_GRAPH_FLOOD_TTL: int = 86400   # 24 hours — flooded city graphs stay longer (important data)
    REDIS_WEIGHT_TTL: int = 3600       # 1 hour
    REDIS_ROUTE_TTL: int = 1800        # 30 minutes
    REDIS_SESSION_TTL: int = 3600      # 1 hour — chat session memory expiry

    @property
    def REDIS_URL(self) -> str:
        auth = f":{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
        return f"redis://{auth}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    # ── Copernicus EMS ───────────────────────────────────────────────────
    COPERNICUS_API_URL: str = "https://emergency.copernicus.eu/mapping/list-of-components"
    COPERNICUS_DOWNLOAD_BASE: str = "https://emergency.copernicus.eu/mapping/download"
    COPERNICUS_POLL_INTERVAL: int = 300  # seconds (5 minutes)
    COPERNICUS_WATCH_COUNTRIES: str = "India"  # Comma-separated countries to auto-monitor
    COPERNICUS_AUTO_IMPORT: bool = True  # Enable/disable automatic flood import

    # ── OpenStreetMap ────────────────────────────────────────────────────
    OSM_NOMINATIM_URL: str = "https://nominatim.openstreetmap.org"
    OSM_USER_AGENT: str = "AFDAS-FloodNavigation/1.0"
    OSM_RATE_LIMIT: float = 1.0  # seconds between requests

    # ── AI / LLM ────────────────────────────────────────────────────────
    GROQ_API_KEY: str = ""
    LLM_MODEL: str = "llama-3.3-70b-versatile"
    LLM_TEMPERATURE: float = 0.0
    LLM_MAX_TOKENS: int = 4096

    # ── JWT Authentication ───────────────────────────────────────────────
    JWT_SECRET_KEY: str = "afdas-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRY_MINUTES: int = 1440  # 24 hours

    # ── Security ─────────────────────────────────────────────────────────
    # Rate limiting
    RATE_LIMIT_REQUESTS: int = 60          # Max requests per window
    RATE_LIMIT_WINDOW_SECONDS: int = 60    # Window size in seconds
    RATE_LIMIT_AUTH_REQUESTS: int = 5      # Max login/register attempts per window
    RATE_LIMIT_AUTH_WINDOW: int = 300      # Auth rate limit window (5 min)
    RATE_LIMIT_CHAT_REQUESTS: int = 20     # Max AI chat requests per window
    RATE_LIMIT_CHAT_WINDOW: int = 60       # Chat rate limit window (1 min)

    # Brute force protection
    LOGIN_MAX_ATTEMPTS: int = 5            # Max failed login attempts before lockout
    LOGIN_LOCKOUT_SECONDS: int = 900       # Lockout duration (15 min)

    # Request limits
    MAX_REQUEST_SIZE_MB: float = 10.0      # Max request body size in MB

    # Password requirements
    PASSWORD_MIN_LENGTH: int = 8
    PASSWORD_REQUIRE_UPPERCASE: bool = True
    PASSWORD_REQUIRE_NUMBER: bool = True

    # ── Routing ──────────────────────────────────────────────────────────
    MAX_ROUTES: int = 3
    DEFAULT_VEHICLE: str = "car"
    REROUTE_CHECK_INTERVAL: int = 30  # seconds
    NEARBY_CITY_RADIUS_KM: float = 20.0  # Radius to include neighboring cities for route optimization
    BORDER_THRESHOLD_KM: float = 5.0     # If user is within this distance of city boundary, show border indicator on frontend

    # ── Monitoring ───────────────────────────────────────────────────────
    GPS_UPDATE_INTERVAL: int = 15  # seconds
    FLOOD_ALERT_RADIUS_KM: float = 5.0

    # ── Data Paths ───────────────────────────────────────────────────────
    DATA_DIR: str = "./data"
    FLOOD_DATA_DIR: str = "./data/flood"
    OSM_DATA_DIR: str = "./data/osm"
    GRAPH_DATA_DIR: str = "./data/graphs"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# Singleton instance
settings = Settings()
