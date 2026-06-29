"""
Weight computation engine — computes vehicle-specific edge weights.
Separates weight logic from graph topology for efficient recomputation.
"""

import networkx as nx
import geopandas as gpd
from typing import Dict

from models.vehicle import VehicleProfile, VEHICLE_PROFILES, VehicleType
from models.road import ROAD_TYPE_FACTORS
from utils.constants import IMPASSABLE_WEIGHT
from utils.logger import graph_logger as logger


class WeightEngine:
    """
    Computes edge weights for a specific vehicle type.
    
    Weight formula:
        weight = (time_cost * road_factor) + flood_penalty
    
    Where:
        - time_cost = distance / vehicle_speed
        - road_factor = penalty for road type (motorway=0.8, residential=1.5)
        - flood_penalty = flood_level * vehicle.flood_penalty_factor
        - If flood_level > vehicle.max_flood_depth → weight = IMPASSABLE (1e9)
    
    This allows the same base graph to be reused across all vehicles
    by simply recomputing the weight arrays.
    """

    def compute_weights_for_graph(
        self,
        G: nx.MultiDiGraph,
        vehicle: VehicleProfile,
    ) -> nx.MultiDiGraph:
        """
        Compute and assign weights to all edges in a MultiDiGraph.
        Modifies the graph in-place and returns it.
        
        Args:
            G: Graph with flood_level on edges
            vehicle: Vehicle profile for weight computation
        
        Returns:
            Same graph with 'weight' attribute on all edges
        """
        blocked_count = 0
        total_edges = 0

        for u, v, key, data in G.edges(keys=True, data=True):
            weight = self._compute_single_weight(data, vehicle)
            data["weight"] = weight
            total_edges += 1
            if weight >= IMPASSABLE_WEIGHT:
                blocked_count += 1

        logger.info(
            f"Weights computed for {vehicle.vehicle_type.value}: "
            f"{total_edges} edges, {blocked_count} blocked"
        )
        return G

    def compute_weights_for_simple_graph(
        self,
        G_simple: nx.DiGraph,
        vehicle: VehicleProfile,
    ) -> nx.DiGraph:
        """
        Compute weights for a simplified DiGraph.
        
        Args:
            G_simple: Simplified graph
            vehicle: Vehicle profile
        
        Returns:
            Graph with updated weights
        """
        for u, v, data in G_simple.edges(data=True):
            data["weight"] = self._compute_single_weight(data, vehicle)
        return G_simple

    def compute_weights_for_edges_gdf(
        self,
        edges_gdf: gpd.GeoDataFrame,
        vehicle: VehicleProfile,
    ) -> gpd.GeoDataFrame:
        """
        Compute weights for an edges GeoDataFrame.
        
        Args:
            edges_gdf: Edges with flood_level column
            vehicle: Vehicle profile
        
        Returns:
            Same GeoDataFrame with 'weight' column added/updated
        """
        edges_gdf["weight"] = edges_gdf.apply(
            lambda row: self._compute_single_weight(row, vehicle), axis=1
        )
        return edges_gdf

    def _compute_single_weight(self, edge_data, vehicle: VehicleProfile) -> float:
        """
        Compute weight for a single edge.
        
        Args:
            edge_data: Edge attributes (dict or Series)
            vehicle: Vehicle profile
        
        Returns:
            Computed weight (float)
        """
        # Base distance
        distance = edge_data.get("length", 1.0)
        if distance <= 0:
            distance = 1.0

        # Time cost
        time_cost = distance / (vehicle.average_speed * 1000 / 3600)  # m/s

        # Flood level
        flood_level = edge_data.get("flood_level", 0.0)
        if flood_level is None:
            flood_level = 0.0

        # BLOCKED: flood exceeds vehicle tolerance
        if flood_level > vehicle.max_flood_depth:
            return IMPASSABLE_WEIGHT

        # Flood penalty (proportional to depth)
        flood_penalty = flood_level * vehicle.flood_penalty_factor

        # Road type factor
        road_type = edge_data.get("highway", "residential")
        if isinstance(road_type, list):
            road_type = road_type[0]

        road_factor = self._get_road_factor(road_type)

        # Check road restrictions for this vehicle
        if road_type in vehicle.road_restrictions:
            return IMPASSABLE_WEIGHT

        # Final weight
        weight = (time_cost * road_factor) + flood_penalty
        return max(weight, 0.001)  # Ensure positive

    @staticmethod
    def _get_road_factor(road_type: str) -> float:
        """Get the road type weighting factor."""
        road_factor_map = {
            "motorway": 0.8,
            "motorway_link": 0.85,
            "trunk": 0.9,
            "trunk_link": 0.95,
            "primary": 1.0,
            "primary_link": 1.05,
            "secondary": 1.2,
            "secondary_link": 1.25,
            "tertiary": 1.3,
            "tertiary_link": 1.35,
            "residential": 1.5,
            "service": 1.8,
            "unclassified": 1.6,
            "living_street": 2.0,
            "pedestrian": 2.5,
            "track": 2.2,
        }
        return road_factor_map.get(road_type, 1.5)

    def get_all_vehicle_weights(
        self, G: nx.MultiDiGraph
    ) -> Dict[str, nx.MultiDiGraph]:
        """
        Compute weights for ALL vehicle types.
        Returns a dict of vehicle_type → weighted graph copy.
        
        Useful for pre-caching popular vehicle types.
        """
        result = {}
        for vtype, profile in VEHICLE_PROFILES.items():
            G_copy = G.copy()
            self.compute_weights_for_graph(G_copy, profile)
            result[vtype.value] = G_copy
            logger.info(f"Pre-computed weights for: {vtype.value}")
        return result
