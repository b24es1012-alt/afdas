"""
Building/infrastructure repository — CRUD for hospitals, shelters, schools, etc.
"""

from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from utils.logger import logger


class BuildingRepository:
    """Repository for building and infrastructure database operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def insert_building(
        self,
        osm_id: Optional[int],
        name: str,
        building_type: str,
        latitude: float,
        longitude: float,
        address: Optional[str] = None,
        phone: Optional[str] = None,
        capacity: Optional[int] = None,
        is_emergency_facility: bool = False,
        event_id: Optional[int] = None,
    ) -> int:
        """Insert a building/POI."""
        result = await self.session.execute(
            text("""
                INSERT INTO buildings (osm_id, name, building_type, latitude, longitude,
                                       address, phone, capacity, is_emergency_facility,
                                       event_id, created_at)
                VALUES (:osm_id, :name, :building_type, :latitude, :longitude,
                        :address, :phone, :capacity, :is_emergency_facility,
                        :event_id, NOW())
                ON CONFLICT (osm_id) DO UPDATE SET
                    name = EXCLUDED.name,
                    building_type = EXCLUDED.building_type
                RETURNING id
            """),
            {
                "osm_id": osm_id,
                "name": name,
                "building_type": building_type,
                "latitude": latitude,
                "longitude": longitude,
                "address": address,
                "phone": phone,
                "capacity": capacity,
                "is_emergency_facility": is_emergency_facility,
                "event_id": event_id,
            },
        )
        return result.scalar_one()


    async def bulk_insert_buildings(self, buildings: List[dict]) -> int:
        """Bulk insert buildings. Returns count."""
        count = 0
        for building in buildings:
            await self.insert_building(**building)
            count += 1
        logger.info(f"Inserted {count} buildings into database.")
        return count

    async def get_buildings_by_type(
        self, building_type: str, event_id: Optional[int] = None
    ) -> List[dict]:
        """Get all buildings of a specific type."""
        event_filter = ""
        params = {"building_type": building_type}
        if event_id:
            event_filter = "AND event_id = :event_id"
            params["event_id"] = event_id

        result = await self.session.execute(
            text(f"""
                SELECT id, osm_id, name, building_type, latitude, longitude,
                       address, phone, capacity, is_emergency_facility
                FROM buildings
                WHERE building_type = :building_type {event_filter}
                ORDER BY name
            """),
            params,
        )
        return [dict(row._mapping) for row in result.fetchall()]

    async def find_nearest_buildings(
        self,
        lat: float,
        lon: float,
        building_type: Optional[str] = None,
        limit: int = 5,
    ) -> List[dict]:
        """Find nearest buildings to a point, optionally filtered by type."""
        type_filter = ""
        params = {"lat": lat, "lon": lon, "limit": limit}
        if building_type:
            type_filter = "AND building_type = :building_type"
            params["building_type"] = building_type

        result = await self.session.execute(
            text(f"""
                SELECT id, name, building_type, latitude, longitude,
                       address, phone, capacity, is_emergency_facility,
                       ST_Distance(
                           ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)::geography,
                           ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography
                       ) as distance_m
                FROM buildings
                WHERE TRUE {type_filter}
                ORDER BY ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)
                         <-> ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)
                LIMIT :limit
            """),
            params,
        )
        return [dict(row._mapping) for row in result.fetchall()]

    async def get_safe_buildings(
        self,
        event_id: int,
        building_type: str,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
    ) -> List[dict]:
        """Get buildings of a type that are NOT in flood zones."""
        order_clause = "ORDER BY b.name"
        params = {"event_id": event_id, "building_type": building_type}

        if lat and lon:
            order_clause = (
                "ORDER BY ST_SetSRID(ST_MakePoint(b.longitude, b.latitude), 4326)"
                " <-> ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)"
            )
            params["lat"] = lat
            params["lon"] = lon

        result = await self.session.execute(
            text(f"""
                SELECT b.id, b.name, b.building_type, b.latitude, b.longitude,
                       b.address, b.phone, b.capacity
                FROM buildings b
                WHERE b.building_type = :building_type
                  AND NOT EXISTS (
                      SELECT 1 FROM flood_zones fz
                      WHERE fz.event_id = :event_id
                        AND ST_Intersects(
                            fz.geometry,
                            ST_SetSRID(ST_MakePoint(b.longitude, b.latitude), 4326)
                        )
                  )
                {order_clause}
                LIMIT 10
            """),
            params,
        )
        return [dict(row._mapping) for row in result.fetchall()]

    async def count_buildings(self, building_type: Optional[str] = None) -> int:
        """Count buildings, optionally by type."""
        if building_type:
            result = await self.session.execute(
                text("SELECT COUNT(*) FROM buildings WHERE building_type = :bt"),
                {"bt": building_type},
            )
        else:
            result = await self.session.execute(text("SELECT COUNT(*) FROM buildings"))
        return result.scalar_one()
