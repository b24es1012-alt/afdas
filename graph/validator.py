"""
Graph validator — checks graph integrity before routing.
"""

import networkx as nx
from typing import List, Tuple

from utils.logger import graph_logger as logger
from utils.constants import IMPASSABLE_WEIGHT


class GraphValidator:
    """
    Validates graph quality and connectivity before routing.
    
    Checks:
    - Graph is not empty
    - Source and target nodes exist
    - Path exists between source and target (at least one)
    - No completely disconnected subgraphs blocking the route
    - Edge weights are reasonable
    """

    def validate_for_routing(
        self,
        G: nx.DiGraph,
        source: int,
        target: int,
    ) -> Tuple[bool, str]:
        """
        Validate that routing is possible between source and target.
        
        Args:
            G: Graph to validate
            source: Source node ID
            target: Target node ID
        
        Returns:
            (is_valid, message) tuple
        """
        # Check graph not empty
        if G.number_of_nodes() == 0:
            return False, "Graph is empty — no nodes"

        if G.number_of_edges() == 0:
            return False, "Graph has no edges"

        # Check nodes exist
        if source not in G.nodes:
            return False, f"Source node {source} not in graph"

        if target not in G.nodes:
            return False, f"Target node {target} not in graph"

        # Check if source == target
        if source == target:
            return False, "Source and target are the same node"

        # Check basic connectivity (ignoring blocked edges)
        G_passable = nx.DiGraph()
        for u, v, data in G.edges(data=True):
            if data.get("weight", 0) < IMPASSABLE_WEIGHT:
                G_passable.add_edge(u, v)

        if source not in G_passable.nodes or target not in G_passable.nodes:
            return False, "Source or target only connected by blocked (flooded) roads"

        if not nx.has_path(G_passable, source, target):
            return False, "No passable path exists between source and target (all routes flooded)"

        return True, "Graph valid for routing"

    def check_graph_health(self, G: nx.MultiDiGraph) -> dict:
        """
        Full health check of a graph.
        
        Returns:
            Dict with health metrics
        """
        total_edges = G.number_of_edges()
        blocked_edges = sum(
            1 for _, _, d in G.edges(data=True)
            if d.get("weight", 0) >= IMPASSABLE_WEIGHT
        )
        flooded_edges = sum(
            1 for _, _, d in G.edges(data=True)
            if d.get("flood_level", 0) > 0
        )

        # Connectivity
        G_undirected = G.to_undirected()
        components = nx.number_connected_components(G_undirected)

        return {
            "total_nodes": G.number_of_nodes(),
            "total_edges": total_edges,
            "blocked_edges": blocked_edges,
            "flooded_edges": flooded_edges,
            "blocked_percentage": (blocked_edges / total_edges * 100) if total_edges > 0 else 0,
            "flooded_percentage": (flooded_edges / total_edges * 100) if total_edges > 0 else 0,
            "connected_components": components,
            "is_connected": components == 1,
        }

    def find_isolated_nodes(self, G: nx.DiGraph) -> List[int]:
        """Find nodes with no passable edges."""
        isolated = []
        for node in G.nodes:
            has_out = any(
                G[node][succ].get("weight", 0) < IMPASSABLE_WEIGHT
                for succ in G.successors(node)
            )
            has_in = any(
                G[pred][node].get("weight", 0) < IMPASSABLE_WEIGHT
                for pred in G.predecessors(node)
            )
            if not has_out and not has_in:
                isolated.append(node)
        return isolated
