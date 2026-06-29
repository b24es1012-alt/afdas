"""
Road data repository — CRUD for road network stored in PostGIS.
"""

from typing import List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from utils.logger import logger


class RoadRepository:
    """Repository for road network database operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def insert_road(
        self,
        osm_id: int,
        name: Optional[str],
        road_type: str,
        geometry_wkt: str,
        length_m: float,
        max_speed: Optional[float] = None,
        lanes: Optional[int] = None,
        is_bridge: bool = False,
        is_tunnel: bool = False,
        is_oneway: bool = False,
        surface: Optional[str] = None,
        event_id: Optional[int] = None,
    ) -> int:
        """Insert a road segment."""
        result = await self.session.execute(
            text("""
                INSERT INTO roads (osm_id, name, road_type, geometry, length_m, 
                                   max_speed, lanes, is_bridge, is_tunnel, 
                                   is_oneway, surface, event_id, created_at)
                VALUES (:osm_id, :name, :road_type, ST_GeomFromText(:geometry_wkt, 4326), 
                        :length_m, :max_speed, :lanes, :is_bridge, :is_tunnel, 
                        :is_oneway, :surface, :event_id, NOW())
                ON CONFLICT (osm_id) DO UPDATE SET
                    name = EXCLUDED.name,
                    road_type = EXCLUDED.road_type,
                    geometry = EXCLUDED.geometry,
                    length_m = EXCLUDED.length_m
                RETURNING id
            """),
            {
                "osm_id": osm_id,
                "name": name,
                "road_type": road_type,
                "geometry_wkt": geometry_wkt,
                "length_m": length_m,
                "max_speed": max_speed,
                "lanes": lanes,
                "is_bridge": is_bridge,
                "is_tunnel": is_tunnel,
                "is_oneway": is_oneway,
                "surface": surface,
                "event_id": event_id,
            },
        )
        return result.scalar_one()

    async def bulk_insert_roads(self, roads: List[dict]) -> int:
        """Bulk insert road segments. Returns count."""
        count = 0
        for road in roads:
            await self.insert_road(**road)
            count += 1
        logger.info(f"Inserted {count} roads into database.")
        return count

    async def get_roads_in_bbox(
        self,
        min_lat: float,
        min_lon: float,
        max_lat: float,
        max_lon: float,
    ) -> List[dict]:
        """Get all roads within a bounding box."""
        result = await self.session.execute(
            text("""
                SELECT id, osm_id, name, road_type, 
                       ST_AsText(geometry) as geometry_wkt,
                       length_m, max_speed, is_bridge, is_oneway
                FROM roads
                WHERE ST_Intersects(
                    geometry,
                    ST_MakeEnvelope(:min_lon, :min_lat, :max_lon, :max_lat, 4326)
                )
            """),
            {
                "min_lat": min_lat,
                "min_lon": min_lon,
                "max_lat": max_lat,
                "max_lon": max_lon,
            },
        )
        return [dict(row._mapping) for row in result.fetchall()]

    async def get_roads_for_place(self, place_name: str) -> List[dict]:
        """Get all roads associated with a place (by event context)."""
        result = await self.session.execute(
            text("""
                SELECT id, osm_id, name, road_type, 
                       ST_AsText(geometry) as geometry_wkt,
                       length_m, max_speed, is_bridge, is_oneway
                FROM roads
                ORDER BY id
            """),
        )
        return [dict(row._mapping) for row in result.fetchall()]

    async def get_road_by_osm_id(self, osm_id: int) -> Optional[dict]:
        """Find a road by its OSM ID."""
        result = await self.session.execute(
            text("""
                SELECT id, osm_id, name, road_type, 
                       ST_AsText(geometry) as geometry_wkt,
                       length_m, max_speed, is_bridge, is_oneway
                FROM roads 
                WHERE osm_id = :osm_id
            """),
            {"osm_id": osm_id},
        )
        row = result.fetchone()
        return dict(row._mapping) if row else None

    async def find_nearest_road(self, lat: float, lon: float) -> Optional[dict]:
        """Find the nearest road to a point."""
        result = await self.session.execute(
            text("""
                SELECT id, osm_id, name, road_type,
                       ST_AsText(geometry) as geometry_wkt,
                       ST_Distance(
                           geometry::geography, 
                           ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography
                       ) as distance_m
                FROM roads
                ORDER BY geometry <-> ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)
                LIMIT 1
            """),
            {"lat": lat, "lon": lon},
        )
        row = result.fetchone()
        return dict(row._mapping) if row else None

    async def count_roads(self) -> int:
        """Get total number of roads in database."""
        result = await self.session.execute(text("SELECT COUNT(*) FROM roads"))
        return result.scalar_one()

    async def delete_roads_for_event(self, event_id: int) -> int:
        """Delete all roads associated with an event (for re-import)."""
        result = await self.session.execute(
            text("DELETE FROM roads WHERE event_id = :event_id"),
            {"event_id": event_id},
        )
        return result.rowcount
