"""
Agent tools — wraps backend services as LangChain tools for the AI agent.
Each tool is a self-contained function that the planner can invoke.
"""

import time
from typing import List, Dict, Any, Optional

from langchain_core.tools import tool

from config.settings import settings
from osm.downloader import OSMDownloader
from flood.risk import depth_to_severity, assess_path_risk
from models.vehicle import VEHICLE_PROFILES, VehicleType
from utils.geometry import interpolate_points
from utils.logger import agent_logger as logger


# Lazy-loaded shared instances
_osm_downloader: Optional[OSMDownloader] = None

# Shared route result storage — allows chat.py to extract structured route data
# after the calculate_route tool runs (since tools return text, not structured data)
_last_route_results: Optional[List[Dict[str, Any]]] = None


def get_last_route_results() -> Optional[List[Dict[str, Any]]]:
    """Get the last calculated route results as structured data."""
    global _last_route_results
    return _last_route_results


def clear_last_route_results():
    """Clear stored route results."""
    global _last_route_results
    _last_route_results = None


def _get_osm() -> OSMDownloader:
    global _osm_downloader
    if _osm_downloader is None:
        _osm_downloader = OSMDownloader()
    return _osm_downloader


# ============================================================================
# TOOLS
# ============================================================================

async def _reverse_geocode_city(lat: float, lon: float) -> str:
    """Get city name from coordinates using Nominatim reverse geocoding."""
    import httpx
    try:
        async with httpx.AsyncClient() as client:
            res = await client.get(
                f"https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lon}&format=json&zoom=10",
                headers={"User-Agent": "AFDAS/1.0"},
                timeout=5.0,
            )
            data = res.json()
            city = data.get("address", {}).get("city") or data.get("address", {}).get("state_district") or data.get("address", {}).get("state") or "Delhi"
            state = data.get("address", {}).get("state", "")
            country = data.get("address", {}).get("country", "India")
            return city, state, country
    except Exception:
        return "Delhi", "Delhi", "India"


async def _detect_place_from_coordinates(
    start_lat: float, start_lon: float,
    end_lat: float, end_lon: float,
) -> str:
    """
    Auto-detect the OSM place name from route coordinates.
    
    Strategy:
    - Geocode BOTH origin and destination separately
    - If they're in the same city → return that city
    - If different cities → return the larger/primary city (the multi-city
      loader will handle downloading additional cities via border detection)
    - ALWAYS normalizes to Title Case for consistent caching
    
    Returns an OSM-compatible place string like "Dehradun, India" or "New Delhi, India"
    """
    # Geocode origin
    origin_city, origin_state, origin_country = await _reverse_geocode_city(start_lat, start_lon)
    # Geocode destination
    dest_city, dest_state, dest_country = await _reverse_geocode_city(end_lat, end_lon)

    logger.info(f"[place_detect] Origin: {origin_city}, {origin_state} | Dest: {dest_city}, {dest_state}")

    # Normalize to title case for consistent caching
    origin_city = origin_city.strip().title() if origin_city else ""
    dest_city = dest_city.strip().title() if dest_city else ""
    origin_country = origin_country.strip().title() if origin_country else "India"
    dest_country = dest_country.strip().title() if dest_country else "India"

    # Build place strings
    origin_place = f"{origin_city}, {origin_country}" if origin_city else None
    dest_place = f"{dest_city}, {dest_country}" if dest_city else None

    # If same city, just use it
    if origin_city and dest_city and origin_city.lower() == dest_city.lower():
        return origin_place or "New Delhi, India"

    # Different cities — pick the origin city as primary
    # (the multi-city loader will detect that dest is outside and download it)
    if origin_place:
        return origin_place
    if dest_place:
        return dest_place

    return "New Delhi, India"

@tool
async def get_coordinates_from_location(
    location_name: str,
    city: str = "Delhi",
    state: str = "Delhi",
    country: str = "India",
) -> str:
    """
    Convert a location name (e.g. 'DHQ Hospital', 'Railway Station') to GPS coordinates.
    ALWAYS call this first when the user gives a place name instead of coordinates.

    Args:
        location_name: Name of the location
        city: City (default: Delhi)
        state: State (default: Delhi)
        country: Country (default: India)
    """
    osm = _get_osm()
    results = await osm.geocode_location(location_name, city, state, country)

    if not results:
        return f"Location '{location_name}' not found in {city}. Try a different name."

    lines = [f"Found {len(results)} match(es) for '{location_name}':\n"]
    for i, place in enumerate(results, 1):
        lines.append(
            f"{i}. {place['name']}\n"
            f"   Coordinates: ({place['lat']}, {place['lon']})\n"
            f"   Type: {place['type']}\n"
        )
    return "\n".join(lines)


