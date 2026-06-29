"""
Real-time rerouting service — recomputes routes when conditions change.
"""

import networkx as nx
from typing import List, Optional, Tuple

from routing.astar import astar_path
from routing.service import RouteResult, RoutingService
from graph.validator import GraphValidator
from models.vehicle import get_vehicle_profile
from utils.logger import routing_logger as logger
from utils.constants import IMPASSABLE_WEIGHT


class ReroutingService:
    """
    Handles real-time rerouting when road conditions change.
    
    Triggers for reroute:
    - User deviates from planned route
    - Road ahead becomes newly flooded
    - Flood data is updated
    - User requests a different vehicle type mid-navigation
    """

    def __init__(self, routing_service: RoutingService):
        self.routing_service = routing_service
        self.validator = GraphValidator()

    async def check_route_validity(
        self,
        G_simple: nx.DiGraph,
        current_path: List[int],
        current_position_idx: int,
        vehicle_type: str,
    ) -> Tuple[bool, str]:
        """
        Check if the remaining route is still passable.
        
        Args:
            G_simple: Current weighted graph
            current_path: Original planned path
            current_position_idx: Index in path of current position
            vehicle_type: Vehicle type
        
        Returns:
            (is_valid, reason) — reason is empty if valid
        """
        vehicle = get_vehicle_profile(vehicle_type)
        remaining = current_path[current_position_idx:]

        if len(remaining) < 2:
            return True, ""

        for u, v in zip(remaining[:-1], remaining[1:]):
            if not G_simple.has_edge(u, v):
                return False, f"Edge {u}→{v} no longer exists"

            edge_data = G_simple[u][v]
            weight = edge_data.get("weight", 0)

            if weight >= IMPASSABLE_WEIGHT:
                flood_level = edge_data.get("flood_level", 0)
                return False, (
                    f"Road segment {u}→{v} is now blocked "
                    f"(flood depth: {flood_level:.2f}m, "
                    f"vehicle limit: {vehicle.max_flood_depth}m)"
                )

        return True, ""

    async def reroute(
        self,
        current_lat: float,
        current_lon: float,
        end_lat: float,
        end_lon: float,
        vehicle_type: str = "car",
        place: str = "Gujrat, Punjab, Pakistan",
        flood_shapefile: Optional[str] = None,
        event_id: Optional[str] = None,
    ) -> List[RouteResult]:
        """
        Compute a new route from current position to destination.
        Called when the existing route becomes invalid.
        
        Args:
            current_lat, current_lon: Current GPS position
            end_lat, end_lon: Original destination
            vehicle_type: Vehicle type
            place: Place context for graph
            flood_shapefile: Flood data (may be updated)
            event_id: Flood event ID
        
        Returns:
            New list of RouteResult
        """
        logger.info(
            f"REROUTING: ({current_lat:.5f}, {current_lon:.5f}) → "
            f"({end_lat:.5f}, {end_lon:.5f}) [{vehicle_type}]"
        )

        # Invalidate existing graph cache to pick up new flood data
        await self.routing_service.graph_loader.invalidate(
            place=place, vehicle_type=vehicle_type, event_id=event_id
        )

        # Compute new routes from current position
        routes = await self.routing_service.find_routes(
            start_lat=current_lat,
            start_lon=current_lon,
            end_lat=end_lat,
            end_lon=end_lon,
            vehicle_type=vehicle_type,
            k=2,  # Fewer alternatives for reroute (speed)
            place=place,
            flood_shapefile=flood_shapefile,
            event_id=event_id,
        )

        if routes:
            logger.info(f"Reroute successful: {len(routes)} new route(s)")
        else:
            logger.warning("Reroute failed: no passable routes found")

        return routes
