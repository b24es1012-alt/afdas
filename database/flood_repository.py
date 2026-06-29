"""
Flood data repository — CRUD operations for flood events, zones, and affected infrastructure.
Uses PostGIS spatial queries for efficient geospatial lookups.
"""

from typing import List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from datetime import datetime

from utils.logger import logger


class FloodRepository:
    """Repository for flood-related database operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    # ══════════════════════════════════════════════════════════════════════
    # FLOOD EVENTS
    # ══════════════════════════════════════════════════════════════════════

    async def create_flood_event(
        self,
        activation_id: str,
        event_name: str,
        country: str,
        region: str,
        start_date: datetime,
        data_source: str = "copernicus_ems",
    ) -> int:
        """Insert a new flood event and return its ID."""
        result = await self.session.execute(
            text("""
                INSERT INTO flood_events (activation_id, event_name, country, region, 
                                          start_date, data_source, is_active, created_at)
                VALUES (:activation_id, :event_name, :country, :region, 
                        :start_date, :data_source, TRUE, NOW())
                RETURNING id
            """),
            {
                "activation_id": activation_id,
                "event_name": event_name,
                "country": country,
                "region": region,
                "start_date": start_date,
                "data_source": data_source,
            },
        )
        event_id = result.scalar_one()
        logger.info(f"Created flood event {activation_id} with ID {event_id}")
        return event_id

    async def get_active_events(self) -> List[dict]:
        """Get all currently active flood events."""
        result = await self.session.execute(
            text("""
                SELECT id, activation_id, event_name, country, region, 
                       start_date, is_active, created_at
                FROM flood_events 
                WHERE is_active = TRUE
                ORDER BY start_date DESC
            """)
        )
        return [dict(row._mapping) for row in result.fetchall()]

    async def get_event_by_activation_id(self, activation_id: str) -> Optional[dict]:
        """Find a flood event by Copernicus activation ID."""
        result = await self.session.execute(
            text("""
                SELECT id, activation_id, event_name, country, region, 
                       start_date, end_date, is_active, data_source
                FROM flood_events 
                WHERE activation_id = :activation_id
            """),
            {"activation_id": activation_id},
        )
        row = result.fetchone()
        return dict(row._mapping) if row else None

    async def deactivate_event(self, event_id: int, end_date: datetime = None) -> None:
        """Mark a flood event as inactive (flood has ended)."""
        await self.session.execute(
            text("""
                UPDATE flood_events 
                SET is_active = FALSE, end_date = :end_date, updated_at = NOW()
                WHERE id = :event_id
            """),
            {"event_id": event_id, "end_date": end_date or datetime.utcnow()},
        )

    # ══════════════════════════════════════════════════════════════════════
    # FLOOD ZONES (Polygons)
    # ══════════════════════════════════════════════════════════════════════

    async def insert_flood_zone(
        self,
        event_id: int,
        geometry_wkt: str,
        max_depth: Optional[float] = None,
        avg_depth: Optional[float] = None,
        area_km2: Optional[float] = None,
        source_file: Optional[str] = None,
    ) -> int:
        """Insert a flood polygon zone."""
        result = await self.session.execute(
            text("""
                INSERT INTO flood_zones (event_id, geometry, max_depth, avg_depth, 
                                         area_km2, source_file, created_at)
                VALUES (:event_id, ST_GeomFromText(:geometry_wkt, 4326), :max_depth, 
                        :avg_depth, :area_km2, :source_file, NOW())
                RETURNING id
            """),
            {
                "event_id": event_id,
                "geometry_wkt": geometry_wkt,
                "max_depth": max_depth,
                "avg_depth": avg_depth,
                "area_km2": area_km2,
                "source_file": source_file,
            },
        )
        return result.scalar_one()

    async def bulk_insert_flood_zones(self, zones: List[dict]) -> int:
        """Bulk insert flood zones. Returns count of inserted zones."""
        if not zones:
            return 0

        count = 0
        for zone in zones:
            await self.insert_flood_zone(**zone)
            count += 1

        logger.info(f"Inserted {count} flood zones for event {zones[0].get('event_id')}")
        return count

    async def get_flood_zones_for_event(self, event_id: int) -> List[dict]:
        """Get all flood zones for a specific event."""
        result = await self.session.execute(
            text("""
                SELECT id, event_id, 
                       ST_AsText(geometry) as geometry_wkt,
                       max_depth, avg_depth, area_km2,
                       ST_Y(ST_Centroid(geometry)) as centroid_lat,
                       ST_X(ST_Centroid(geometry)) as centroid_lon
                FROM flood_zones 
                WHERE event_id = :event_id
            """),
            {"event_id": event_id},
        )
        return [dict(row._mapping) for row in result.fetchall()]

    async def check_point_in_flood(
        self, lat: float, lon: float, event_id: Optional[int] = None
    ) -> Optional[dict]:
        """
        Check if a point is inside any active flood zone.
        Returns flood zone info if flooded, None if safe.
        """
        event_filter = ""
        params = {"lon": lon, "lat": lat}

        if event_id:
            event_filter = "AND fz.event_id = :event_id"
            params["event_id"] = event_id
        else:
            event_filter = "AND fe.is_active = TRUE"

        result = await self.session.execute(
            text(f"""
                SELECT fz.id, fz.event_id, fz.max_depth, fz.avg_depth,
                       fe.activation_id, fe.event_name
                FROM flood_zones fz
                JOIN flood_events fe ON fe.id = fz.event_id
                WHERE ST_Intersects(
                    fz.geometry, 
                    ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)
                )
                {event_filter}
                ORDER BY fz.max_depth DESC
                LIMIT 1
            """),
            params,
        )
        row = result.fetchone()
        return dict(row._mapping) if row else None

    async def get_flood_depth_at_point(
        self, lat: float, lon: float, event_id: Optional[int] = None
    ) -> float:
        """Get flood depth at a specific point. Returns 0.0 if not flooded."""
        zone = await self.check_point_in_flood(lat, lon, event_id)
        if zone is None:
            return 0.0
        return zone.get("max_depth") or 1.0  # Default 1.0 if polygon exists but no depth

    # ══════════════════════════════════════════════════════════════════════
    # FLOODED ROADS
    # ══════════════════════════════════════════════════════════════════════

    async def insert_flooded_road(
        self,
        event_id: int,
        road_id: int,
        max_depth: float,
        avg_depth: float,
        flooded_percentage: float,
        risk_score: float,
    ) -> int:
        """Record a road as flooded."""
        result = await self.session.execute(
            text("""
                INSERT INTO flooded_roads (event_id, road_id, max_depth, avg_depth, 
                                           flooded_percentage, risk_score, created_at)
                VALUES (:event_id, :road_id, :max_depth, :avg_depth, 
                        :flooded_percentage, :risk_score, NOW())
                ON CONFLICT (event_id, road_id) 
                DO UPDATE SET max_depth = EXCLUDED.max_depth,
                             avg_depth = EXCLUDED.avg_depth,
                             flooded_percentage = EXCLUDED.flooded_percentage,
                             risk_score = EXCLUDED.risk_score
                RETURNING id
            """),
            {
                "event_id": event_id,
                "road_id": road_id,
                "max_depth": max_depth,
                "avg_depth": avg_depth,
                "flooded_percentage": flooded_percentage,
                "risk_score": risk_score,
            },
        )
        return result.scalar_one()

    async def get_flooded_roads(self, event_id: int) -> List[dict]:
        """Get all flooded roads for an event."""
        result = await self.session.execute(
            text("""
                SELECT fr.id, fr.road_id, fr.max_depth, fr.avg_depth, 
                       fr.flooded_percentage, fr.risk_score,
                       r.name as road_name, r.road_type
                FROM flooded_roads fr
                JOIN roads r ON r.id = fr.road_id
                WHERE fr.event_id = :event_id
                ORDER BY fr.risk_score DESC
            """),
            {"event_id": event_id},
        )
        return [dict(row._mapping) for row in result.fetchall()]

    # ══════════════════════════════════════════════════════════════════════
    # FLOODED BUILDINGS
    # ══════════════════════════════════════════════════════════════════════

    async def insert_flooded_building(
        self,
        event_id: int,
        building_id: int,
        water_depth: float,
        is_accessible: bool = True,
        evacuation_needed: bool = False,
    ) -> int:
        """Record a building as affected by flooding."""
        result = await self.session.execute(
            text("""
                INSERT INTO flooded_buildings (event_id, building_id, water_depth, 
                                               is_accessible, evacuation_needed, created_at)
                VALUES (:event_id, :building_id, :water_depth, 
                        :is_accessible, :evacuation_needed, NOW())
                ON CONFLICT (event_id, building_id) 
                DO UPDATE SET water_depth = EXCLUDED.water_depth,
                             is_accessible = EXCLUDED.is_accessible,
                             evacuation_needed = EXCLUDED.evacuation_needed
                RETURNING id
            """),
            {
                "event_id": event_id,
                "building_id": building_id,
                "water_depth": water_depth,
                "is_accessible": is_accessible,
                "evacuation_needed": evacuation_needed,
            },
        )
        return result.scalar_one()

    async def get_flooded_buildings(
        self, event_id: int, building_type: Optional[str] = None
    ) -> List[dict]:
        """Get flooded buildings, optionally filtered by type."""
        type_filter = ""
        params = {"event_id": event_id}

        if building_type:
            type_filter = "AND b.building_type = :building_type"
            params["building_type"] = building_type

        result = await self.session.execute(
            text(f"""
                SELECT fb.id, fb.building_id, fb.water_depth, 
                       fb.is_accessible, fb.evacuation_needed,
                       b.name, b.building_type, b.latitude, b.longitude
                FROM flooded_buildings fb
                JOIN buildings b ON b.id = fb.building_id
                WHERE fb.event_id = :event_id {type_filter}
                ORDER BY fb.water_depth DESC
            """),
            params,
        )
        return [dict(row._mapping) for row in result.fetchall()]

    # ══════════════════════════════════════════════════════════════════════
    # SPATIAL QUERIES
    # ══════════════════════════════════════════════════════════════════════

    async def find_roads_intersecting_flood(
        self, event_id: int
    ) -> List[dict]:
        """Find all roads that intersect active flood zones for an event."""
        result = await self.session.execute(
            text("""
                SELECT r.id as road_id, r.name, r.road_type,
                       ST_AsText(r.geometry) as road_wkt,
                       MAX(fz.max_depth) as max_flood_depth,
                       AVG(fz.avg_depth) as avg_flood_depth,
                       (ST_Length(ST_Intersection(r.geometry, fz.geometry)::geography) /
                        ST_Length(r.geometry::geography)) * 100 as flooded_percentage
                FROM roads r
                JOIN flood_zones fz ON ST_Intersects(r.geometry, fz.geometry)
                WHERE fz.event_id = :event_id
                GROUP BY r.id, r.name, r.road_type, r.geometry
            """),
            {"event_id": event_id},
        )
        return [dict(row._mapping) for row in result.fetchall()]

    async def find_buildings_in_flood(
        self, event_id: int, building_type: Optional[str] = None
    ) -> List[dict]:
        """Find all buildings inside flood zones."""
        type_filter = ""
        params = {"event_id": event_id}

        if building_type:
            type_filter = "AND b.building_type = :building_type"
            params["building_type"] = building_type

        result = await self.session.execute(
            text(f"""
                SELECT b.id, b.name, b.building_type, b.latitude, b.longitude,
                       fz.max_depth as flood_depth
                FROM buildings b
                JOIN flood_zones fz ON ST_Intersects(
                    fz.geometry,
                    ST_SetSRID(ST_MakePoint(b.longitude, b.latitude), 4326)
                )
                WHERE fz.event_id = :event_id {type_filter}
                ORDER BY fz.max_depth DESC
            """),
            params,
        )
        return [dict(row._mapping) for row in result.fetchall()]

    async def delete_flood_zones_for_event(self, event_id: int) -> int:
        """Delete all flood zones for an event (before re-importing updated data)."""
        result = await self.session.execute(
            text("DELETE FROM flood_zones WHERE event_id = :event_id"),
            {"event_id": event_id},
        )
        return result.rowcount
