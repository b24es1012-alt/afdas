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
    place: str = Field(default="New Delhi, India")
    event_id: Optional[str] = None
    custom_clearance: Optional[float] = Field(default=None, description="Custom max flood depth in meters (overrides vehicle default)")


class RerouteRequest(BaseModel):
    """Request for real-time rerouting."""
    current_lat: float = Field(..., ge=-90, le=90)
    current_lon: float = Field(..., ge=-180, le=180)
    end_lat: float = Field(..., ge=-90, le=90)
    end_lon: float = Field(..., ge=-180, le=180)
    vehicle_type: str = Field(default="car")
    place: str = Field(default="New Delhi, India")
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
        # Load active flood zones from database as GeoDataFrame
        flood_gdf = None
        try:
            from sqlalchemy import text
            import geopandas as gpd
            from shapely import wkt

            # Get active flood zones
            event_filter = ""
            params = {}
            if request.event_id:
                event_filter = "AND fz.event_id = :event_id"
                params["event_id"] = int(request.event_id)

            result = await db.execute(
                text(f"""
                    SELECT ST_AsText(fz.geometry) as geom_wkt, fz.max_depth
                    FROM flood_zones fz
                    JOIN flood_events fe ON fe.id = fz.event_id
                    WHERE fe.is_active = TRUE {event_filter}
                """),
                params,
            )
            rows = result.fetchall()

            if rows:
                from shapely.geometry import shape
                from shapely import wkt as shapely_wkt
                geometries = []
                depths = []
                for row in rows:
                    r = dict(row._mapping)
                    geom = shapely_wkt.loads(r["geom_wkt"])
                    geometries.append(geom)
                    depths.append(r["max_depth"] or 1.0)

                flood_gdf = gpd.GeoDataFrame(
                    {"geometry": geometries, "depth": depths},
                    crs="EPSG:4326"
                )
                logger.info(f"Loaded {len(flood_gdf)} flood zones from database")
            else:
                logger.info("No active flood zones in database")
        except Exception as flood_err:
            logger.warning(f"Could not load flood data: {flood_err}")

        service = _get_routing_service()
        
        # If custom clearance, override vehicle profile temporarily
        if request.custom_clearance is not None:
            from models.vehicle import VehicleProfile, get_vehicle_profile
            vehicle_profile = get_vehicle_profile(request.vehicle_type)
            vehicle_profile = vehicle_profile.model_copy(update={"max_flood_depth": request.custom_clearance})
            logger.info(f"Using custom clearance: {request.custom_clearance}m (vehicle: {request.vehicle_type})")

        routes = await service.find_routes(
            start_lat=request.start_lat,
            start_lon=request.start_lon,
            end_lat=request.end_lat,
            end_lon=request.end_lon,
            vehicle_type=request.vehicle_type,
            k=request.k,
            place=request.place,
            flood_gdf=flood_gdf,
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



# ── Nearby Cities / Border Detection ─────────────────────────────────────────

class NearbyCitiesRequest(BaseModel):
    """Request to check for nearby cities at border areas."""
    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)
    place: str = Field(default="New Delhi, India")


@router.post("/nearby-cities")
async def check_nearby_cities(request: NearbyCitiesRequest):
    """
    Check if a point is near the border of a city and return neighboring cities.
    
    This helps the frontend show which additional areas will be downloaded
    for optimal cross-boundary routing.
    """
    from graph.border_detector import BorderDetector

    detector = BorderDetector()

    is_near, direction = detector.is_near_border(request.lat, request.lon, request.place)

    nearby = []
    if is_near:
        nearby = detector.get_nearby_cities(request.lat, request.lon, request.place, direction)

    return {
        "is_near_border": is_near,
        "direction": direction,
        "nearby_cities": [
            {"name": c.get("name", ""), "place": c.get("place", ""), "direction": c.get("direction", "")}
            for c in nearby
        ],
        "message": (
            f"Point is near the {direction.upper()} border of {request.place}. "
            f"{len(nearby)} neighboring area(s) available for extended routing."
            if is_near
            else f"Point is well within {request.place} boundaries."
        ),
    }


@router.get("/neighbors/{place}")
async def list_city_neighbors(place: str):
    """
    List all known neighboring cities for a given place.
    Used by frontend to show coverage expansion options.
    """
    from graph.border_detector import CITY_NEIGHBORS

    # URL-decode the place name
    from urllib.parse import unquote
    place_decoded = unquote(place)

    neighbors = CITY_NEIGHBORS.get(place_decoded, [])

    return {
        "place": place_decoded,
        "neighbors": [
            {"name": n["name"], "place": n["place"], "direction": n["direction"]}
            for n in neighbors
        ],
        "count": len(neighbors),
    }
