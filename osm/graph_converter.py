"""
Graph converter — converts OSM road network into internal graph representation.
Bridges the gap between OSMnx graphs and our routing engine.
"""

import networkx as nx
import geopandas as gpd
import osmnx as ox
from typing import Dict, Tuple, Optional

from utils.logger import logger


class GraphConverter:
    """
    Converts OSMnx MultiDiGraph into simplified structures
    suitable for routing and serialization.
    
    Operations:
    - Extract nodes with coordinates
    - Extract edges with attributes
    - Create simplified DiGraph (best edge per pair)
    - Annotate with CRS information
    """

    def graph_to_gdfs(
        self, G: nx.MultiDiGraph
    ) -> Tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]:
        """
        Convert OSMnx graph to GeoDataFrames.
        
        Returns:
            (nodes_gdf, edges_gdf)
        """
        nodes_gdf, edges_gdf = ox.graph_to_gdfs(G, nodes=True, edges=True)
        return nodes_gdf, edges_gdf

    def simplify_graph(self, G: nx.MultiDiGraph) -> nx.DiGraph:
        """
        Convert MultiDiGraph to simple DiGraph, keeping only
        the best (lowest weight) edge between each node pair.
        
        This is required for efficient routing algorithms.
        
        Args:
            G: OSMnx MultiDiGraph (may have parallel edges)
        
        Returns:
            Simple DiGraph with single edge per pair
        """
        G_simple = nx.DiGraph()

        # Add nodes with attributes
        for node, attrs in G.nodes(data=True):
            G_simple.add_node(node, **attrs)

        # Add edges, keeping lowest weight
        for u, v, data in G.edges(data=True):
            weight = data.get("weight", data.get("length", 1))
            if G_simple.has_edge(u, v):
                if weight < G_simple[u][v].get("weight", float("inf")):
                    G_simple[u][v].update(data)
                    G_simple[u][v]["weight"] = weight
            else:
                G_simple.add_edge(u, v, **data)
                G_simple[u][v]["weight"] = weight

        logger.info(
            f"Simplified graph: {G_simple.number_of_nodes()} nodes, "
            f"{G_simple.number_of_edges()} edges"
        )
        return G_simple

    def extract_node_coordinates(self, G: nx.MultiDiGraph) -> Dict[int, Tuple[float, float]]:
        """
        Extract node ID → (lat, lon) mapping.
        
        Returns:
            Dict mapping node_id to (latitude, longitude)
        """
        coords = {}
        for node, data in G.nodes(data=True):
            lat = data.get("y")
            lon = data.get("x")
            if lat is not None and lon is not None:
                coords[node] = (lat, lon)
        return coords

    def find_nearest_node(
        self, G: nx.MultiDiGraph, lat: float, lon: float
    ) -> int:
        """
        Find the nearest graph node to given coordinates.
        
        Args:
            G: Road network graph
            lat, lon: Target coordinates
        
        Returns:
            Node ID of the nearest node
        """
        return ox.distance.nearest_nodes(G, lon, lat)

    def get_graph_bounds(self, G: nx.MultiDiGraph) -> dict:
        """
        Get the geographic bounds of the graph.
        
        Returns:
            Dict with min_lat, max_lat, min_lon, max_lon
        """
        nodes_gdf = ox.graph_to_gdfs(G, nodes=True, edges=False)
        bounds = nodes_gdf.total_bounds  # [minx, miny, maxx, maxy]
        return {
            "min_lon": bounds[0],
            "min_lat": bounds[1],
            "max_lon": bounds[2],
            "max_lat": bounds[3],
        }

    def get_graph_stats(self, G: nx.MultiDiGraph) -> dict:
        """Get statistics about the graph."""
        return {
            "nodes": G.number_of_nodes(),
            "edges": G.number_of_edges(),
            "is_strongly_connected": nx.is_strongly_connected(G),
            "density": nx.density(G),
        }
