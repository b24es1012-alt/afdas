"""
Road flood analytics — identifies repeatedly affected road infrastructure.
"""

from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from database.analytics_repository import AnalyticsRepository
from utils.logger import logger


class RoadAnalytics:
    """
    Generates road-level flood analysis reports.
    
    Questions answered:
    - Which roads flood most frequently?
    - What is the average flood depth on key roads?
    - Which roads are critical bottlenecks when flooded?
    """

    def __init__(self, session: AsyncSession):
        self.repo = AnalyticsRepository(session)

    async def most_flooded_roads(
        self, event_id: Optional[int] = None, limit: int = 20
    ) -> List[dict]:
        """Get roads with highest flood frequency."""
        return await self.repo.most_flooded_roads(limit=limit, event_id=event_id)

    async def road_flood_summary(self, event_id: int) -> dict:
        """Summary statistics about road flooding for an event."""
        roads = await self.repo.most_flooded_roads(event_id=event_id, limit=1000)

        if not roads:
            return {"total_flooded": 0}

        depths = [r["worst_depth"] for r in roads if r.get("worst_depth")]
        percentages = [r["avg_flooded_pct"] for r in roads if r.get("avg_flooded_pct")]

        return {
            "total_flooded_roads": len(roads),
            "avg_max_depth": sum(depths) / len(depths) if depths else 0,
            "max_depth": max(depths) if depths else 0,
            "avg_flooded_percentage": sum(percentages) / len(percentages) if percentages else 0,
            "most_affected_types": self._count_road_types(roads),
        }

    @staticmethod
    def _count_road_types(roads: List[dict]) -> dict:
        """Count roads by type."""
        types = {}
        for road in roads:
            rt = road.get("road_type", "unknown")
            types[rt] = types.get(rt, 0) + 1
        return dict(sorted(types.items(), key=lambda x: x[1], reverse=True))