@tool
async def search_amenity(
    amenity: str,
    city: str = "Delhi",
    state: str = "Delhi",
    country: str = "India",
    limit: int = 10,
) -> str:
    """
    Find amenities (hospitals, schools, shelters, pharmacies, etc.) from the database.

    Args:
        amenity: Type of amenity (e.g. 'hospital', 'school', 'pharmacy', 'shelter')
        city: City (default: Delhi)
        state: State (default: Delhi)
        country: Country (default: India)
        limit: Max results (default: 10)
    """
    from database.connection import DatabaseManager
    from sqlalchemy import text

    try:
        async with DatabaseManager.session() as session:
            result = await session.execute(
                text("""
                    SELECT name, building_type, latitude, longitude, is_emergency_facility
                    FROM buildings
                    WHERE LOWER(building_type) LIKE :amenity
                    ORDER BY name
                    LIMIT :limit
                """),
                {"amenity": f"%{amenity.lower()}%", "limit": limit},
            )
            rows = result.fetchall()

        if not rows:
            # Fallback to Nominatim if DB is empty
            osm = _get_osm()
            results = await osm.search_amenities(amenity, city, state, country, limit)
            if not results:
                return f"No {amenity}s found in {city}"
            lines = [f"Found {len(results)} {amenity}(s) (from OSM):\n"]
            for i, place in enumerate(results, 1):
                lines.append(f"{i}. {place['name']}\n   Coordinates: ({place['lat']}, {place['lon']})\n")
            return "\n".join(lines)

        lines = [f"Found {len(rows)} {amenity}(s) in database:\n"]
        for i, row in enumerate(rows, 1):
            r = dict(row._mapping)
            emergency = " [EMERGENCY]" if r["is_emergency_facility"] else ""
            lines.append(f"{i}. {r['name']}{emergency}\n   Coordinates: ({r['latitude']}, {r['longitude']})\n")
        return "\n".join(lines)

    except Exception as e:
        return f"Error searching amenities: {e}"


@tool
async def check_flood_depth(lat: float, lon: float) -> str:
    """
    Check flood depth at specific coordinates using PostGIS data.

    Args:
        lat: Latitude
        lon: Longitude
    """
    # In production this queries PostGIS; for now use the database repository
    from database.connection import DatabaseManager
    from database.flood_repository import FloodRepository

    try:
        async with DatabaseManager.session() as session:
            repo = FloodRepository(session)
            depth = await repo.get_flood_depth_at_point(lat, lon)

        severity, desc = depth_to_severity(depth)

        if depth == 0:
            return (
                f"Location ({lat}, {lon}):\n"
                f"- Status: SAFE (not in any flood zone)\n"
                f"- Flood Depth: 0 m\n"
            )

        return (
            f"Location ({lat}, {lon}):\n"
            f"- Status: FLOODED\n"
            f"- Flood Depth: {depth:.2f} m\n"
            f"- Severity: {severity.value.upper()} — {desc}\n"
        )
    except Exception as e:
        return f"Error checking flood depth: {e}"


@tool
async def check_vehicle_passability(
    lat: float, lon: float, vehicle_type: str = "car"
) -> str:
    """
    Check if a vehicle can pass a location given current flood depth.

    Args:
        lat: Latitude
        lon: Longitude
        vehicle_type: 'car', 'ambulance', 'truck', 'suv', or 'boat'
    """
    from database.connection import DatabaseManager
    from database.flood_repository import FloodRepository

    try:
        vt = VehicleType(vehicle_type.lower())
    except ValueError:
        vt = VehicleType.CAR

    profile = VEHICLE_PROFILES[vt]

    try:
        async with DatabaseManager.session() as session:
            repo = FloodRepository(session)
            depth = await repo.get_flood_depth_at_point(lat, lon)

        passable = depth <= profile.max_flood_depth
        status = "PASSABLE" if passable else "NOT PASSABLE"

        rec = (
            "Location is passable."
            if passable
            else f"Do NOT attempt with {vehicle_type}. Depth {depth:.2f}m exceeds limit {profile.max_flood_depth}m."
        )

        return (
            f"Vehicle Passability at ({lat}, {lon}):\n"
            f"  Vehicle: {profile.display_name}\n"
            f"  Flood Depth: {depth:.2f} m\n"
            f"  Vehicle Limit: {profile.max_flood_depth} m\n"
            f"  Status: {status}\n"
            f"  Recommendation: {rec}\n"
        )
    except Exception as e:
        return f"Error checking passability: {e}"


