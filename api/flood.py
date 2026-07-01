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
    country: str = "India"
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


@router.get("/zones/geojson")
async def get_flood_zones_geojson(
    event_id: Optional[int] = Query(None, description="Flood event ID (omit for all active)"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get flood zones as GeoJSON FeatureCollection for map display.
    If no event_id, returns all active flood zones.
    """
    from sqlalchemy import text

    if event_id:
        result = await db.execute(
            text("""
                SELECT fz.id, fz.event_id, fz.max_depth, fz.avg_depth, fz.area_km2,
                       ST_AsGeoJSON(fz.geometry) as geojson,
                       fe.event_name, fe.activation_id
                FROM flood_zones fz
                JOIN flood_events fe ON fe.id = fz.event_id
                WHERE fz.event_id = :event_id
            """),
            {"event_id": event_id},
        )
    else:
        result = await db.execute(
            text("""
                SELECT fz.id, fz.event_id, fz.max_depth, fz.avg_depth, fz.area_km2,
                       ST_AsGeoJSON(fz.geometry) as geojson,
                       fe.event_name, fe.activation_id
                FROM flood_zones fz
                JOIN flood_events fe ON fe.id = fz.event_id
                WHERE fe.is_active = TRUE
            """)
        )

    rows = result.fetchall()

    import json
    features = []
    for row in rows:
        r = dict(row._mapping)
        features.append({
            "type": "Feature",
            "geometry": json.loads(r["geojson"]),
            "properties": {
                "id": r["id"],
                "event_id": r["event_id"],
                "event_name": r["event_name"],
                "activation_id": r["activation_id"],
                "max_depth": r["max_depth"],
                "avg_depth": r["avg_depth"],
                "area_km2": r["area_km2"],
            }
        })

    return {
        "type": "FeatureCollection",
        "features": features,
        "count": len(features),
    }


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



# ── Admin: End Flood Event ───────────────────────────────────────────────────

class EndFloodRequest(BaseModel):
    """Request to mark a flood event as ended."""
    reason: Optional[str] = Field(None, max_length=500, description="Reason for ending (e.g. 'Water receded', 'False alarm')")


@router.post("/events/{event_id}/end")
async def end_flood_event(
    event_id: int,
    request: EndFloodRequest = None,
    db: AsyncSession = Depends(get_db),
    admin: CurrentUser = Depends(get_current_user),
):
    """
    Mark a flood event as ENDED (admin only).
    
    This will:
    1. Set is_active = FALSE and end_date = NOW()
    2. Invalidate cached graphs for affected areas (forces fresh route calculations)
    3. Flood zones remain in DB for historical analytics but stop affecting routing
    
    After ending:
    - New route calculations will NOT avoid previously flooded roads
    - Frontend will stop showing these flood zones (only active zones shown)
    - Historical data preserved for analytics/reports
    """
    from auth.middleware import require_admin

    # Require admin role
    if not admin or not admin.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required to end flood events",
        )

    repo = FloodRepository(db)

    # Check event exists
    from sqlalchemy import text
    result = await db.execute(
        text("SELECT id, activation_id, event_name, is_active, region FROM flood_events WHERE id = :id"),
        {"id": event_id},
    )
    row = result.fetchone()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Flood event {event_id} not found",
        )

    event = dict(row._mapping)

    if not event["is_active"]:
        return {
            "status": "already_ended",
            "message": f"Flood event '{event['event_name']}' is already marked as ended.",
            "event_id": event_id,
        }

    # Deactivate the event
    await repo.deactivate_event(event_id, end_date=datetime.utcnow())

    # Delete flood zone data for this event (cleanup)
    deleted_zones = await repo.delete_flood_zones_for_event(event_id)
    await db.commit()

    # Invalidate ONLY affected region's graph cache (not all cities)
    cache_cleared = 0
    try:
        from cache.graph_cache import GraphCache

        graph_cache = GraphCache()
        region = event.get("region", "")
        event_name = event.get("event_name", "")

        # Clear by region name
        if region:
            cache_cleared += await graph_cache.clear_by_region(region)
        # Clear by event ID (graphs tagged with this event)
        cache_cleared += await graph_cache.clear_by_event(str(event_id))

        logger.info(f"Cleared {cache_cleared} cached graphs for region '{region}' (event {event_id})")
    except Exception as e:
        logger.warning(f"Cache invalidation failed (non-fatal): {e}")

    reason = request.reason if request else None
    logger.info(
        f"Flood event ENDED by admin: {event['activation_id']} "
        f"({event['event_name']}) — reason: {reason or 'not specified'}"
    )

    return {
        "status": "ended",
        "message": f"Flood event '{event['event_name']}' has been marked as ended.",
        "event_id": event_id,
        "activation_id": event["activation_id"],
        "ended_at": datetime.utcnow().isoformat(),
        "reason": reason,
        "flood_zones_deleted": deleted_zones,
        "graphs_invalidated": cache_cleared,
        "note": "Flood data deleted. Only affected region's graphs cleared. Unrelated cities untouched.",
    }


@router.post("/events/{event_id}/reactivate")
async def reactivate_flood_event(
    event_id: int,
    db: AsyncSession = Depends(get_db),
    admin: CurrentUser = Depends(get_current_user),
):
    """
    Reactivate a previously ended flood event (admin only).
    Use if a flood was ended prematurely or water levels rose again.
    """
    if not admin or not admin.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    from sqlalchemy import text

    result = await db.execute(
        text("SELECT id, activation_id, event_name, is_active FROM flood_events WHERE id = :id"),
        {"id": event_id},
    )
    row = result.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail=f"Event {event_id} not found")

    event = dict(row._mapping)

    if event["is_active"]:
        return {"status": "already_active", "message": "Event is already active."}

    # Reactivate
    await db.execute(
        text("UPDATE flood_events SET is_active = TRUE, end_date = NULL, updated_at = NOW() WHERE id = :id"),
        {"id": event_id},
    )
    await db.commit()

    # Only clear graphs for the affected region (not all cities)
    try:
        from cache.graph_cache import GraphCache
        graph_cache = GraphCache()
        await graph_cache.clear_by_event(str(event_id))
    except Exception:
        pass

    logger.info(f"Flood event REACTIVATED: {event['activation_id']} ({event['event_name']})")

    return {
        "status": "reactivated",
        "message": f"Flood event '{event['event_name']}' is active again.",
        "event_id": event_id,
        "cache_cleared": True,
    }
