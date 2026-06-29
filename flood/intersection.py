"""
Flood intersection engine — computes road and building flood exposure.
"""

import geopandas as gpd
import numpy as np
from typing import List, Tuple, Optional
from shapely.geometry import Point, LineString
from sqlalchemy.ext.asyncio import AsyncSession

from database.flood_repository import FloodRepository
from database.road_repository import RoadRepository
from database.building_repository import BuildingRepository
from utils.logger import flood_logger as logger
from utils.constants import CRS_WGS84


class FloodIntersectionEngine:
    """
    Computes intersection between flood polygons and infrastructure.
    
    For each road: max depth, avg depth, flooded percentage, risk score.
    For each building: water depth, accessibility, evacuation status.
    """

    def __init__(self, session: AsyncSession):
        self.flood_repo = FloodRepository(session)
        self.road_repo = RoadRepository(session)
        self.building_repo = BuildingRepository(session)
        self.session = session

    async def compute_road_flood_exposure(
        self,
        event_id: int,
        flood_gdf: gpd.GeoDataFrame,
        roads_gdf: gpd.GeoDataFrame,
    ) -> List[dict]:
        """
        Compute flood exposure for all roads against flood polygons.
        
        Args:
            event_id: Flood event ID
            flood_gdf: GeoDataFrame of flood polygons
            roads_gdf: GeoDataFrame of road geometries
        
        Returns:
            List of flooded road dicts with exposure data
        """
        logger.info(f"Computing flood exposure: {len(roads_gdf)} roads × {len(flood_gdf)} zones")

        # Ensure same CRS
        if roads_gdf.crs != flood_gdf.crs:
            flood_gdf = flood_gdf.to_crs(roads_gdf.crs)

        # Spatial join — find roads intersecting flood
        joined = gpd.sjoin(
            roads_gdf,
            flood_gdf[["geometry"]],
            how="left",
            predicate="intersects",
        )

        # Detect depth column in flood data
        depth_col = next(
            (c for c in flood_gdf.columns if "depth" in c.lower()), None
        )

        flooded_roads = []
        flood_union = flood_gdf.geometry.unary_union

        for idx, road in roads_gdf.iterrows():
            road_geom = road.geometry
            if road_geom is None or road_geom.is_empty:
                continue

            # Check intersection
            intersection = road_geom.intersection(flood_union)
            if intersection.is_empty:
                continue

            # Compute metrics
            road_length = road_geom.length
            flooded_length = intersection.length
            flooded_pct = (flooded_length / road_length * 100) if road_length > 0 else 0

            # Get max depth at this road
            max_depth = 1.0  # Default if no depth column
            if depth_col:
                # Find which flood polygons this road crosses
                for _, fzone in flood_gdf.iterrows():
                    if road_geom.intersects(fzone.geometry):
                        d = fzone.get(depth_col, 1.0)
                        if d and float(d) > max_depth:
                            max_depth = float(d)

            avg_depth = max_depth * (flooded_pct / 100)

            # Risk score (0-1)
            risk = min(1.0, (max_depth / 2.0) * (flooded_pct / 100))

            road_data = {
                "road_idx": idx,
                "max_depth": max_depth,
                "avg_depth": avg_depth,
                "flooded_percentage": flooded_pct,
                "risk_score": risk,
            }
            flooded_roads.append(road_data)

        logger.info(f"Found {len(flooded_roads)} flooded road segments")
        return flooded_roads

    async def compute_building_flood_exposure(
        self,
        event_id: int,
        flood_gdf: gpd.GeoDataFrame,
        buildings: List[dict],
    ) -> List[dict]:
        """
        Check which buildings are in flood zones.
        
        Args:
            event_id: Flood event ID
            flood_gdf: GeoDataFrame of flood polygons
            buildings: List of building dicts with lat/lon
        
        Returns:
            List of affected building dicts
        """
        logger.info(f"Checking {len(buildings)} buildings against flood zones")

        depth_col = next(
            (c for c in flood_gdf.columns if "depth" in c.lower()), None
        )
        flood_union = flood_gdf.geometry.unary_union

        affected = []
        for building in buildings:
            point = Point(building["longitude"], building["latitude"])

            if flood_union.contains(point):
                # Find max depth
                water_depth = 1.0
                if depth_col:
                    for _, zone in flood_gdf.iterrows():
                        if zone.geometry.contains(point):
                            d = zone.get(depth_col, 1.0)
                            if d and float(d) > water_depth:
                                water_depth = float(d)

                affected.append({
                    "building_id": building.get("id"),
                    "name": building.get("name"),
                    "water_depth": water_depth,
                    "is_accessible": water_depth < 0.3,
                    "evacuation_needed": water_depth > 0.5,
                })

        logger.info(f"Found {len(affected)} affected buildings")
        return affected

    def get_flood_depth_at_point(
        self, lat: float, lon: float, flood_gdf: gpd.GeoDataFrame
    ) -> float:
        """
        Get flood depth at a specific point from in-memory GeoDataFrame.
        
        Args:
            lat, lon: Coordinates
            flood_gdf: Flood polygon GeoDataFrame
        
        Returns:
            Flood depth in metres (0.0 if not flooded)
        """
        point = Point(lon, lat)
        depth_col = next(
            (c for c in flood_gdf.columns if "depth" in c.lower()), None
        )

        for _, row in flood_gdf.iterrows():
            if row.geometry.contains(point):
                if depth_col and row[depth_col] is not None:
                    return float(row[depth_col])
                return 1.0

        return 0.0