@tool
async def calculate_route(
    start_lat: float,
    start_lon: float,
    end_lat: float,
    end_lon: float,
    vehicle_type: str = "car",
    k: int = 3,
) -> str:
    """
    Compute flood-safe routes on the real road network.

    Args:
        start_lat, start_lon: Origin coordinates
        end_lat, end_lon: Destination coordinates
        vehicle_type: Vehicle type (default: 'car')
        k: Number of alternative routes (default: 3)
    """
    global _last_route_results
    from routing.service import RoutingService
    from graph.loader import GraphLoader
    from cache.graph_cache import GraphCache

    try:
        graph_cache = GraphCache()
        graph_loader = GraphLoader(graph_cache=graph_cache)
        service = RoutingService(graph_loader=graph_loader)

        # Auto-detect the city/place from coordinates using reverse geocoding
        # This prevents downloading Delhi maps when user is in Uttarakhand, etc.
        place = await _detect_place_from_coordinates(start_lat, start_lon, end_lat, end_lon)
        logger.info(f"[calculate_route] Auto-detected place: '{place}' from coordinates ({start_lat}, {start_lon})")

        routes = await service.find_routes(
            start_lat=start_lat,
            start_lon=start_lon,
            end_lat=end_lat,
            end_lon=end_lon,
            vehicle_type=vehicle_type,
            k=k,
            place=place,
        )

        if not routes:
            _last_route_results = None
            return "No routes found between the given coordinates."

        # Store structured route data for frontend map display
        _last_route_results = [
            {
                "route_index": route.route_index,
                "coordinates": route.coordinates,  # List of (lat, lon) tuples
                "total_distance_m": route.total_distance_m,
                "estimated_time_s": route.estimated_time_s,
                "flooded_segments": route.flooded_segments,
                "total_segments": route.total_segments,
                "risk_score": route.risk_score,
                "max_flood_depth": route.max_flood_depth,
            }
            for route in routes
        ]

        lines = [f"Found {len(routes)} route(s):\n"]
        for route in routes:
            lines.append(
                f"  Route {route.route_index + 1}: "
                f"{route.total_distance_m:.0f}m | "
                f"{route.estimated_time_s / 60:.1f} min | "
                f"Risk: {route.risk_score:.2f} | "
                f"{route.flooded_segments} flooded segments\n"
            )
        
        # Include first route coordinates for map display
        if routes[0].coordinates:
            coords_str = str(routes[0].coordinates[:5]) + "..." if len(routes[0].coordinates) > 5 else str(routes[0].coordinates)
            lines.append(f"\nBest route coordinates (for map): {coords_str}")
            lines.append(f"Total waypoints: {len(routes[0].coordinates)}")
        
        return "\n".join(lines)

    except Exception as e:
        _last_route_results = None
        return f"Error calculating route: {e}"


@tool
async def check_amenity_flood_status(
    amenity: str,
    city: str = "Delhi",
    state: str = "Delhi",
    country: str = "India",
) -> str:
    """
    Check which amenities (hospitals, schools, etc.) are in flood zones using database.

    Args:
        amenity: Type (e.g. 'hospital', 'school')
        city: City (default: Delhi)
        state: State (default: Delhi)
        country: Country (default: India)
    """
    from database.connection import DatabaseManager
    from database.flood_repository import FloodRepository
    from sqlalchemy import text

    try:
        async with DatabaseManager.session() as session:
            # Get buildings from DB
            result = await session.execute(
                text("""
                    SELECT id, name, building_type, latitude, longitude
                    FROM buildings
                    WHERE LOWER(building_type) LIKE :amenity
                """),
                {"amenity": f"%{amenity.lower()}%"},
            )
            buildings = [dict(row._mapping) for row in result.fetchall()]

        if not buildings:
            return f"No {amenity}s found in database. Try calculating a route first to download buildings."

        # Check flood status for each building
        safe_list, flood_list = [], []
        async with DatabaseManager.session() as session:
            repo = FloodRepository(session)
            for b in buildings:
                depth = await repo.get_flood_depth_at_point(b["latitude"], b["longitude"])
                entry = {**b, "depth": depth}
                if depth > 0:
                    flood_list.append(entry)
                else:
                    safe_list.append(entry)

        lines = [
            f"Flood Status — {amenity.capitalize()}s:",
            f"  Total: {len(buildings)} | Safe: {len(safe_list)} | Flooded: {len(flood_list)}\n",
        ]

        if flood_list:
            lines.append("FLOODED (avoid):")
            for p in flood_list[:5]:
                lines.append(f"  X {p['name']} — depth: {p['depth']:.2f}m ({p['latitude']}, {p['longitude']})")

        if safe_list:
            lines.append("\nSAFE (accessible):")
            for p in safe_list[:5]:
                lines.append(f"  OK {p['name']} ({p['latitude']}, {p['longitude']})")

        return "\n".join(lines)

    except Exception as e:
        return f"Error checking flood status: {e}"


