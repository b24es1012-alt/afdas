"""
Graph loader — orchestrates graph retrieval from cache or rebuilds if needed.
Single point of access for getting a ready-to-route graph.
"""

import networkx as nx
import geopandas as gpd
from typing import Tuple, Optional

from graph.builder import GraphBuilder
from graph.weights import WeightEngine
from graph.serializer import GraphSerializer
from cache.graph_cache import GraphCache
from models.vehicle import VehicleProfile, get_vehicle_profile
from utils.logger import graph_logger as logger


class GraphLoader:
    """
    High-level graph loader — the single entry point for routing.
    
    Logic:
    1. Check Redis cache for pre-built weighted graph
    2. If miss → check if base graph exists in cache
    3. If miss → build from scratch (OSM download + flood annotation)
    4. Apply vehicle-specific weights
    5. Cache result
    6. Return ready-to-route graph
    """

    def __init__(self, graph_cache: Optional[GraphCache] = None):
        self.builder = GraphBuilder()
        self.weight_engine = WeightEngine()
        self.serializer = GraphSerializer()
        self.graph_cache = graph_cache

    async def get_weighted_graph(
        self,
        place: str,
        vehicle_type: str,
        flood_shapefile: Optional[str] = None,
        flood_gdf: Optional[gpd.GeoDataFrame] = None,
        event_id: Optional[str] = None,
    ) -> Tuple[nx.MultiDiGraph, nx.DiGraph, gpd.GeoDataFrame]:
        """
        Get a weighted graph ready for routing.
        
        Args:
            place: OSM place name
            vehicle_type: Vehicle type string
            flood_shapefile: Path to flood data (optional)
            flood_gdf: Pre-loaded flood GeoDataFrame (optional)
            event_id: Flood event ID for cache key
        
        Returns:
            (G_multi, G_simple, edges_gdf) with weights applied
        """
        vehicle = get_vehicle_profile(vehicle_type)
        cache_key = f"{event_id or 'default'}:{place}:{vehicle_type}"

        # Try cache first
        if self.graph_cache:
            cached = await self.graph_cache.get_full_graph(cache_key)
            if cached:
                logger.info(f"Cache HIT for graph: {cache_key}")
                return cached

        logger.info(f"Cache MISS for graph: {cache_key} — building...")

        # Build the base graph
        G, G_simple, edges_gdf = self.builder.build_from_place(
            place=place,
            flood_shapefile=flood_shapefile,
            flood_gdf=flood_gdf,
        )

        # Apply vehicle-specific weights
        G = self.weight_engine.compute_weights_for_graph(G, vehicle)
        G_simple = self.weight_engine.compute_weights_for_simple_graph(G_simple, vehicle)
        edges_gdf = self.weight_engine.compute_weights_for_edges_gdf(edges_gdf, vehicle)

        # Cache the result
        if self.graph_cache:
            await self.graph_cache.store_full_graph(cache_key, G, G_simple, edges_gdf)
            logger.info(f"Cached graph: {cache_key}")

        return G, G_simple, edges_gdf

    async def invalidate(
        self,
        place: Optional[str] = None,
        vehicle_type: Optional[str] = None,
        event_id: Optional[str] = None,
    ) -> None:
        """
        Invalidate cached graphs. Called when flood data updates.
        
        Args:
            place: Invalidate for specific place (or all if None)
            vehicle_type: Invalidate for specific vehicle (or all if None)
            event_id: Specific event context
        """
        if self.graph_cache:
            if place and vehicle_type:
                key = f"{event_id or 'default'}:{place}:{vehicle_type}"
                await self.graph_cache.delete(key)
            else:
                await self.graph_cache.clear_all()
            logger.info("Graph cache invalidated")
