"""
Navigation API endpoints — flood-safe routing.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from auth.middleware import get_current_user, CurrentUser
from database.connection import get_db
from routing.service import RoutingService, RouteResult
from routing.rerouting import ReroutingService
from graph.loader import GraphLoader
from cache.graph_cache import GraphCache
from utils.logger import api_logger as logger
from utils.validators import validate_coordinates, validate_vehicle_type

router = APIRouter(prefix="/navigation", tags=["Navigation"])


# ── Request/Response Models ──────────────────────────────────────────────────

class RouteRequest(BaseModel):
    """Request body for route computation."""
    start_lat: float = Field(..., ge=-90, le=90)
    start_lon: float = Field(..., ge=-180, le=180)
    end_lat: float = Field(..., ge=-90, le=90)
    end_lon: float = Field(..., ge=-180, le=180)
    vehicle_type: str = Field(default="car")
    k: int = Field(default=3, ge=1, le=5)
    place: str = Field(default="Gujrat, Punjab, Pakistan")
    event_id: Optional[str] = None


class RerouteRequest(BaseModel):
    """Request for real-time rerouting."""
    current_lat: float = Field(..., ge=-90, le=90)
    current_lon: float = Field(..., ge=-180, le=180)
    end_lat: float = Field(..., ge=-90, le=90)
    end_lon: float = Field(..., ge=-180, le=180)
    vehicle_type: str = Field(default="car")
    place: str = Field(default="Gujrat, Punjab, Pakistan")
    event_id: Optional[str] = None


class RouteResponse(BaseModel):
    """Response containing computed routes."""
    success: bool
    routes: List[RouteResult]
    vehicle_type: str
    message: str


# ── Helper to get routing service ────────────────────────────────────────────

def _get_routing_service() -> RoutingService:
    """Create routing service with graph loader."""
    graph_cache = GraphCache()
    graph_loader = GraphLoader(graph_cache=graph_cache)
    return RoutingService(graph_loader=graph_loader)


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/route", response_model=RouteResponse)
async def calculate_route(
    request: RouteRequest,
    user: Optional[CurrentUser] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Compute flood-safe routes between two points.
    
    Returns up to K alternative routes ranked by safety.
    """
    # Validate vehicle type
    if not validate_vehicle_type(request.vehicle_type):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported vehicle type: {request.vehicle_type}",
        )

    logger.info(
        f"Route request: ({request.start_lat:.5f},{request.start_lon:.5f}) → "
        f"({request.end_lat:.5f},{request.end_lon:.5f}) [{request.vehicle_type}]"
    )

    try:
        service = _get_routing_service()
        routes = await service.find_routes(
            start_lat=request.start_lat,
            start_lon=request.start_lon,
            end_lat=request.end_lat,
            end_lon=request.end_lon,
            vehicle_type=request.vehicle_type,
            k=request.k,
            place=request.place,
            event_id=request.event_id,
        )

        if not routes:
            return RouteResponse(
                success=False,
                routes=[],
                vehicle_type=request.vehicle_type,
                message="No passable routes found. All roads may be flooded.",
            )

        # Save best route to database
        try:
            best = routes[0]
            user_id = user.user_id if user else None
            await db.execute(
                text("""
                    INSERT INTO route_history (event_id, user_id, start_lat, start_lon,
                                               end_lat, end_lon, vehicle_type,
                                               total_distance_m, estimated_time_s,
                                               risk_score, flooded_segments, created_at)
                    VALUES (:event_id, :user_id, :start_lat, :start_lon,
                            :end_lat, :end_lon, :vehicle_type,
                            :distance, :time, :risk, :flooded, NOW())
                """),
                {
                    "event_id": int(request.event_id) if request.event_id else None,
                    "user_id": user_id,
                    "start_lat": request.start_lat,
                    "start_lon": request.start_lon,
                    "end_lat": request.end_lat,
                    "end_lon": request.end_lon,
                    "vehicle_type": request.vehicle_type,
                    "distance": best.total_distance_m,
                    "time": best.estimated_time_s,
                    "risk": best.risk_score,
                    "flooded": best.flooded_segments,
                },
            )
            await db.commit()
            logger.info("Route saved to history")
        except Exception as save_err:
            logger.warning(f"Failed to save route history: {save_err}")

        return RouteResponse(
            success=True,
            routes=routes,
            vehicle_type=request.vehicle_type,
            message=f"Found {len(routes)} route(s).",
        )

    except Exception as e:
        logger.error(f"Route computation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Route computation failed: {str(e)}",
        )


@router.post("/reroute", response_model=RouteResponse)
async def reroute(
    request: RerouteRequest,
    user: Optional[CurrentUser] = Depends(get_current_user),
):
    """
    Recompute route from current GPS position.
    Called when the existing route becomes blocked.
    """
    logger.info(f"Reroute request from ({request.current_lat:.5f},{request.current_lon:.5f})")

    try:
        service = _get_routing_service()
        rerouting = ReroutingService(routing_service=service)

        routes = await rerouting.reroute(
            current_lat=request.current_lat,
            current_lon=request.current_lon,
            end_lat=request.end_lat,
            end_lon=request.end_lon,
            vehicle_type=request.vehicle_type,
            place=request.place,
            event_id=request.event_id,
        )

        if not routes:
            return RouteResponse(
                success=False,
                routes=[],
                vehicle_type=request.vehicle_type,
                message="No alternative routes available. Consider changing vehicle type.",
            )

        return RouteResponse(
            success=True,
            routes=routes,
            vehicle_type=request.vehicle_type,
            message=f"Rerouted: found {len(routes)} alternative(s).",
        )

    except Exception as e:
        logger.error(f"Reroute error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Rerouting failed: {str(e)}",
        )


@router.get("/route/history")
async def route_history(
    limit: int = 20,
    user: CurrentUser = Depends(get_current_user),
):
    """Get route history for the current user or event."""
    # TODO: Connect to route_repository
    return {"routes": [], "message": "Route history endpoint - connect to database"}
