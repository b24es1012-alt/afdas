"""
PostgreSQL/PostGIS connection management.
Provides async connection pool, health checks, and session lifecycle.
"""

from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
    AsyncEngine,
)
from sqlalchemy import text
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from config.settings import settings
from utils.logger import logger


class DatabaseManager:
    """
    Manages the PostgreSQL/PostGIS connection pool.
    Singleton pattern — one engine per application lifecycle.
    """

    _engine: Optional[AsyncEngine] = None
    _session_factory: Optional[async_sessionmaker] = None

    @classmethod
    async def initialize(cls) -> None:
        """Create the async engine and session factory."""
        if cls._engine is not None:
            logger.info("Database engine already initialized.")
            return

        logger.info(f"Connecting to PostgreSQL at {settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}")

        cls._engine = create_async_engine(
            settings.DATABASE_URL,
            pool_size=settings.DB_POOL_MIN,
            max_overflow=settings.DB_POOL_MAX - settings.DB_POOL_MIN,
            pool_pre_ping=True,
            pool_recycle=3600,
            echo=settings.DEBUG,
        )

        cls._session_factory = async_sessionmaker(
            bind=cls._engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

        # Verify connection and PostGIS availability
        async with cls._engine.begin() as conn:
            result = await conn.execute(text("SELECT PostGIS_Version();"))
            postgis_version = result.scalar()
            logger.info(f"PostGIS connected — version: {postgis_version}")

    @classmethod
    async def close(cls) -> None:
        """Dispose of the connection pool."""
        if cls._engine:
            await cls._engine.dispose()
            cls._engine = None
            cls._session_factory = None
            logger.info("Database connection pool closed.")

    @classmethod
    def get_engine(cls) -> AsyncEngine:
        """Get the current async engine."""
        if cls._engine is None:
            raise RuntimeError("Database not initialized. Call DatabaseManager.initialize() first.")
        return cls._engine

    @classmethod
    @asynccontextmanager
    async def session(cls) -> AsyncGenerator[AsyncSession, None]:
        """Context manager for a database session with automatic rollback on error."""
        if cls._session_factory is None:
            raise RuntimeError("Database not initialized. Call DatabaseManager.initialize() first.")

        async with cls._session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    @classmethod
    async def get_session(cls) -> AsyncGenerator[AsyncSession, None]:
        """FastAPI dependency — yields an async session."""
        if cls._session_factory is None:
            raise RuntimeError("Database not initialized.")

        async with cls._session_factory() as session:
            try:
                yield session
            finally:
                await session.close()

    @classmethod
    async def health_check(cls) -> dict:
        """Check database connectivity and PostGIS availability."""
        try:
            async with cls.session() as session:
                # Basic connectivity
                result = await session.execute(text("SELECT 1"))
                result.scalar()

                # PostGIS check
                result = await session.execute(text("SELECT PostGIS_Version();"))
                postgis_ver = result.scalar()

                # Pool stats
                pool = cls._engine.pool
                return {
                    "status": "healthy",
                    "postgis_version": postgis_ver,
                    "pool_size": pool.size(),
                    "pool_checked_out": pool.checkedout(),
                    "pool_overflow": pool.overflow(),
                }
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}


# FastAPI dependency shortcut
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency injection for FastAPI routes."""
    async for session in DatabaseManager.get_session():
        yield session
