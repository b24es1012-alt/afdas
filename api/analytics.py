"""
Analytics API endpoints — post-flood analysis and reporting.
"""

from fastapi import APIRouter, Depends, Query
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from auth.middleware import get_current_user, CurrentUser
from database.connection import get_db
from database.analytics_repository import AnalyticsRepository
from utils.logger import api_logger as logger

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/roads/most-flooded")
async def most_flooded_roads(
    event_id: Optional[int] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Get roads most frequently affected by flooding."""
    repo = AnalyticsRepository(db)
    roads = await repo.most_flooded_roads(limit=limit, event_id=event_id)
    return {"roads": roads, "count": len(roads)}


@router.get("/buildings/most-affected")
async def most_affected_buildings(
    building_type: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Get buildings most frequently affected by flooding."""
    repo = AnalyticsRepository(db)
    buildings = await repo.most_affected_buildings(
        building_type=building_type, limit=limit
    )
    return {"buildings": buildings, "count": len(buildings)}


@router.get("/event/{event_id}/summary")
async def flood_event_summary(
    event_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get comprehensive summary of a flood event's impact."""
    repo = AnalyticsRepository(db)
    summary = await repo.flood_event_summary(event_id)
    if not summary:
        return {"error": "Event not found"}
    return summary


@router.get("/event/{event_id}/infrastructure-risk")
async def infrastructure_risk_report(
    event_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Generate infrastructure risk report for a flood event."""
    repo = AnalyticsRepository(db)
    report = await repo.infrastructure_risk_report(event_id)
    return report
