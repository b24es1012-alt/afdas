"""
Graph cache — stores serialized base graphs in Redis.
"""

import networkx as nx
import geopandas as gpd
from typing import Optional, Tuple

from cache.manager import CacheManager
from graph.serializer import GraphSerializer
from config.settings import settings
from utils.logger import cache_logger as logger


class GraphCache:
    """
    Caches complete graph bundles (G, G_simple, edges_gdf) in Redis.
    
    Key format: "graph:{event_id}:{place}:{vehicle_type}"
    TTL: configurable (default 24 hours)
    """

    PREFIX = "afdas:graph:"

    def __init__(self):
        self.serializer = GraphSerializer()
        self.ttl = settings.REDIS_GRAPH_TTL

    async def store_full_graph(
        self,
        key: str,
        G: nx.MultiDiGraph,
        G_simple: nx.DiGraph,
        edges_gdf: gpd.GeoDataFrame,
    ) -> None:
        """Store a full graph bundle in Redis."""
        client = CacheManager.get_client()
        data = self.serializer.serialize_full(G, G_simple, edges_gdf)
        await client.setex(f"{self.PREFIX}{key}", self.ttl, data)
        logger.info(f"Stored graph: {key} ({len(data)} bytes, TTL={self.ttl}s)")

    async def get_full_graph(
        self, key: str
    ) -> Optional[Tuple[nx.MultiDiGraph, nx.DiGraph, gpd.GeoDataFrame]]:
        """Retrieve a full graph bundle from Redis."""
        client = CacheManager.get_client()
        data = await client.get(f"{self.PREFIX}{key}")
        if data is None:
            return None
        return self.serializer.deserialize_full(data)

    async def delete(self, key: str) -> None:
        """Delete a specific cached graph."""
        client = CacheManager.get_client()
        await client.delete(f"{self.PREFIX}{key}")
        logger.info(f"Deleted cached graph: {key}")

    async def clear_all(self) -> None:
        """Clear all cached graphs."""
        client = CacheManager.get_client()
        keys = []
        async for key in client.scan_iter(match=f"{self.PREFIX}*"):
            keys.append(key)
        if keys:
            await client.delete(*keys)
            logger.info(f"Cleared {len(keys)} cached graphs")

    async def list_keys(self) -> list:
        """List all cached graph keys."""
        client = CacheManager.get_client()
        keys = []
        async for key in client.scan_iter(match=f"{self.PREFIX}*"):
            keys.append(key.decode() if isinstance(key, bytes) else key)
        return keys

    async def exists(self, key: str) -> bool:
        """Check if a graph is cached."""
        client = CacheManager.get_client()
        return await client.exists(f"{self.PREFIX}{key}") > 0
