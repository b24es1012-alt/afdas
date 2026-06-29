"""
A* routing algorithm — heuristic-guided shortest path.
Uses great-circle distance as the heuristic for geospatial graphs.
"""

import heapq
import math
from typing import List, Optional, Dict, Tuple
import networkx as nx

from utils.logger import routing_logger as logger
from utils.constants import IMPASSABLE_WEIGHT, EARTH_RADIUS_KM


def _haversine_heuristic(G: nx.DiGraph, target: int):
    """
    Create a heuristic function for A* using haversine distance.
    Returns a function that estimates cost from any node to target.
    """
    target_lat = G.nodes[target].get("y", 0)
    target_lon = G.nodes[target].get("x", 0)

    def heuristic(node, _target):
        lat = G.nodes[node].get("y", 0)
        lon = G.nodes[node].get("x", 0)
        # Haversine in meters (approximate, fast)
        dlat = math.radians(target_lat - lat)
        dlon = math.radians(target_lon - lon)
        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(math.radians(lat))
            * math.cos(math.radians(target_lat))
            * math.sin(dlon / 2) ** 2
        )
        c = 2 * math.asin(math.sqrt(a))
        return EARTH_RADIUS_KM * c * 1000  # metres

    return heuristic


def astar_path(
    G: nx.DiGraph,
    source: int,
    target: int,
    weight: str = "weight",
) -> Optional[List[int]]:
    """
    Find the shortest path using A* with haversine heuristic.
    
    Args:
        G: Weighted DiGraph
        source: Start node
        target: End node
        weight: Edge weight attribute name
    
    Returns:
        List of node IDs forming the path, or None if no path exists
    """
    if source not in G.nodes or target not in G.nodes:
        return None

    try:
        heuristic = _haversine_heuristic(G, target)
        path = nx.astar_path(G, source, target, heuristic=heuristic, weight=weight)
        return path
    except nx.NetworkXNoPath:
        logger.warning(f"A*: No path from {source} to {target}")
        return None
    except Exception as e:
        logger.error(f"A* error: {e}")
        return None


def astar_path_with_cost(
    G: nx.DiGraph,
    source: int,
    target: int,
    weight: str = "weight",
) -> Tuple[Optional[List[int]], float]:
    """
    A* with total path cost returned.
    
    Returns:
        (path, total_cost) tuple. Path is None if not found.
    """
    path = astar_path(G, source, target, weight)
    if path is None:
        return None, float("inf")

    cost = sum(
        G[u][v].get(weight, 1)
        for u, v in zip(path[:-1], path[1:])
        if G.has_edge(u, v)
    )
    return path, cost
