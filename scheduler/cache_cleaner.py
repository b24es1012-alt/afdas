"""
Cache cleaner job — removes expired and stale cache entries.
"""

from cache.manager import CacheManager
from cache.graph_cache import GraphCache
from cache.weight_cache import WeightCache
from cache.route_cache import RouteCache
from utils.logger import scheduler_logger as logger


class CacheCleanerJob:
    """
    Periodic cache maintenance.
    
    Tasks:
    - Remove expired route caches
    - Clean orphaned graph entries
    - Log cache statistics
    """

    def __init__(self):
        self.graph_cache = GraphCache()
        self.weight_cache = WeightCache()
        self.route_cache = RouteCache()

    async def run(self) -> dict:
        """Execute cache cleanup."""
        logger.info("Cache cleaner job started")
        results = {"graphs_cleared": 0, "routes_cleared": 0}

        try:
            # Redis handles TTL-based expiration automatically
            # This job logs stats and handles edge cases

            client = CacheManager.get_client()
            info = await client.info("memory")

            logger.info(
                f"Redis memory: {info.get('used_memory_human', 'unknown')} | "
                f"Keys: {info.get('db0', {})}"
            )

            # List active graph keys
            graph_keys = await self.graph_cache.list_keys()
            logger.info(f"Active graph cache entries: {len(graph_keys)}")

            results["active_graphs"] = len(graph_keys)
            results["memory_used"] = info.get("used_memory_human", "unknown")

        except Exception as e:
            logger.error(f"Cache cleaner error: {e}")
            results["error"] = str(e)

        return results

    async def force_clear_all(self) -> dict:
        """Force clear all caches (use after flood data update)."""
        logger.warning("Force clearing ALL caches")

        await self.graph_cache.clear_all()
        await self.weight_cache.clear_all()
        await self.route_cache.invalidate_all()

        return {"status": "all_caches_cleared"}
