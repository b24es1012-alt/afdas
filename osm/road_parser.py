"""
Road network parser — extracts road data from OSMnx graphs.
Converts raw OSM data into structured road objects for database storage.
"""

import networkx as nx
import geopandas as gpd
import osmnx as ox
from typing import List, Tuple, Optional

from utils.logger import logger


class RoadParser:
    """
    Parses an OSMnx road network graph into structured road data.
    
    Extracts:
    - Road segments with geometry
    - Road types (motorway, primary, secondary, etc.)
    - Speed limits
    - Bridge/tunnel flags
    - One-way restrictions
    - Lane counts
    """

    def parse_graph(self, G: nx.MultiDiGraph) -> Tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]:
        """
        Convert an OSMnx graph to nodes and edges GeoDataFrames.
        
        Args:
            G: OSMnx road network graph
        
        Returns:
            (nodes_gdf, edges_gdf) tuple
        """
        nodes_gdf, edges_gdf = ox.graph_to_gdfs(G, nodes=True, edges=True)
        logger.info(f"Parsed graph: {len(nodes_gdf)} nodes, {len(edges_gdf)} edges")
        return nodes_gdf, edges_gdf

    def extract_roads(self, edges_gdf: gpd.GeoDataFrame) -> List[dict]:
        """
        Extract structured road data from edges GeoDataFrame.
        
        Args:
            edges_gdf: GeoDataFrame of graph edges
        
        Returns:
            List of road dicts ready for database insertion
        """
        roads = []

        for (u, v, key), row in edges_gdf.iterrows():
            road_type = row.get("highway", "residential")
            if isinstance(road_type, list):
                road_type = road_type[0]

            name = row.get("name")
            if isinstance(name, list):
                name = name[0] if name else None

            max_speed = row.get("maxspeed")
            if isinstance(max_speed, list):
                max_speed = max_speed[0]
            if max_speed:
                try:
                    max_speed = float(str(max_speed).replace(" km/h", "").replace(" mph", ""))
                except (ValueError, TypeError):
                    max_speed = None

            lanes = row.get("lanes")
            if isinstance(lanes, list):
                lanes = lanes[0]
            if lanes:
                try:
                    lanes = int(lanes)
                except (ValueError, TypeError):
                    lanes = None

            is_bridge = bool(row.get("bridge", False))
            if isinstance(is_bridge, str):
                is_bridge = is_bridge.lower() in ("yes", "true", "1")

            is_tunnel = bool(row.get("tunnel", False))
            if isinstance(is_tunnel, str):
                is_tunnel = is_tunnel.lower() in ("yes", "true", "1")

            is_oneway = bool(row.get("oneway", False))

            surface = row.get("surface")
            if isinstance(surface, list):
                surface = surface[0]

            length_m = row.get("length", 0)
            geometry = row.geometry

            osm_id = row.get("osmid", 0)
            if isinstance(osm_id, list):
                osm_id = osm_id[0]

            roads.append({
                "osm_id": int(osm_id) if osm_id else 0,
                "name": name,
                "road_type": road_type,
                "geometry_wkt": geometry.wkt if geometry else None,
                "length_m": float(length_m),
                "max_speed": max_speed,
                "lanes": lanes,
                "is_bridge": is_bridge,
                "is_tunnel": is_tunnel,
                "is_oneway": is_oneway,
                "surface": surface,
                "source_node": u,
                "target_node": v,
                "edge_key": key,
            })

        logger.info(f"Extracted {len(roads)} road segments")
        return roads

    def get_road_type_distribution(self, edges_gdf: gpd.GeoDataFrame) -> dict:
        """Get count of roads by type."""
        types = {}
        for _, row in edges_gdf.iterrows():
            rt = row.get("highway", "unknown")
            if isinstance(rt, list):
                rt = rt[0]
            types[rt] = types.get(rt, 0) + 1
        return dict(sorted(types.items(), key=lambda x: x[1], reverse=True))
