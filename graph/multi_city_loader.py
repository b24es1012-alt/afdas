"""
Multi-city graph loader — downloads and merges road networks from multiple cities.

When a route crosses city boundaries (detected by BorderDetector), this module:
1. Downloads the road network for each relevant city
2. Merges them into a single unified graph
3. Caches the merged result for future use

The merged graph allows routing across city boundaries seamlessly.
"""

import networkx as nx
import geopandas as gpd
import osmnx as ox
import pandas as pd
from typing import List, Dict, Tuple, Optional

from graph.builder import GraphBuilder
from graph.border_detector import BorderDetector
from graph.weights import WeightEngine
from graph.serializer import GraphSerializer
from cache.graph_cache import GraphCache
from models.vehicle import get_vehicle_profile
from osm.downloader import OSMDownloader
from config.settings import settings
from utils.logger import graph_logger as logger


class MultiCityLoader:
    """
    Loads and merges road networks from multiple cities for cross-boundary routing.

    Architecture:
        - Each city graph is downloaded and cached independently (reuses existing cache)
        - Merged graph is built by composing individual city graphs
        - The merged graph gets its own cache key for fast retrieval
        - Flood annotation is applied to the merged graph

    Performance:
        - Individual city graphs are cached → if a city is already cached, no re-download
        - Merged graph is cached separately → subsequent cross-boundary routes are instant
        - Only downloads cities that are actually needed (detected by BorderDetector)
    """

    def __init__(self, graph_cache: Optional[GraphCache] = None):
        self.builder = GraphBuilder()
        self.weight_engine = WeightEngine()
        self.serializer = GraphSerializer()
        self.graph_cache = graph_cache
        self.border_detector = BorderDetector()
        self.osm_downloader = OSMDownloader()

    async def get_cross_boundary_graph(
        self,
        start_lat: float,
        start_lon: float,
        end_lat: float,
        end_lon: float,
        primary_place: str,
        vehicle_type: str,
        flood_gdf: Optional[gpd.GeoDataFrame] = None,
        event_id: Optional[str] = None,
    ) -> Optional[Tuple[nx.MultiDiGraph, nx.DiGraph, gpd.GeoDataFrame]]:
        """
        Check if cross-boundary routing is needed and return merged graph if so.

        Args:
            start_lat, start_lon: Origin
            end_lat, end_lon: Destination
            primary_place: Main city/place name
            vehicle_type: Vehicle type for weight computation
            flood_gdf: Flood zones (applied to all cities)
            event_id: Flood event ID

        Returns:
            (G_merged, G_simple_merged, edges_gdf_merged) or None if not needed
        """
        # Detect if cross-boundary routing is needed
        additional_cities = self.border_detector.detect_cross_city_route(
            start_lat, start_lon, end_lat, end_lon, primary_place
        )

        if not additional_cities:
            logger.debug("No neighboring cities found for this area — using single city graph")
            return None

        logger.info(
            f"Multi-city routing: downloading {len(additional_cities)} neighboring area(s) "
            f"for '{primary_place}': {[c['name'] for c in additional_cities]}"
        )

        # Build cache key for merged graph
        city_names = sorted([primary_place] + [c["place"] or c["name"] for c in additional_cities])
        merged_key = f"merged:{event_id or 'default'}:{'+'.join(city_names)}"

        # Check merged graph cache
        if self.graph_cache:
            cached = await self.graph_cache.get_full_graph(merged_key)
            if cached:
                logger.info(f"Merged graph cache HIT: {merged_key}")
                G_merged, G_simple_merged, edges_gdf_merged = cached
                # Apply vehicle weights
                vehicle = get_vehicle_profile(vehicle_type)
                import copy
                G = copy.deepcopy(G_merged)
                G_simple = copy.deepcopy(G_simple_merged)
                edges_gdf = edges_gdf_merged.copy()
                G = self.weight_engine.compute_weights_for_graph(G, vehicle)
                G_simple = self.weight_engine.compute_weights_for_simple_graph(G_simple, vehicle)
                edges_gdf = self.weight_engine.compute_weights_for_edges_gdf(edges_gdf, vehicle)
                return G, G_simple, edges_gdf

        # Download and merge graphs
        try:
            G_merged, G_simple_merged, edges_gdf_merged = await self._build_merged_graph(
                primary_place=primary_place,
                additional_cities=additional_cities,
                flood_gdf=flood_gdf,
                event_id=event_id,
            )

            # Cache the merged base graph
            if self.graph_cache:
                await self.graph_cache.store_full_graph(
                    merged_key, G_merged, G_simple_merged, edges_gdf_merged
                )
                logger.info(f"Merged graph cached: {merged_key}")

            # Apply vehicle weights
            vehicle = get_vehicle_profile(vehicle_type)
            import copy
            G = copy.deepcopy(G_merged)
            G_simple = copy.deepcopy(G_simple_merged)
            edges_gdf = edges_gdf_merged.copy()
            G = self.weight_engine.compute_weights_for_graph(G, vehicle)
            G_simple = self.weight_engine.compute_weights_for_simple_graph(G_simple, vehicle)
            edges_gdf = self.weight_engine.compute_weights_for_edges_gdf(edges_gdf, vehicle)

            return G, G_simple, edges_gdf

        except Exception as e:
            logger.warning(f"Multi-city graph build failed: {e}. Falling back to single city.")
            return None

    async def _build_merged_graph(
        self,
        primary_place: str,
        additional_cities: List[Dict],
        flood_gdf: Optional[gpd.GeoDataFrame] = None,
        event_id: Optional[str] = None,
    ) -> Tuple[nx.MultiDiGraph, nx.DiGraph, gpd.GeoDataFrame]:
        """
        Build a merged graph from primary city + additional neighboring cities.
        """
        all_graphs: List[nx.MultiDiGraph] = []

        # Download primary city graph
        logger.info(f"Downloading primary city graph: {primary_place}")
        try:
            G_primary = self.osm_downloader.download_road_network(primary_place)
            all_graphs.append(G_primary)
        except Exception as e:
            logger.error(f"Failed to download primary city {primary_place}: {e}")
            raise

        # Download additional city graphs
        for city_info in additional_cities:
            try:
                if city_info.get("place"):
                    # Named place — download by place name
                    logger.info(f"Downloading neighbor: {city_info['name']} ({city_info['place']})")
                    G_city = self.osm_downloader.download_road_network(city_info["place"])
                else:
                    # Dynamic point-based download (for unknown cities)
                    lat = city_info["lat"]
                    lon = city_info["lon"]
                    radius = city_info.get("radius_m", 10000)
                    logger.info(f"Downloading area around ({lat:.3f}, {lon:.3f}), radius={radius}m")
                    G_city = self.osm_downloader.download_road_network_point(lat, lon, radius)

                all_graphs.append(G_city)
                logger.info(f"  → {G_city.number_of_nodes()} nodes, {G_city.number_of_edges()} edges")

            except Exception as e:
                logger.warning(f"Failed to download {city_info['name']}: {e} (skipping)")
                continue

        if len(all_graphs) < 2:
            logger.warning("Only primary city downloaded — no merge needed")
            # Fall back to single city build
            return self.builder.build_from_place(
                place=primary_place,
                flood_gdf=flood_gdf,
                event_id=int(event_id) if event_id else None,
            )

        # Merge all graphs into one
        G_merged = self._merge_graphs(all_graphs)

        logger.info(
            f"Merged graph: {G_merged.number_of_nodes()} nodes, "
            f"{G_merged.number_of_edges()} edges "
            f"(from {len(all_graphs)} city graphs)"
        )

        # Convert to GeoDataFrames
        from osm.graph_converter import GraphConverter
        converter = GraphConverter()
        nodes_gdf, edges_gdf = converter.graph_to_gdfs(G_merged)

        # Annotate with flood data
        if flood_gdf is not None:
            edges_gdf = self.builder._annotate_flood(edges_gdf, flood_gdf)
        else:
            edges_gdf["flood_level"] = 0.0

        # Write flood_level back into the graph
        for (u, v, key), row in edges_gdf.iterrows():
            if key in G_merged[u][v]:
                G_merged[u][v][key]["flood_level"] = row.get("flood_level", 0.0)

        # Create simplified DiGraph
        G_simple = converter.simplify_graph(G_merged)

        return G_merged, G_simple, edges_gdf

    def _merge_graphs(self, graphs: List[nx.MultiDiGraph]) -> nx.MultiDiGraph:
        """
        Merge multiple city graphs into one unified graph.

        OSMnx graphs use OSM node IDs as node identifiers, which are globally unique.
        This means graphs from adjacent cities will naturally share border nodes,
        creating seamless connectivity at boundaries.
        """
        if len(graphs) == 1:
            return graphs[0]

        # Use nx.compose for merging — shared nodes (same OSM ID) are merged automatically
        G_merged = graphs[0].copy()

        for G_additional in graphs[1:]:
            # nx.compose merges nodes and edges. Nodes with same ID are unified.
            G_merged = nx.compose(G_merged, G_additional)

        # Verify connectivity improvement
        nodes_before = graphs[0].number_of_nodes()
        nodes_after = G_merged.number_of_nodes()
        edges_before = graphs[0].number_of_edges()
        edges_after = G_merged.number_of_edges()

        logger.info(
            f"Graph merge result: {nodes_before}→{nodes_after} nodes, "
            f"{edges_before}→{edges_after} edges "
            f"(+{nodes_after - nodes_before} new nodes, +{edges_after - edges_before} new edges)"
        )

        return G_merged

    async def list_available_neighbors(self, place: str) -> List[Dict[str, str]]:
        """
        List all known neighboring cities for a given place.
        Useful for frontend UI showing expandable coverage.
        """
        from graph.border_detector import CITY_NEIGHBORS
        neighbors = CITY_NEIGHBORS.get(place, [])
        return [
            {"name": n["name"], "place": n["place"], "direction": n["direction"]}
            for n in neighbors
        ]
