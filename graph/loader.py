"""
Graph loader — orchestrates graph retrieval from cache or rebuilds if needed.
Separates BASE graph (topology + flood) from VEHICLE weights.

Architecture:
  - Base graph: downloaded ONCE per (place + flood_event), cached in Redis
  - Vehicle weights: computed on-the-fly from cached base graph (fast, no download)
  - Cross-boundary: when points are near city borders, merges adjacent city graphs
"""

import copy
import networkx as nx
import geopandas as gpd
from typing import Tuple, Optional

from graph.builder import GraphBuilder
from graph.weights import WeightEngine
from graph.serializer import GraphSerializer
from graph.border_detector import BorderDetector
from cache.graph_cache import GraphCache
from models.vehicle import VehicleProfile, get_vehicle_profile
from utils.logger import graph_logger as logger


class GraphLoader:
    """
    High-level graph loader.

    Logic:
    1. Check if route crosses city boundaries (border detection)
    2. If cross-boundary → use MultiCityLoader to merge graphs
    3. Else → check Redis for BASE graph (place + flood event, NO vehicle)
    4. If miss → download OSM + annotate flood → cache BASE
    5. Apply vehicle-specific weights to a COPY of base graph
    6. Return ready-to-route graph
    """

    def __init__(self, graph_cache: Optional[GraphCache] = None):
        self.builder = GraphBuilder()
        self.weight_engine = WeightEngine()
        self.serializer = GraphSerializer()
        self.graph_cache = graph_cache
        self.border_detector = BorderDetector()

    async def get_weighted_graph(
        self,
        place: str,
        vehicle_type: str,
        flood_shapefile: Optional[str] = None,
        flood_gdf: Optional[gpd.GeoDataFrame] = None,
        event_id: Optional[str] = None,
        start_lat: Optional[float] = None,
        start_lon: Optional[float] = None,
        end_lat: Optional[float] = None,
        end_lon: Optional[float] = None,
    ) -> Tuple[nx.MultiDiGraph, nx.DiGraph, gpd.GeoDataFrame]:
        """
        Get a weighted graph ready for routing.

        Step 0: Check if cross-boundary routing is needed
        Step 1: Get/build BASE graph (same for all vehicles)
        Step 2: Apply vehicle-specific weights (fast, no download)
        """
        vehicle = get_vehicle_profile(vehicle_type)

        # ── Step 0: Check for cross-boundary routing ─────────────────────
        if start_lat and start_lon and end_lat and end_lon:
            cross_boundary_result = await self._try_cross_boundary(
                start_lat, start_lon, end_lat, end_lon,
                place, vehicle_type, flood_gdf, event_id,
            )
            if cross_boundary_result:
                return cross_boundary_result

        # ── Step 1: Get or build BASE graph (single city) ────────────────
        base_key = f"base:{event_id or 'default'}:{place}"
        G_base, G_simple_base, edges_gdf_base = await self._get_base_graph(
            base_key, place, flood_shapefile, flood_gdf, event_id
        )

        # ── Step 2: Apply vehicle weights to a COPY ──────────────────────
        logger.info(f"Applying {vehicle_type} weights to cached base graph...")
        G = copy.deepcopy(G_base)
        G_simple = copy.deepcopy(G_simple_base)
        edges_gdf = edges_gdf_base.copy()

        G = self.weight_engine.compute_weights_for_graph(G, vehicle)
        G_simple = self.weight_engine.compute_weights_for_simple_graph(G_simple, vehicle)
        edges_gdf = self.weight_engine.compute_weights_for_edges_gdf(edges_gdf, vehicle)

        return G, G_simple, edges_gdf

    async def _try_cross_boundary(
        self,
        start_lat: float,
        start_lon: float,
        end_lat: float,
        end_lon: float,
        place: str,
        vehicle_type: str,
        flood_gdf: Optional[gpd.GeoDataFrame],
        event_id: Optional[str],
    ) -> Optional[Tuple[nx.MultiDiGraph, nx.DiGraph, gpd.GeoDataFrame]]:
        """
        Attempt cross-boundary routing if needed.
        Returns merged weighted graph or None if not needed.
        """
        try:
            from graph.multi_city_loader import MultiCityLoader

            multi_loader = MultiCityLoader(graph_cache=self.graph_cache)
            result = await multi_loader.get_cross_boundary_graph(
                start_lat=start_lat,
                start_lon=start_lon,
                end_lat=end_lat,
                end_lon=end_lon,
                primary_place=place,
                vehicle_type=vehicle_type,
                flood_gdf=flood_gdf,
                event_id=event_id,
            )
            return result
        except Exception as e:
            logger.warning(f"Cross-boundary routing check failed: {e}. Using single city.")
            return None

    async def _get_base_graph(
        self,
        cache_key: str,
        place: str,
        flood_shapefile: Optional[str] = None,
        flood_gdf: Optional[gpd.GeoDataFrame] = None,
        event_id: Optional[str] = None,
    ) -> Tuple[nx.MultiDiGraph, nx.DiGraph, gpd.GeoDataFrame]:
        """
        Get the BASE graph (topology + flood annotation, NO vehicle weights).
        Downloads from OSM only on first call, then cached.
        """
        # Try cache
        if self.graph_cache:
            cached = await self.graph_cache.get_full_graph(cache_key)
            if cached:
                logger.info(f"BASE graph cache HIT: {cache_key}")
                return cached

        logger.info(f"BASE graph cache MISS: {cache_key} — building...")

        # Build base graph (download OSM + annotate flood + save flooded roads to DB)
        G, G_simple, edges_gdf = self.builder.build_from_place(
            place=place,
            flood_shapefile=flood_shapefile,
            flood_gdf=flood_gdf,
            event_id=int(event_id) if event_id else None,
        )

        # Cache the BASE graph (no vehicle weights applied)
        if self.graph_cache:
            await self.graph_cache.store_full_graph(cache_key, G, G_simple, edges_gdf)
            logger.info(f"BASE graph cached: {cache_key}")

        return G, G_simple, edges_gdf

    async def invalidate(
        self,
        place: Optional[str] = None,
        vehicle_type: Optional[str] = None,
        event_id: Optional[str] = None,
    ) -> None:
        """
        Invalidate cached base graph. Called when flood data updates.
        """
        if self.graph_cache:
            if place:
                key = f"base:{event_id or 'default'}:{place}"
                await self.graph_cache.delete(key)
            else:
                await self.graph_cache.clear_all()
            logger.info("Graph cache invalidated")
