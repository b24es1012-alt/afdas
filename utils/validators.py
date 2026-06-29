"""
Input validation utilities.
"""

from typing import Optional


def validate_coordinates(lat: float, lon: float) -> bool:
    """Check if coordinates are within valid ranges."""
    return -90 <= lat <= 90 and -180 <= lon <= 180


def validate_flood_depth(depth: float) -> bool:
    """Check if flood depth is reasonable (0 to 20 meters)."""
    return 0 <= depth <= 20.0


def validate_vehicle_type(vehicle_type: str) -> bool:
    """Check if vehicle type is supported."""
    valid_types = {"walking", "motorcycle", "car", "suv", "ambulance", "truck", "boat"}
    return vehicle_type.lower() in valid_types


def validate_k_routes(k: int) -> bool:
    """Check if K (number of routes) is reasonable."""
    return 1 <= k <= 5


def sanitize_location_name(name: str) -> str:
    """Clean up a location name for geocoding queries."""
    # Remove extra whitespace, trim
    cleaned = " ".join(name.strip().split())
    # Basic protection against injection (Nominatim)
    cleaned = cleaned.replace(";", "").replace("--", "")
    return cleaned[:200]  # Max 200 chars


def validate_bbox(
    min_lat: float, min_lon: float, max_lat: float, max_lon: float
) -> bool:
    """Validate a bounding box."""
    return (
        validate_coordinates(min_lat, min_lon)
        and validate_coordinates(max_lat, max_lon)
        and min_lat < max_lat
        and min_lon < max_lon
    )
