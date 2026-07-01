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
        self.flood_ttl = settings.REDIS_GRAPH_FLOOD_TTL

    async def store_full_graph(
        self,
        key: str,
        G: nx.MultiDiGraph,
        G_simple: nx.DiGraph,
        edges_gdf: gpd.GeoDataFrame,
    ) -> None:
        """Store a full graph bundle in Redis with appropriate TTL."""
        client = CacheManager.get_client()
        data = self.serializer.serialize_full(G, G_simple, edges_gdf)

        # Use longer TTL for flood-annotated graphs (they have event IDs, not "default")
        # Key format: "base:{event_id}:{place}" or "merged:{event_id}:{places}"
        # If event_id is NOT "default", it's a flooded graph → keep longer
        is_flooded = "default" not in key
        ttl = self.flood_ttl if is_flooded else self.ttl

        await client.setex(f"{self.PREFIX}{key}", ttl, data)
        logger.info(f"Stored graph: {key} ({len(data)} bytes, TTL={ttl}s {'[FLOOD]' if is_flooded else '[normal]'})")

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

    async def clear_by_region(self, region: str) -> int:
        """
        Clear cached graphs that contain a specific region/place name.
        Only deletes graphs affected by that region, leaves others intact.
        
        Args:
            region: Place name or partial match (e.g. "Delhi", "Mumbai")
            
        Returns:
            Number of keys deleted
        """
        client = CacheManager.get_client()
        keys_to_delete = []

        # Scan for keys containing the region name
        async for key in client.scan_iter(match=f"{self.PREFIX}*"):
            key_str = key.decode() if isinstance(key, bytes) else key
            if region.lower() in key_str.lower():
                keys_to_delete.append(key)

        if keys_to_delete:
            await client.delete(*keys_to_delete)
            logger.info(f"Cleared {len(keys_to_delete)} cached graphs for region '{region}'")

        return len(keys_to_delete)

    async def clear_by_event(self, event_id: str) -> int:
        """
        Clear cached graphs associated with a specific flood event ID.
        
        Args:
            event_id: Flood event ID
            
        Returns:
            Number of keys deleted
        """
        client = CacheManager.get_client()
        keys_to_delete = []

        # Scan for keys containing the event_id
        async for key in client.scan_iter(match=f"{self.PREFIX}*{event_id}*"):
            keys_to_delete.append(key)

        # Also clear merged graphs (they might include flood data)
        async for key in client.scan_iter(match=f"{self.PREFIX}merged:*"):
            keys_to_delete.append(key)

        if keys_to_delete:
            await client.delete(*keys_to_delete)
            logger.info(f"Cleared {len(keys_to_delete)} cached graphs for event '{event_id}'")

        return len(keys_to_delete)

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
