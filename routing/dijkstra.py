"""
Dijkstra's algorithm and Yen's K-shortest paths.
Used for finding multiple alternative flood-safe routes.
"""

import heapq
from itertools import count
from typing import List, Optional
import networkx as nx

from utils.logger import routing_logger as logger
from utils.constants import IMPASSABLE_WEIGHT


def dijkstra_path(
    G: nx.DiGraph,
    source: int,
    target: int,
    weight: str = "weight",
) -> Optional[List[int]]:
    """
    Find shortest path using Dijkstra's algorithm.
    
    Args:
        G: Weighted DiGraph
        source: Start node
        target: End node
        weight: Edge weight attribute
    
    Returns:
        List of node IDs or None
    """
    try:
        return nx.dijkstra_path(G, source, target, weight=weight)
    except nx.NetworkXNoPath:
        logger.warning(f"Dijkstra: No path from {source} to {target}")
        return None
    except Exception as e:
        logger.error(f"Dijkstra error: {e}")
        return None


def yen_k_shortest_paths(
    G: nx.DiGraph,
    source: int,
    target: int,
    k: int = 3,
    weight: str = "weight",
) -> List[List[int]]:
    """
    Yen's K-shortest simple paths algorithm.
    Finds up to K alternative routes between source and target.
    
    Args:
        G: Weighted DiGraph
        source: Start node
        target: End node
        k: Number of paths to find
        weight: Edge weight attribute
    
    Returns:
        List of paths (each path is a list of node IDs)
    """
    # Find the first shortest path
    try:
        first = nx.dijkstra_path(G, source, target, weight=weight)
    except nx.NetworkXNoPath:
        logger.warning(f"Yen's: No initial path from {source} to {target}")
        return []

    A = [first]  # Found shortest paths
    B = []  # Candidate paths (heap)
    counter = count()

    for _ in range(1, k):
        prev = A[-1]

        for i in range(len(prev) - 1):
            spur_node = prev[i]
            root_path = prev[: i + 1]

            # Track removed edges for restoration
            removed_edges = []

            # Remove edges that share the same root path
            for path in A:
                if path[: i + 1] == root_path and i + 1 < len(path):
                    u, v = path[i], path[i + 1]
                    if G.has_edge(u, v):
                        edge_data = G[u][v].copy()
                        removed_edges.append((u, v, edge_data))
                        G.remove_edge(u, v)

            # Remove root path nodes (except spur) to avoid loops
            removed_node_edges = []
            for node in root_path[:-1]:
                for successor in list(G.successors(node)):
                    edge_data = G[node][successor].copy()
                    removed_node_edges.append((node, successor, edge_data))
                    G.remove_edge(node, successor)

            # Find spur path
            try:
                spur_path = nx.dijkstra_path(G, spur_node, target, weight=weight)
                total_path = root_path[:-1] + spur_path

                # Calculate cost
                cost = 0
                valid = True
                for u, v in zip(total_path[:-1], total_path[1:]):
                    if G.has_edge(u, v):
                        cost += G[u][v].get(weight, 1)
                    else:
                        # Edge was removed, use original cost from A[0]'s graph
                        valid = False
                        break

                if valid and total_path not in A:
                    heapq.heappush(B, (cost, next(counter), total_path))

            except nx.NetworkXNoPath:
                pass

            # Restore removed edges
            for u, v, data in removed_edges:
                G.add_edge(u, v, **data)
            for u, v, data in removed_node_edges:
                G.add_edge(u, v, **data)

        if not B:
            break

        _, _, next_path = heapq.heappop(B)

        # Skip duplicates
        while B and next_path in A:
            if not B:
                break
            _, _, next_path = heapq.heappop(B)

        if next_path not in A:
            A.append(next_path)

    logger.info(f"Yen's K-shortest: found {len(A)} paths (requested {k})")
    return A
