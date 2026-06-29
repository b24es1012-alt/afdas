"""
Flood event analytics — event-level statistics and comparisons.
"""

from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from database.analytics_repository import AnalyticsRepository
from database.flood_repository import FloodRepository
from utils.logger import logger


class EventAnalytics:
    """
    Generates event-level flood analysis.
    
    Questions answered:
    - How does this flood compare to previous ones?
    - What was the total impact?
    - Which areas were most affected?
    """

    def __init__(self, session: AsyncSession):
        self.analytics_repo = AnalyticsRepository(session)
        self.flood_repo = FloodRepository(session)

    async def event_summary(self, event_id: int) -> dict:
        """Get comprehensive event summary."""
        return await self.analytics_repo.flood_event_summary(event_id)

    async def event_comparison(self, event_ids: List[int]) -> List[dict]:
        """Compare multiple flood events side by side."""
        comparisons = []
        for eid in event_ids:
            summary = await self.analytics_repo.flood_event_summary(eid)
            if summary:
                comparisons.append(summary)
        return comparisons

    async def get_most_requested_routes(
        self, event_id: int, limit: int = 10
    ) -> List[dict]:
        """Get most commonly requested evacuation routes."""
        from database.route_repository import RouteRepository
        route_repo = RouteRepository(self.flood_repo.session)
        return await route_repo.get_most_requested_routes(event_id, limit)
