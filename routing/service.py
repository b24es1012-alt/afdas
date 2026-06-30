"""
Routing service — orchestrates path finding and returns structured results.
This is the main interface for computing flood-safe routes.
"""

import networkx as nx
import geopandas as gpd
import osmnx as ox
from typing import List, Optional, Tuple
from pydantic import BaseModel

from routing.astar import astar_path, astar_path_with_cost
from routing.dijkstra import dijkstra_path, yen_k_shortest_paths
from graph.loader import GraphLoader
from graph.validator import GraphValidator
from models.vehicle import get_vehicle_profile, VehicleProfile
from utils.logger import routing_logger as logger
from utils.constants import IMPASSABLE_WEIGHT


class RouteResult(BaseModel):
    """Structured result of a route computation."""

    route_index: int
    nodes: List[int]
    coordinates: List[Tuple[float, float]]  # (lat, lon) pairs
    total_distance_m: float
    estimated_time_s: float
    flooded_segments: int
    total_segments: int
    risk_score: float
    max_flood_depth: float


class RoutingService:
    """
    Main routing service — finds flood-safe routes.
    
    Capabilities:
    - Single best route (A*)
    - K alternative routes (Yen's)
    - Route metrics (distance, time, risk)
    - Route coordinates for frontend display
    """

    def __init__(self, graph_loader: GraphLoader):
        self.graph_loader = graph_loader
        self.validator = GraphValidator()

    async def find_routes(
        self,
        start_lat: float,
        start_lon: float,
        end_lat: float,
        end_lon: float,
        vehicle_type: str = "car",
        k: int = 3,
        place: str = "Gujrat, Punjab, Pakistan",
        flood_shapefile: Optional[str] = None,
        flood_gdf: Optional[gpd.GeoDataFrame] = None,
        event_id: Optional[str] = None,
    ) -> List[RouteResult]:
        """
        Find up to K flood-safe routes between two points.
        
        Args:
            start_lat, start_lon: Origin coordinates
            end_lat, end_lon: Destination coordinates
            vehicle_type: Vehicle type for weight computation
            k: Number of alternative routes
            place: OSM place name for network download
            flood_shapefile: Path to flood data
            flood_gdf: Pre-loaded flood GeoDataFrame
            event_id: Flood event ID
        
        Returns:
            List of RouteResult objects (may be empty if no path)
        """
        # Get the weighted graph
        G, G_simple, edges_gdf = await self.graph_loader.get_weighted_graph(
            place=place,
            vehicle_type=vehicle_type,
            flood_shapefile=flood_shapefile,
            flood_gdf=flood_gdf,
            event_id=event_id,
        )

        vehicle = get_vehicle_profile(vehicle_type)

        # Snap start/end to nearest nodes
        source = ox.distance.nearest_nodes(G, start_lon, start_lat)
        target = ox.distance.nearest_nodes(G, end_lon, end_lat)

        # Validate
        is_valid, message = self.validator.validate_for_routing(G_simple, source, target)
        if not is_valid:
            logger.warning(f"Routing validation failed: {message}")
            # Fallback: route by distance only, ignoring flood weights
            logger.info("Fallback: routing by distance (ignoring flood blocks)...")
            try:
                # Convert MultiDiGraph to simple DiGraph by length for fallback
                G_fallback = nx.DiGraph()
                for u, v, data in G.edges(data=True):
                    length = data.get("length", 1)
                    if not G_fallback.has_edge(u, v) or length < G_fallback[u][v].get("length", float("inf")):
                        G_fallback.add_edge(u, v, **data)
                        G_fallback[u][v]["length"] = length

                fallback_path = nx.shortest_path(G_fallback, source, target, weight="length")
                if fallback_path:
                    result = self._build_route_result(G, G_simple, fallback_path, 0, vehicle)
                    logger.info(f"Fallback route found: {result.total_distance_m:.0f}m, {result.flooded_segments} flooded segments")
                    return [result]
            except (nx.NetworkXNoPath, nx.NodeNotFound) as e:
                logger.warning(f"Fallback also failed: {e}")
            return []

        # Find K paths on a working copy (Yen's modifies the graph)
        G_working = G_simple.copy()
        paths = yen_k_shortest_paths(G_working, source, target, k=k, weight="weight")

        if not paths:
            # Fallback to A*
            single_path = astar_path(G_simple, source, target, weight="weight")
            if single_path:
                paths = [single_path]
            else:
                # Last fallback: try shortest path by length on original graph
                logger.info("A* failed, trying shortest path by length...")
                try:
                    fallback = nx.shortest_path(G, source, target, weight="length")
                    if fallback:
                        paths = [fallback]
                except nx.NetworkXNoPath:
                    logger.warning("No routes found between given coordinates")
                    return []

        # Build route results
        results = []
        for i, path in enumerate(paths):
            result = self._build_route_result(G, G_simple, path, i, vehicle)
            results.append(result)

        logger.info(f"Found {len(results)} route(s) for {vehicle_type}")
        return results

    def _build_route_result(
        self,
        G: nx.MultiDiGraph,
        G_simple: nx.DiGraph,
        path: List[int],
        index: int,
        vehicle: VehicleProfile,
    ) -> RouteResult:
        """Build a RouteResult from a node path."""
        coordinates = []
        total_distance = 0.0
        total_time = 0.0
        flooded_segments = 0
        max_flood_depth = 0.0

        for node in path:
            lat = G.nodes[node].get("y", 0)
            lon = G.nodes[node].get("x", 0)
            coordinates.append((lat, lon))

        for u, v in zip(path[:-1], path[1:]):
            if G_simple.has_edge(u, v):
                edge_data = G_simple[u][v]
                length = edge_data.get("length", 0)
                flood_level = edge_data.get("flood_level", 0)

                total_distance += length
                total_time += length / (vehicle.average_speed * 1000 / 3600)

                if flood_level > 0:
                    flooded_segments += 1
                    max_flood_depth = max(max_flood_depth, flood_level)

        total_segments = len(path) - 1
        risk_score = (
            (flooded_segments / total_segments) * (max_flood_depth / vehicle.max_flood_depth)
            if total_segments > 0 and vehicle.max_flood_depth > 0
            else 0.0
        )
        risk_score = min(risk_score, 1.0)

        return RouteResult(
            route_index=index,
            nodes=path,
            coordinates=coordinates,
            total_distance_m=round(total_distance, 1),
            estimated_time_s=round(total_time, 1),
            flooded_segments=flooded_segments,
            total_segments=total_segments,
            risk_score=round(risk_score, 3),
            max_flood_depth=round(max_flood_depth, 3),
        )
