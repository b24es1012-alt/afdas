"""
Distance calculation utilities.
"""

import math
from typing import List, Tuple
from utils.constants import EARTH_RADIUS_KM


def euclidean_distance(x1: float, y1: float, x2: float, y2: float) -> float:
    """Simple Euclidean distance (for projected coordinates)."""
    return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)


def manhattan_distance(x1: float, y1: float, x2: float, y2: float) -> float:
    """Manhattan (city-block) distance."""
    return abs(x2 - x1) + abs(y2 - y1)


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in km using Haversine formula."""
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))

    return EARTH_RADIUS_KM * c


def haversine_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in meters."""
    return haversine_km(lat1, lon1, lat2, lon2) * 1000


def nearest_point(
    target_lat: float,
    target_lon: float,
    points: List[Tuple[float, float]],
) -> Tuple[int, float]:
    """
    Find the nearest point from a list to the target.
    
    Args:
        target_lat, target_lon: Target coordinates
        points: List of (lat, lon) tuples
    
    Returns:
        (index, distance_km) of the nearest point
    """
    min_dist = float("inf")
    min_idx = 0

    for i, (lat, lon) in enumerate(points):
        dist = haversine_km(target_lat, target_lon, lat, lon)
        if dist < min_dist:
            min_dist = dist
            min_idx = i

    return min_idx, min_dist


def travel_time_seconds(distance_km: float, speed_kmh: float) -> float:
    """Calculate travel time in seconds given distance and speed."""
    if speed_kmh <= 0:
        return float("inf")
    return (distance_km / speed_kmh) * 3600
