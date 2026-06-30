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
        event_id: Optional[int] = None,
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

        # Step 6: Save roads and flooded roads to database
        self._save_roads_to_db(edges_gdf, event_id=event_id)

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


    def _save_roads_to_db(self, edges_gdf: gpd.GeoDataFrame, event_id: Optional[int] = None):
        """
        Save roads and flooded roads to the database after graph construction.
        
        - All edges → `roads` table (ON CONFLICT skip if already exists)
        - Edges with flood_level > 0 → `flooded_roads` table
        """
        import asyncio
        from database.connection import DatabaseManager
        from sqlalchemy import text

        try:
            flooded_edges = edges_gdf[edges_gdf["flood_level"] > 0]
            total_edges = len(edges_gdf)
            flooded_count = len(flooded_edges)

            if total_edges == 0:
                return

            logger.info(f"Saving {total_edges} roads to DB ({flooded_count} flooded)...")

            async def _save():
                async with DatabaseManager.session() as session:
                    # Save all roads
                    roads_saved = 0
                    for idx, row in edges_gdf.iterrows():
                        try:
                            u, v, key = idx
                            osm_id = row.get("osmid", None)
                            if isinstance(osm_id, list):
                                osm_id = osm_id[0] if osm_id else None

                            name = row.get("name", None)
                            if isinstance(name, list):
                                name = name[0] if name else None

                            road_type = row.get("highway", "residential")
                            if isinstance(road_type, list):
                                road_type = road_type[0] if road_type else "residential"

                            length = row.get("length", 0) or 0
                            max_speed = row.get("maxspeed", None)
                            if isinstance(max_speed, list):
                                max_speed = max_speed[0] if max_speed else None
                            if isinstance(max_speed, str):
                                try:
                                    max_speed = float(max_speed.replace("mph", "").replace("kph", "").strip())
                                except (ValueError, AttributeError):
                                    max_speed = None

                            lanes = row.get("lanes", None)
                            if isinstance(lanes, list):
                                lanes = lanes[0] if lanes else None
                            if isinstance(lanes, str):
                                try:
                                    lanes = int(lanes)
                                except (ValueError, TypeError):
                                    lanes = None

                            is_bridge = bool(row.get("bridge", False))
                            is_tunnel = bool(row.get("tunnel", False))
                            is_oneway = bool(row.get("oneway", False))
                            surface = row.get("surface", None)
                            if isinstance(surface, list):
                                surface = surface[0] if surface else None

                            # Get geometry as WKT
                            geom = row.get("geometry", None)
                            if geom is None:
                                continue
                            geom_wkt = geom.wkt

                            await session.execute(
                                text("""
                                    INSERT INTO roads (osm_id, name, road_type, geometry, length_m,
                                                      max_speed, lanes, is_bridge, is_tunnel,
                                                      is_oneway, surface, event_id, created_at)
                                    VALUES (:osm_id, :name, :road_type,
                                            ST_GeomFromText(:geom, 4326),
                                            :length, :max_speed, :lanes,
                                            :is_bridge, :is_tunnel, :is_oneway,
                                            :surface, :event_id, NOW())
                                    ON CONFLICT (osm_id) DO NOTHING
                                """),
                                {
                                    "osm_id": int(osm_id) if osm_id else None,
                                    "name": str(name)[:255] if name else None,
                                    "road_type": str(road_type)[:50],
                                    "geom": geom_wkt,
                                    "length": float(length),
                                    "max_speed": float(max_speed) if max_speed else None,
                                    "lanes": int(lanes) if lanes else None,
                                    "is_bridge": is_bridge,
                                    "is_tunnel": is_tunnel,
                                    "is_oneway": is_oneway,
                                    "surface": str(surface)[:50] if surface else None,
                                    "event_id": event_id,
                                },
                            )
                            roads_saved += 1
                        except Exception:
                            pass

                    await session.commit()
                    logger.info(f"Saved {roads_saved} roads to database")

                    # Now save flooded roads
                    if flooded_count > 0 and event_id:
                        flooded_saved = 0
                        for idx, row in flooded_edges.iterrows():
                            try:
                                u, v, key = idx
                                osm_id = row.get("osmid", None)
                                if isinstance(osm_id, list):
                                    osm_id = osm_id[0] if osm_id else None
                                if not osm_id:
                                    continue

                                flood_level = float(row.get("flood_level", 0))
                                length = float(row.get("length", 0) or 0)

                                # Get road_id from roads table
                                result = await session.execute(
                                    text("SELECT id FROM roads WHERE osm_id = :osm_id LIMIT 1"),
                                    {"osm_id": int(osm_id)},
                                )
                                road_row = result.fetchone()
                                if not road_row:
                                    continue

                                road_id = road_row[0]

                                await session.execute(
                                    text("""
                                        INSERT INTO flooded_roads (event_id, road_id, max_depth,
                                                                   avg_depth, flooded_percentage,
                                                                   risk_score, created_at)
                                        VALUES (:event_id, :road_id, :max_depth, :avg_depth,
                                                :flooded_pct, :risk_score, NOW())
                                        ON CONFLICT (event_id, road_id) DO UPDATE SET
                                            max_depth = GREATEST(flooded_roads.max_depth, EXCLUDED.max_depth),
                                            avg_depth = EXCLUDED.avg_depth,
                                            risk_score = EXCLUDED.risk_score
                                    """),
                                    {
                                        "event_id": event_id,
                                        "road_id": road_id,
                                        "max_depth": flood_level,
                                        "avg_depth": flood_level,
                                        "flooded_pct": 100.0,
                                        "risk_score": min(flood_level / 1.0, 1.0),
                                    },
                                )
                                flooded_saved += 1
                            except Exception:
                                pass

                        await session.commit()
                        logger.info(f"Saved {flooded_saved} flooded roads to database")
                    elif flooded_count > 0 and not event_id:
                        logger.info(f"Skipped flooded_roads save: no event_id provided ({flooded_count} flooded edges)")

            # Run async save
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(_save())
            except RuntimeError:
                asyncio.run(_save())

        except Exception as e:
            logger.warning(f"Road DB save failed (non-fatal): {e}")
