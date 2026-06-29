"""
Flood data API endpoints — flood zones, depth checks, event management.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

from auth.middleware import get_current_user, CurrentUser
from database.connection import get_db
from database.flood_repository import FloodRepository
from flood.downloader import CopernicusDownloader
from utils.logger import api_logger as logger
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/flood", tags=["Flood Data"])


# ── Models ───────────────────────────────────────────────────────────────────

class FloodDepthRequest(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)
    event_id: Optional[int] = None


class FloodDepthResponse(BaseModel):
    lat: float
    lon: float
    depth: float
    is_flooded: bool
    severity: str
    message: str


class FloodEventResponse(BaseModel):
    id: int
    activation_id: str
    event_name: str
    country: str
    region: str
    start_date: str
    is_active: bool


class DownloadFloodRequest(BaseModel):
    """Request to download new flood data from Copernicus EMS."""
    activation_id: str = Field(..., description="e.g. EMSR838")
    event_name: str
    country: str = "Pakistan"
    region: str = "Punjab"


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/active", response_model=List[FloodEventResponse])
async def get_active_floods(
    db: AsyncSession = Depends(get_db),
):
    """Get all currently active flood events."""
    repo = FloodRepository(db)
    events = await repo.get_active_events()
    return [
        FloodEventResponse(
            id=e["id"],
            activation_id=e["activation_id"],
            event_name=e["event_name"],
            country=e["country"],
            region=e["region"],
            start_date=str(e["start_date"]),
            is_active=e["is_active"],
        )
        for e in events
    ]


@router.post("/depth", response_model=FloodDepthResponse)
async def check_flood_depth(
    request: FloodDepthRequest,
    db: AsyncSession = Depends(get_db),
):
    """Check flood depth at a specific coordinate."""
    repo = FloodRepository(db)
    depth = await repo.get_flood_depth_at_point(
        request.lat, request.lon, request.event_id
    )

    if depth == 0:
        severity = "none"
        message = "Location is safe — not in any flood zone."
    elif depth <= 0.3:
        severity = "low"
        message = "Shallow flooding — most vehicles can pass."
    elif depth <= 0.6:
        severity = "moderate"
        message = "Moderate flooding — cars cannot pass, SUVs/trucks may."
    elif depth <= 1.0:
        severity = "high"
        message = "Deep flooding — specialist vehicles only."
    else:
        severity = "critical"
        message = "Extreme flooding — do not attempt. Risk to life."

    return FloodDepthResponse(
        lat=request.lat,
        lon=request.lon,
        depth=depth,
        is_flooded=depth > 0,
        severity=severity,
        message=message,
    )


@router.get("/zones")
async def get_flood_zones(
    event_id: int = Query(..., description="Flood event ID"),
    db: AsyncSession = Depends(get_db),
):
    """Get all flood zones (polygons) for an event."""
    repo = FloodRepository(db)
    zones = await repo.get_flood_zones_for_event(event_id)
    return {"event_id": event_id, "zones": zones, "count": len(zones)}


@router.post("/download")
async def download_flood_data(
    request: DownloadFloodRequest,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Download flood data from Copernicus EMS for a new activation.
    Creates a flood event and imports polygon data.
    """
    logger.info(f"Download request for activation: {request.activation_id}")

    # Check if already in database
    repo = FloodRepository(db)
    existing = await repo.get_event_by_activation_id(request.activation_id)
    if existing:
        return {
            "status": "exists",
            "message": f"Activation {request.activation_id} already in database",
            "event_id": existing["id"],
        }

    # Download from Copernicus
    downloader = CopernicusDownloader()
    try:
        success, shapefile_path, message = await downloader.download_flood_data(
            request.activation_id
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=message,
            )

        # Create flood event in database
        event_id = await repo.create_flood_event(
            activation_id=request.activation_id,
            event_name=request.event_name,
            country=request.country,
            region=request.region,
            start_date=datetime.utcnow(),
        )

        return {
            "status": "downloaded",
            "message": message,
            "event_id": event_id,
            "shapefile_path": shapefile_path,
        }

    finally:
        await downloader.close()


@router.get("/events")
async def list_flood_events(
    db: AsyncSession = Depends(get_db),
):
    """List all flood events (active and historical)."""
    repo = FloodRepository(db)
    events = await repo.get_active_events()
    return {"events": events, "count": len(events)}
