"""
Graph builder — constructs the base road network graph.
Runs ONCE per flood event, then gets cached.
"""

import networkx as nx
import geopandas as gpd
import osmnx as ox
from typing import Tuple, Optional

from osm.downloader import OSMDownloader
from osm.graph_converter import GraphConverter
from flood.polygon_loader import FloodPolygonLoader
from utils.logger import graph_logger as logger


class GraphBuilder:
    """
    Builds the base road network graph with flood annotation.
    
    Workflow:
    1. Download road network from OSM (or load from cache/DB)
    2. Load flood polygons
    3. Spatial join: tag edges with flood data
    4. Return annotated graph ready for weight computation
    
    The base graph stores topology + flood_level per edge.
    Weights are computed separately by the WeightEngine per vehicle.
    """

    def __init__(self):
        self.osm_downloader = OSMDownloader()
        self.graph_converter = GraphConverter()

    def build_from_place(
        self,
        place: str,
        flood_shapefile: Optional[str] = None,
        flood_gdf: Optional[gpd.GeoDataFrame] = None,
        network_type: str = "drive",
    ) -> Tuple[nx.MultiDiGraph, nx.DiGraph, gpd.GeoDataFrame]:
        """
        Build a flood-annotated road graph for a place.
        
        Args:
            place: OSM place name (e.g. "Gujrat, Punjab, Pakistan")
            flood_shapefile: Path to flood shapefile (optional)
            flood_gdf: Pre-loaded flood GeoDataFrame (optional)
            network_type: OSM network type
        
        Returns:
            (G_multi, G_simple, edges_gdf) tuple:
            - G_multi: Original MultiDiGraph with flood_level on edges
            - G_simple: Simplified DiGraph (best edge per pair)
            - edges_gdf: GeoDataFrame of edges with flood annotations
        """
        logger.info(f"Building graph for '{place}'")

        # Step 1: Download road network
        G = self.osm_downloader.download_road_network(place, network_type)

        # Step 2: Convert to GeoDataFrames
        nodes_gdf, edges_gdf = self.graph_converter.graph_to_gdfs(G)

        # Step 3: Annotate with flood data
        if flood_gdf is not None:
            edges_gdf = self._annotate_flood(edges_gdf, flood_gdf)
        elif flood_shapefile:
            loader = FloodPolygonLoader(session=None)
            flood_gdf = loader.load_as_geodataframe(flood_shapefile)
            edges_gdf = self._annotate_flood(edges_gdf, flood_gdf)
        else:
            edges_gdf["flood_level"] = 0.0
            logger.info("No flood data provided — all edges marked safe")

        # Step 4: Write flood_level back into the graph
        for (u, v, key), row in edges_gdf.iterrows():
            if key in G[u][v]:
                G[u][v][key]["flood_level"] = row["flood_level"]

        # Step 5: Create simplified DiGraph
        G_simple = self.graph_converter.simplify_graph(G)

        logger.info(
            f"Graph built: {G.number_of_nodes()} nodes, "
            f"{G.number_of_edges()} edges, "
            f"{(edges_gdf['flood_level'] > 0).sum()} flooded edges"
        )

        return G, G_simple, edges_gdf

    def _annotate_flood(
        self,
        edges_gdf: gpd.GeoDataFrame,
        flood_gdf: gpd.GeoDataFrame,
    ) -> gpd.GeoDataFrame:
        """
        Annotate road edges with flood level via spatial join.
        """
        # Ensure matching CRS
        if flood_gdf.crs != edges_gdf.crs:
            flood_gdf = flood_gdf.to_crs(edges_gdf.crs)

        # Detect depth column
        depth_col = next(
            (c for c in flood_gdf.columns if "depth" in c.lower()), None
        )

        # Spatial join
        joined = gpd.sjoin(
            edges_gdf,
            flood_gdf[["geometry"] + ([depth_col] if depth_col else [])],
            how="left",
            predicate="intersects",
        )

        # Assign flood_level
        if depth_col and depth_col in joined.columns:
            joined["flood_level"] = joined[depth_col].fillna(0)
        else:
            joined["flood_level"] = joined["index_right"].notnull().astype(float)

        # Remove index_right before groupby
        if "index_right" in joined.columns:
            joined = joined.drop(columns=["index_right"])

        # Collapse duplicates (keep max flood per edge)
        agg_dict = {col: "first" for col in joined.columns if col != "flood_level"}
        agg_dict["flood_level"] = "max"
        edges_gdf = joined.groupby(level=[0, 1, 2]).agg(agg_dict)

        flooded_count = (edges_gdf["flood_level"] > 0).sum()
        logger.info(f"Flood annotation: {flooded_count} edges flooded out of {len(edges_gdf)}")

        return edges_gdf
