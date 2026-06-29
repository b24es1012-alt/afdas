"""
Geometry helper functions for geospatial operations.
"""

import math
from typing import List, Tuple
from shapely.geometry import Point, LineString, Polygon
from shapely.ops import transform
import pyproj
from functools import partial

from utils.constants import EARTH_RADIUS_KM, CRS_WGS84


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great-circle distance between two points in km.
    
    Args:
        lat1, lon1: First point coordinates
        lat2, lon2: Second point coordinates
    
    Returns:
        Distance in kilometres
    """
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))

    return EARTH_RADIUS_KM * c


def interpolate_points(
    lat1: float, lon1: float, lat2: float, lon2: float, steps: int = 20
) -> List[Tuple[float, float]]:
    """
    Generate evenly spaced points along a straight line between two coordinates.
    
    Args:
        lat1, lon1: Start coordinates
        lat2, lon2: End coordinates
        steps: Number of intervals (returns steps + 1 points)
    
    Returns:
        List of (lat, lon) tuples
    """
    lats = [lat1 + (lat2 - lat1) * i / steps for i in range(steps + 1)]
    lons = [lon1 + (lon2 - lon1) * i / steps for i in range(steps + 1)]
    return list(zip(lats, lons))


def point_in_polygon(lat: float, lon: float, polygon: Polygon) -> bool:
    """Check if a point is inside a Shapely polygon."""
    return polygon.contains(Point(lon, lat))


def buffer_point_km(lat: float, lon: float, radius_km: float) -> Polygon:
    """
    Create a circular buffer around a point (approximate, in degrees).
    
    Args:
        lat, lon: Center coordinates
        radius_km: Radius in km
    
    Returns:
        Shapely Polygon approximating the buffer
    """
    # Approximate: 1 degree lat ≈ 111 km
    lat_offset = radius_km / 111.0
    lon_offset = radius_km / (111.0 * math.cos(math.radians(lat)))

    point = Point(lon, lat)
    return point.buffer(max(lat_offset, lon_offset))


def line_flood_intersection_ratio(
    line: LineString, flood_polygons: List[Polygon]
) -> float:
    """
    Calculate the fraction of a road segment intersecting flood polygons.
    
    Args:
        line: Road geometry as LineString
        flood_polygons: List of flood polygon geometries
    
    Returns:
        Fraction (0.0 - 1.0) of the road that is flooded
    """
    if not flood_polygons or line.is_empty:
        return 0.0

    total_length = line.length
    if total_length == 0:
        return 0.0

    flooded_length = 0.0
    for poly in flood_polygons:
        intersection = line.intersection(poly)
        if not intersection.is_empty:
            flooded_length += intersection.length

    return min(flooded_length / total_length, 1.0)


def compute_bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Compute initial bearing from point 1 to point 2.
    
    Returns:
        Bearing in degrees (0-360)
    """
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])

    dlon = lon2 - lon1
    x = math.sin(dlon) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)

    bearing = math.atan2(x, y)
    return (math.degrees(bearing) + 360) % 360
