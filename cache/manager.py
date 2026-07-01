"""
Redis cache connection manager.
"""

import redis.asyncio as redis
from typing import Optional

from config.settings import settings
from utils.logger import cache_logger as logger


class CacheManager:
    """
    Manages Redis connection for graph, weight, and route caching.
    Singleton pattern — one connection pool per application.
    """

    _pool: Optional[redis.Redis] = None

    @classmethod
    async def initialize(cls) -> None:
        """Create Redis connection pool."""
        if cls._pool is not None:
            logger.info("Redis already initialized.")
            return

        logger.info(f"Connecting to Redis at {settings.REDIS_HOST}:{settings.REDIS_PORT}")

        # Detect if SSL is required (Upstash, Redis Cloud, etc.)
        use_ssl = getattr(settings, "REDIS_SSL", False)
        # Auto-detect from host (Upstash always needs SSL)
        if "upstash.io" in (settings.REDIS_HOST or ""):
            use_ssl = True

        cls._pool = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            password=settings.REDIS_PASSWORD,
            db=settings.REDIS_DB,
            decode_responses=False,  # Binary data for pickled graphs
            ssl=use_ssl,
            socket_connect_timeout=5,
            socket_timeout=30,
            retry_on_timeout=True,
        )

        # Verify connection
        await cls._pool.ping()
        logger.info("Redis connected successfully.")

    @classmethod
    async def close(cls) -> None:
        """Close Redis connection pool."""
        if cls._pool:
            await cls._pool.close()
            cls._pool = None
            logger.info("Redis connection closed.")

    @classmethod
    def get_client(cls) -> redis.Redis:
        """Get the Redis client."""
        if cls._pool is None:
            raise RuntimeError("Redis not initialized. Call CacheManager.initialize() first.")
        return cls._pool

    @classmethod
    async def health_check(cls) -> dict:
        """Check Redis connectivity."""
        try:
            client = cls.get_client()
            await client.ping()
            info = await client.info("memory")
            return {
                "status": "healthy",
                "used_memory": info.get("used_memory_human", "unknown"),
                "connected_clients": info.get("connected_clients", 0),
            }
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}

    @classmethod
    async def flush_all(cls) -> None:
        """Clear all cached data. Use with caution."""
        client = cls.get_client()
        await client.flushdb()
        logger.warning("Redis flushed — all cached data cleared.")