@tool
async def get_flooded_areas() -> str:
    """List all active flood zones from the database."""
    from database.connection import DatabaseManager
    from database.flood_repository import FloodRepository

    try:
        async with DatabaseManager.session() as session:
            repo = FloodRepository(session)
            events = await repo.get_active_events()

            if not events:
                return "No active flood events in the database."

            lines = [f"Active flood events ({len(events)}):\n"]
            for event in events:
                zones = await repo.get_flood_zones_for_event(event["id"])
                lines.append(
                    f"  {event['activation_id']} — {event['event_name']}\n"
                    f"    Region: {event['region']}, {event['country']}\n"
                    f"    Zones: {len(zones)} polygons\n"
                )
            return "\n".join(lines)
    except Exception as e:
        return f"Error fetching flood areas: {e}"


@tool
async def assess_path_flood_risk(
    start_lat: float,
    start_lon: float,
    end_lat: float,
    end_lon: float,
    steps: int = 30,
) -> str:
    """
    Assess flood risk along the straight-line corridor between two points.

    Args:
        start_lat, start_lon: Origin
        end_lat, end_lon: Destination
        steps: Number of checkpoints (default: 30)
    """
    from database.connection import DatabaseManager
    from database.flood_repository import FloodRepository

    points = interpolate_points(start_lat, start_lon, end_lat, end_lon, steps)

    try:
        async with DatabaseManager.session() as session:
            repo = FloodRepository(session)
            checkpoints = []
            for lat, lon in points:
                depth = await repo.get_flood_depth_at_point(lat, lon)
                checkpoints.append((lat, lon, depth))

        assessment = assess_path_risk(checkpoints)

        return (
            f"Path Flood Risk Assessment:\n"
            f"  From: ({start_lat}, {start_lon})\n"
            f"  To: ({end_lat}, {end_lon})\n"
            f"  Overall Risk: {assessment.overall_risk.value.upper()}\n"
            f"  Max Depth: {assessment.max_depth:.2f}m\n"
            f"  Flooded: {assessment.checkpoints_flooded}/{assessment.checkpoints_total} checkpoints\n"
            f"  Recommendation: {assessment.recommendation}\n"
        )
    except Exception as e:
        return f"Error assessing path risk: {e}"


@tool
async def get_city_bbox(
    city: str = "Delhi",
    state: str = "Delhi",
    country: str = "India",
) -> str:
    """
    Get bounding box coordinates for a city.

    Args:
        city: City name
        state: State
        country: Country
    """
    osm = _get_osm()
    bbox = await osm.get_city_bbox(city, state, country)
    if not bbox:
        return f"Could not find bounding box for {city}"
    return (
        f"Bounding box for {city}:\n"
        f"  Min: ({bbox['min_lat']}, {bbox['min_lon']})\n"
        f"  Max: ({bbox['max_lat']}, {bbox['max_lon']})\n"
        f"  Center: ({bbox['center_lat']}, {bbox['center_lon']})\n"
    )


@tool
async def optimize_flood_safe_route(
    start_lat: float,
    start_lon: float,
    locations: List[Dict[str, Any]],
) -> str:
    """
    Find safest visiting order for multiple locations.

    Args:
        start_lat, start_lon: Starting position
        locations: List of dicts with 'name', 'lat', 'lon'
    """
    from utils.distance import haversine_km

    current = (start_lat, start_lon)
    route_order = []
    unvisited = locations.copy()

    while unvisited:
        nearest = min(
            unvisited,
            key=lambda loc: haversine_km(current[0], current[1], loc["lat"], loc["lon"]),
        )
        route_order.append(nearest)
        current = (nearest["lat"], nearest["lon"])
        unvisited.remove(nearest)

    lines = ["Optimized Multi-Stop Route:\n"]
    for i, loc in enumerate(route_order, 1):
        lines.append(f"  {i}. {loc['name']} ({loc['lat']}, {loc['lon']})")

    return "\n".join(lines)


# ============================================================================
# TOOLS MAP — used by the planner agent
# ============================================================================

def get_tools_map() -> dict:
    """Get the complete tools map for the agent."""
    return {
        "get_coordinates_from_location": get_coordinates_from_location,
        "search_amenity": search_amenity,
        "get_city_bbox": get_city_bbox,
        "check_flood_depth": check_flood_depth,
        "get_flooded_areas": get_flooded_areas,
        "assess_path_flood_risk": assess_path_flood_risk,
        "check_amenity_flood_status": check_amenity_flood_status,
        "check_vehicle_passability": check_vehicle_passability,
        "calculate_route": calculate_route,
        "optimize_flood_safe_route": optimize_flood_safe_route,
    }
