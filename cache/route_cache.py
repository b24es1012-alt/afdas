"""
Route cache — caches frequently requested routes.
"""

import json
import hashlib
from typing import Optional, List

from cache.manager import CacheManager
from config.settings import settings
from utils.logger import cache_logger as logger


class RouteCache:
    """
    Caches computed routes for repeated requests.
    
    Key: hash of (start, end, vehicle_type, event_id)
    TTL: short-lived (default 30 minutes) — routes become invalid as flood changes
    """

    PREFIX = "afdas:route:"

    def __init__(self):
        self.ttl = settings.REDIS_ROUTE_TTL

    def _make_key(
        self,
        start_lat: float,
        start_lon: float,
        end_lat: float,
        end_lon: float,
        vehicle_type: str,
        event_id: str = "default",
    ) -> str:
        """Generate a deterministic cache key from route parameters."""
        raw = f"{start_lat:.5f},{start_lon:.5f},{end_lat:.5f},{end_lon:.5f},{vehicle_type},{event_id}"
        key_hash = hashlib.md5(raw.encode()).hexdigest()[:16]
        return key_hash

    async def store_route(
        self,
        start_lat: float,
        start_lon: float,
        end_lat: float,
        end_lon: float,
        vehicle_type: str,
        routes_json: str,
        event_id: str = "default",
    ) -> None:
        """Cache a route result."""
        client = CacheManager.get_client()
        key = self._make_key(start_lat, start_lon, end_lat, end_lon, vehicle_type, event_id)
        await client.setex(
            f"{self.PREFIX}{key}",
            self.ttl,
            routes_json.encode(),
        )

    async def get_route(
        self,
        start_lat: float,
        start_lon: float,
        end_lat: float,
        end_lon: float,
        vehicle_type: str,
        event_id: str = "default",
    ) -> Optional[str]:
        """Retrieve a cached route. Returns JSON string or None."""
        client = CacheManager.get_client()
        key = self._make_key(start_lat, start_lon, end_lat, end_lon, vehicle_type, event_id)
        data = await client.get(f"{self.PREFIX}{key}")
        if data:
            return data.decode()
        return None

    async def invalidate_all(self) -> None:
        """Clear all cached routes (called when flood data updates)."""
        client = CacheManager.get_client()
        keys = []
        async for key in client.scan_iter(match=f"{self.PREFIX}*"):
            keys.append(key)
        if keys:
            await client.delete(*keys)
            logger.info(f"Invalidated {len(keys)} cached routes")
