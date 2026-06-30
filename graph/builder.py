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
            place: OSM place name (e.g. "New Delhi, India")
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

        # Step 2: Download and save buildings/amenities
        self._download_buildings(place)

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

    def _download_buildings(self, place: str):
        """Download hospitals, schools, shelters, police, fire stations from OSM and save to DB."""
        import asyncio
        from osm.building_parser import BuildingParser
        from database.connection import DatabaseManager
        from sqlalchemy import text

        try:
            parser = BuildingParser()
            logger.info(f"Downloading buildings/amenities for '{place}'...")

            # Download amenities from OSM
            gdf = parser.download_buildings_for_place(place)
            if gdf.empty:
                logger.warning(f"No buildings found for '{place}'")
                return

            # Extract structured building data
            buildings = parser.extract_buildings(gdf, building_types=[
                "hospital", "school", "shelter", "police_station", "fire_station", "pharmacy"
            ])

            if not buildings:
                logger.info("No relevant amenities found")
                return

            # Save to database
            async def _save():
                async with DatabaseManager.session() as session:
                    for b in buildings:
                        try:
                            await session.execute(
                                text("""
                                    INSERT INTO buildings (osm_id, name, building_type, latitude, longitude, is_emergency_facility, created_at)
                                    VALUES (:osm_id, :name, :type, :lat, :lon, :emergency, NOW())
                                    ON CONFLICT (osm_id) DO NOTHING
                                """),
                                {
                                    "osm_id": b.get("osm_id") or hash(b["name"]) % 10000000,
                                    "name": b["name"],
                                    "type": b["building_type"],
                                    "lat": b["latitude"],
                                    "lon": b["longitude"],
                                    "emergency": b.get("is_emergency_facility", False),
                                },
                            )
                        except Exception:
                            pass
                    await session.commit()

            # Run async save in current event loop or new one
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(_save())
            except RuntimeError:
                asyncio.run(_save())

            logger.info(f"Downloaded {len(buildings)} buildings for '{place}'")

        except Exception as e:
            logger.warning(f"Building download failed (non-fatal): {e}")
