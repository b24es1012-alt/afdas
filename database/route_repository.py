"""
Route history repository — stores all generated routes for analytics.
"""

from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from datetime import datetime

from utils.logger import logger


class RouteRepository:
    """Repository for route history database operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def save_route(
        self,
        event_id: int,
        user_id: Optional[int],
        start_lat: float,
        start_lon: float,
        end_lat: float,
        end_lon: float,
        vehicle_type: str,
        total_distance_m: float,
        estimated_time_s: float,
        risk_score: float,
        route_geometry_wkt: str,
        flooded_segments: int = 0,
        is_reroute: bool = False,
    ) -> int:
        """Save a computed route to history."""
        result = await self.session.execute(
            text("""
                INSERT INTO route_history (event_id, user_id, start_lat, start_lon,
                                           end_lat, end_lon, vehicle_type,
                                           total_distance_m, estimated_time_s,
                                           risk_score, route_geometry,
                                           flooded_segments, is_reroute, created_at)
                VALUES (:event_id, :user_id, :start_lat, :start_lon,
                        :end_lat, :end_lon, :vehicle_type,
                        :total_distance_m, :estimated_time_s,
                        :risk_score, ST_GeomFromText(:route_wkt, 4326),
                        :flooded_segments, :is_reroute, NOW())
                RETURNING id
            """),
            {
                "event_id": event_id,
                "user_id": user_id,
                "start_lat": start_lat,
                "start_lon": start_lon,
                "end_lat": end_lat,
                "end_lon": end_lon,
                "vehicle_type": vehicle_type,
                "total_distance_m": total_distance_m,
                "estimated_time_s": estimated_time_s,
                "risk_score": risk_score,
                "route_wkt": route_geometry_wkt,
                "flooded_segments": flooded_segments,
                "is_reroute": is_reroute,
            },
        )
        route_id = result.scalar_one()
        logger.info(f"Saved route {route_id}: {total_distance_m:.0f}m, risk={risk_score:.2f}")
        return route_id
