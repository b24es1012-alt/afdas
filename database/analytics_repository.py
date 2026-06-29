"""
Analytics repository — queries for post-flood analysis and reporting.
"""

from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text


class AnalyticsRepository:
    """Repository for analytics and historical flood analysis queries."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def most_flooded_roads(
        self, limit: int = 20, event_id: Optional[int] = None
    ) -> List[dict]:
        """Roads with highest flood frequency or depth across events."""
        event_filter = ""
        params = {"limit": limit}
        if event_id:
            event_filter = "WHERE fr.event_id = :event_id"
            params["event_id"] = event_id

        result = await self.session.execute(
            text(f"""
                SELECT r.name, r.road_type, r.osm_id,
                       COUNT(DISTINCT fr.event_id) as flood_count,
                       MAX(fr.max_depth) as worst_depth,
                       AVG(fr.avg_depth) as avg_depth,
                       AVG(fr.flooded_percentage) as avg_flooded_pct
                FROM flooded_roads fr
                JOIN roads r ON r.id = fr.road_id
                {event_filter}
                GROUP BY r.id, r.name, r.road_type, r.osm_id
                ORDER BY flood_count DESC, worst_depth DESC
                LIMIT :limit
            """),
            params,
        )
        return [dict(row._mapping) for row in result.fetchall()]

    async def most_affected_buildings(
        self, building_type: Optional[str] = None, limit: int = 20
    ) -> List[dict]:
        """Buildings most frequently affected by floods."""
        type_filter = ""
        params = {"limit": limit}
        if building_type:
            type_filter = "AND b.building_type = :building_type"
            params["building_type"] = building_type

        result = await self.session.execute(
            text(f"""
                SELECT b.name, b.building_type, b.latitude, b.longitude,
                       COUNT(DISTINCT fb.event_id) as flood_count,
                       MAX(fb.water_depth) as worst_depth,
                       AVG(fb.water_depth) as avg_depth
                FROM flooded_buildings fb
                JOIN buildings b ON b.id = fb.building_id
                WHERE TRUE {type_filter}
                GROUP BY b.id, b.name, b.building_type, b.latitude, b.longitude
                ORDER BY flood_count DESC, worst_depth DESC
                LIMIT :limit
            """),
            params,
        )
        return [dict(row._mapping) for row in result.fetchall()]

    async def flood_event_summary(self, event_id: int) -> dict:
        """Get a summary of a flood event's impact."""
        result = await self.session.execute(
            text("""
                SELECT 
                    fe.activation_id,
                    fe.event_name,
                    fe.start_date,
                    fe.end_date,
                    (SELECT COUNT(*) FROM flood_zones WHERE event_id = :eid) as zone_count,
                    (SELECT COUNT(*) FROM flooded_roads WHERE event_id = :eid) as road_count,
                    (SELECT COUNT(*) FROM flooded_buildings WHERE event_id = :eid) as building_count,
                    (SELECT COUNT(*) FROM route_history WHERE event_id = :eid) as route_count,
                    (SELECT AVG(risk_score) FROM route_history WHERE event_id = :eid) as avg_route_risk
                FROM flood_events fe
                WHERE fe.id = :eid
            """),
            {"eid": event_id},
        )
        row = result.fetchone()
        return dict(row._mapping) if row else {}

    async def infrastructure_risk_report(self, event_id: int) -> dict:
        """Generate infrastructure risk report for a flood event."""
        hospitals = await self.session.execute(
            text("""
                SELECT COUNT(*) as total,
                       COUNT(CASE WHEN fb.id IS NOT NULL THEN 1 END) as flooded
                FROM buildings b
                LEFT JOIN flooded_buildings fb ON fb.building_id = b.id AND fb.event_id = :eid
                WHERE b.building_type = 'hospital'
            """),
            {"eid": event_id},
        )
        hosp_row = hospitals.fetchone()

        schools = await self.session.execute(
            text("""
                SELECT COUNT(*) as total,
                       COUNT(CASE WHEN fb.id IS NOT NULL THEN 1 END) as flooded
                FROM buildings b
                LEFT JOIN flooded_buildings fb ON fb.building_id = b.id AND fb.event_id = :eid
                WHERE b.building_type = 'school'
            """),
            {"eid": event_id},
        )
        school_row = schools.fetchone()

        return {
            "event_id": event_id,
            "hospitals": dict(hosp_row._mapping) if hosp_row else {},
            "schools": dict(school_row._mapping) if school_row else {},
        }
