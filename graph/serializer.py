"""
Graph serializer — converts graphs to/from binary for Redis caching.
"""

import pickle
import zlib
from typing import Optional, Tuple
import networkx as nx
import geopandas as gpd

from utils.logger import graph_logger as logger


class GraphSerializer:
    """
    Serializes/deserializes NetworkX graphs for Redis storage.
    
    Uses pickle + zlib compression for efficient storage.
    Typical road graph for a city: ~5-20 MB uncompressed → ~1-5 MB compressed.
    """

    COMPRESSION_LEVEL = 6  # Balance between speed and compression ratio

    def serialize_graph(self, G: nx.MultiDiGraph) -> bytes:
        """
        Serialize a MultiDiGraph to compressed bytes.
        
        Args:
            G: NetworkX graph
        
        Returns:
            Compressed bytes
        """
        raw = pickle.dumps(G, protocol=pickle.HIGHEST_PROTOCOL)
        compressed = zlib.compress(raw, self.COMPRESSION_LEVEL)
        ratio = len(compressed) / len(raw) * 100 if raw else 0
        logger.info(
            f"Serialized graph: {len(raw)} → {len(compressed)} bytes "
            f"({ratio:.1f}% of original)"
        )
        return compressed

    def deserialize_graph(self, data: bytes) -> nx.MultiDiGraph:
        """
        Deserialize compressed bytes back to a MultiDiGraph.
        
        Args:
            data: Compressed bytes
        
        Returns:
            NetworkX MultiDiGraph
        """
        raw = zlib.decompress(data)
        G = pickle.loads(raw)
        logger.info(f"Deserialized graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
        return G

    def serialize_simple_graph(self, G: nx.DiGraph) -> bytes:
        """Serialize a DiGraph to compressed bytes."""
        raw = pickle.dumps(G, protocol=pickle.HIGHEST_PROTOCOL)
        return zlib.compress(raw, self.COMPRESSION_LEVEL)

    def deserialize_simple_graph(self, data: bytes) -> nx.DiGraph:
        """Deserialize compressed bytes to a DiGraph."""
        raw = zlib.decompress(data)
        return pickle.loads(raw)

    def serialize_edges_gdf(self, edges_gdf: gpd.GeoDataFrame) -> bytes:
        """Serialize an edges GeoDataFrame."""
        raw = pickle.dumps(edges_gdf, protocol=pickle.HIGHEST_PROTOCOL)
        return zlib.compress(raw, self.COMPRESSION_LEVEL)

    def deserialize_edges_gdf(self, data: bytes) -> gpd.GeoDataFrame:
        """Deserialize bytes to an edges GeoDataFrame."""
        raw = zlib.decompress(data)
        return pickle.loads(raw)

    def serialize_full(
        self,
        G: nx.MultiDiGraph,
        G_simple: nx.DiGraph,
        edges_gdf: gpd.GeoDataFrame,
    ) -> bytes:
        """
        Serialize the full graph bundle (G, G_simple, edges_gdf).
        
        Returns:
            Single compressed bytes blob
        """
        bundle = {
            "G": G,
            "G_simple": G_simple,
            "edges_gdf": edges_gdf,
        }
        raw = pickle.dumps(bundle, protocol=pickle.HIGHEST_PROTOCOL)
        compressed = zlib.compress(raw, self.COMPRESSION_LEVEL)
        logger.info(f"Full bundle serialized: {len(compressed)} bytes")
        return compressed

    def deserialize_full(
        self, data: bytes
    ) -> Tuple[nx.MultiDiGraph, nx.DiGraph, gpd.GeoDataFrame]:
        """
        Deserialize a full graph bundle.
        
        Returns:
            (G, G_simple, edges_gdf)
        """
        raw = zlib.decompress(data)
        bundle = pickle.loads(raw)
        return bundle["G"], bundle["G_simple"], bundle["edges_gdf"]
