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
            logger.info("Fallback: routing by distance (ignoring flood blocks)...")
            try:
                # Build clean DiGraph ignoring flood weights
                G_fallback = nx.DiGraph()
                for u, v, data in G.edges(data=True):
                    length = data.get("length", 1)
                    if not G_fallback.has_edge(u, v) or length < G_fallback[u][v].get("length", float("inf")):
                        G_fallback.add_edge(u, v, length=length, flood_level=data.get("flood_level", 0))

                # Copy node attributes (coordinates)
                for node, attrs in G.nodes(data=True):
                    if node in G_fallback:
                        G_fallback.nodes[node].update(attrs)

                logger.info(f"Fallback graph: {G_fallback.number_of_nodes()} nodes, {G_fallback.number_of_edges()} edges")
                logger.info(f"Source: {source}, Target: {target}, Source in graph: {source in G_fallback}, Target in graph: {target in G_fallback}")

                fallback_path = nx.shortest_path(G_fallback, source, target, weight="length")
                logger.info(f"Fallback path found: {len(fallback_path)} nodes")

                # Build result using fallback graph
                coordinates = []
                total_distance = 0.0
                flooded_segments = 0
                for node in fallback_path:
                    lat = G.nodes[node].get("y", 0)
                    lon = G.nodes[node].get("x", 0)
                    coordinates.append((lat, lon))
                for u, v in zip(fallback_path[:-1], fallback_path[1:]):
                    if G_fallback.has_edge(u, v):
                        total_distance += G_fallback[u][v].get("length", 0)
                        if G_fallback[u][v].get("flood_level", 0) > 0:
                            flooded_segments += 1

                result = RouteResult(
                    route_index=0,
                    nodes=fallback_path,
                    coordinates=coordinates,
                    total_distance_m=round(total_distance, 1),
                    estimated_time_s=round(total_distance / (vehicle.average_speed * 1000 / 3600), 1),
                    flooded_segments=flooded_segments,
                    total_segments=len(fallback_path) - 1,
                    risk_score=min(flooded_segments / max(len(fallback_path) - 1, 1), 1.0),
                    max_flood_depth=0.0,
                )
                logger.info(f"Fallback route: {total_distance:.0f}m, {flooded_segments} flooded segments")
                return [result]

            except (nx.NetworkXNoPath, nx.NodeNotFound) as e:
                logger.warning(f"Fallback failed: {e}")
                # Last resort: try undirected graph (ignores one-way streets)
                logger.info("Last resort: trying undirected graph...")
                try:
                    G_undirected = G_fallback.to_undirected()
                    fallback_path = nx.shortest_path(G_undirected, source, target, weight="length")
                    logger.info(f"Undirected path found: {len(fallback_path)} nodes")

                    coordinates = []
                    total_distance = 0.0
                    flooded_segments = 0
                    for node in fallback_path:
                        lat = G.nodes[node].get("y", 0)
                        lon = G.nodes[node].get("x", 0)
                        coordinates.append((lat, lon))
                    for u, v in zip(fallback_path[:-1], fallback_path[1:]):
                        if G_undirected.has_edge(u, v):
                            total_distance += G_undirected[u][v].get("length", 0)

                    result = RouteResult(
                        route_index=0,
                        nodes=fallback_path,
                        coordinates=coordinates,
                        total_distance_m=round(total_distance, 1),
                        estimated_time_s=round(total_distance / (vehicle.average_speed * 1000 / 3600), 1),
                        flooded_segments=0,
                        total_segments=len(fallback_path) - 1,
                        risk_score=0.0,
                        max_flood_depth=0.0,
                    )
                    logger.info(f"Undirected route: {total_distance:.0f}m")
                    return [result]
                except Exception as e2:
                    logger.error(f"Undirected fallback also failed: {e2}")
            except Exception as e:
                logger.error(f"Fallback error: {e}")
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
