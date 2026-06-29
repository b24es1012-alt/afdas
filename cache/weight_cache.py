"""
Weight cache — stores vehicle-specific weight tables in Redis.
Allows quick switching between vehicle types without recomputing from scratch.
"""

import pickle
import zlib
from typing import Optional, Dict

from cache.manager import CacheManager
from config.settings import settings
from utils.logger import cache_logger as logger


class WeightCache:
    """
    Caches vehicle-specific weight arrays.
    
    Key format: "weights:{event_id}:{place}:{vehicle_type}"
    TTL: configurable (default 1 hour — weights change when flood updates)
    
    Stores: dict of {(u, v): weight} for quick edge weight lookup.
    """

    PREFIX = "afdas:weights:"

    def __init__(self):
        self.ttl = settings.REDIS_WEIGHT_TTL

    async def store_weights(
        self, key: str, weights: Dict[tuple, float]
    ) -> None:
        """Store a weight dictionary in Redis."""
        client = CacheManager.get_client()
        data = pickle.dumps(weights, protocol=pickle.HIGHEST_PROTOCOL)
        compressed = zlib.compress(data, 6)
        await client.setex(f"{self.PREFIX}{key}", self.ttl, compressed)
        logger.info(f"Stored weights: {key} ({len(compressed)} bytes)")

    async def get_weights(self, key: str) -> Optional[Dict[tuple, float]]:
        """Retrieve weights from Redis."""
        client = CacheManager.get_client()
        data = await client.get(f"{self.PREFIX}{key}")
        if data is None:
            return None
        raw = zlib.decompress(data)
        return pickle.loads(raw)

    async def delete(self, key: str) -> None:
        """Delete cached weights."""
        client = CacheManager.get_client()
        await client.delete(f"{self.PREFIX}{key}")

    async def clear_all(self) -> None:
        """Clear all cached weights."""
        client = CacheManager.get_client()
        keys = []
        async for key in client.scan_iter(match=f"{self.PREFIX}*"):
            keys.append(key)
        if keys:
            await client.delete(*keys)
            logger.info(f"Cleared {len(keys)} cached weight entries")
