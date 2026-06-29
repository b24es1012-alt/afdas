"""
Building flood analytics — identifies repeatedly affected infrastructure.
"""

from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from database.analytics_repository import AnalyticsRepository
from utils.logger import logger


class BuildingAnalytics:
    """
    Generates building-level flood analysis reports.
    
    Questions answered:
    - Which hospitals flood every year?
    - Which schools are at highest risk?
    - Which shelters are actually safe during floods?
    """

    def __init__(self, session: AsyncSession):
        self.repo = AnalyticsRepository(session)

    async def most_affected_hospitals(self, limit: int = 10) -> List[dict]:
        """Get hospitals most frequently affected by flooding."""
        return await self.repo.most_affected_buildings(
            building_type="hospital", limit=limit
        )

    async def most_affected_schools(self, limit: int = 10) -> List[dict]:
        """Get schools most frequently affected by flooding."""
        return await self.repo.most_affected_buildings(
            building_type="school", limit=limit
        )

    async def infrastructure_risk_report(self, event_id: int) -> dict:
        """Generate a comprehensive infrastructure risk report."""
        report = await self.repo.infrastructure_risk_report(event_id)

        # Enhance with details
        hospitals = await self.repo.most_affected_buildings(
            building_type="hospital", limit=5
        )
        schools = await self.repo.most_affected_buildings(
            building_type="school", limit=5
        )

        report["top_affected_hospitals"] = hospitals
        report["top_affected_schools"] = schools
        return report
