"""
Flood polygon loader — reads shapefiles/GeoJSON and loads into PostGIS.
"""

import geopandas as gpd
from typing import Optional, List
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession

from database.flood_repository import FloodRepository
from utils.logger import flood_logger as logger
from utils.constants import CRS_WGS84


class FloodPolygonLoader:
    """
    Loads flood polygon data from shapefiles into PostGIS.
    
    Supports:
    - Copernicus EMS shapefiles (.shp)
    - GeoJSON files
    - GeoPackage files (.gpkg)
    """

    def __init__(self, session: AsyncSession):
        self.repo = FloodRepository(session)

    async def load_from_shapefile(
        self,
        shapefile_path: str,
        event_id: int,
        source_name: Optional[str] = None,
    ) -> int:
        """
        Load flood polygons from a shapefile into the database.
        
        Args:
            shapefile_path: Path to .shp file
            event_id: Associated flood event ID
            source_name: Optional label for the source file
        
        Returns:
            Number of polygons loaded
        """
        path = Path(shapefile_path)
        if not path.exists():
            raise FileNotFoundError(f"Shapefile not found: {shapefile_path}")

        logger.info(f"Loading flood polygons from: {shapefile_path}")

        # Read the shapefile
        gdf = gpd.read_file(shapefile_path)

        # Ensure WGS-84 CRS
        if gdf.crs is None:
            gdf = gdf.set_crs(CRS_WGS84)
        else:
            gdf = gdf.to_crs(CRS_WGS84)

        logger.info(f"Loaded {len(gdf)} polygons, CRS: {gdf.crs}")

        # Detect depth column
        depth_col = self._find_depth_column(gdf)
        if depth_col:
            logger.info(f"Depth column detected: '{depth_col}'")

        # Clear existing zones for this event (fresh import)
        deleted = await self.repo.delete_flood_zones_for_event(event_id)
        if deleted:
            logger.info(f"Cleared {deleted} existing zones for event {event_id}")

        # Insert each polygon
        count = 0
        for idx, row in gdf.iterrows():
            geometry = row.geometry
            if geometry is None or geometry.is_empty:
                continue

            # Extract depth info
            max_depth = None
            if depth_col and row[depth_col] is not None:
                try:
                    max_depth = float(row[depth_col])
                except (ValueError, TypeError):
                    pass

            # Compute area in km²
            area_km2 = None
            try:
                # Approximate: 1 degree ≈ 111 km
                area_km2 = geometry.area * (111.0 ** 2)
            except Exception:
                pass

            # Insert into database
            await self.repo.insert_flood_zone(
                event_id=event_id,
                geometry_wkt=geometry.wkt,
                max_depth=max_depth,
                avg_depth=max_depth,  # Will be refined by intersection analysis
                area_km2=area_km2,
                source_file=source_name or path.name,
            )
            count += 1

        logger.info(f"Loaded {count} flood polygons for event {event_id}")
        return count

    async def load_from_geojson(
        self, geojson_path: str, event_id: int
    ) -> int:
        """Load flood polygons from a GeoJSON file."""
        return await self.load_from_shapefile(geojson_path, event_id)

    def load_as_geodataframe(self, shapefile_path: str) -> gpd.GeoDataFrame:
        """
        Load a shapefile as a GeoDataFrame (for in-memory operations).
        Used by the graph builder for flood intersection without DB.
        """
        gdf = gpd.read_file(shapefile_path)
        if gdf.crs is None:
            gdf = gdf.set_crs(CRS_WGS84)
        else:
            gdf = gdf.to_crs(CRS_WGS84)
        return gdf

    @staticmethod
    def _find_depth_column(gdf: gpd.GeoDataFrame) -> Optional[str]:
        """Auto-detect the depth column in the GeoDataFrame."""
        depth_keywords = ["depth", "water_depth", "flood_depth", "max_depth", "wdepth"]
        for col in gdf.columns:
            if any(kw in col.lower() for kw in depth_keywords):
                return col
        return None
