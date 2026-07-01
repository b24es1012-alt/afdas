"""
Border detector — determines if a point is near the edge of a city boundary.
When users are near borders, we need to download adjacent city maps for optimal routing.

Strategy:
  1. Get the city bounding box from Nominatim
  2. Check if origin/destination is within BORDER_THRESHOLD_KM of the edge
  3. If yes, identify nearby cities in the expanding direction
  4. Return list of additional places to download
"""

import math
from typing import List, Dict, Optional, Tuple

from config.settings import settings
from utils.distance import haversine_km
from utils.logger import graph_logger as logger


# Known neighboring cities for Indian metro areas (pre-defined for common routes)
# This avoids expensive API calls for frequently traveled corridors
CITY_NEIGHBORS: Dict[str, List[Dict[str, str]]] = {
    "New Delhi, India": [
        {"name": "Gurgaon", "place": "Gurugram, Haryana, India", "direction": "sw", "center": (28.46, 77.03)},
        {"name": "Noida", "place": "Noida, Uttar Pradesh, India", "direction": "se", "center": (28.53, 77.39)},
        {"name": "Faridabad", "place": "Faridabad, Haryana, India", "direction": "s", "center": (28.41, 77.31)},
        {"name": "Ghaziabad", "place": "Ghaziabad, Uttar Pradesh, India", "direction": "e", "center": (28.67, 77.44)},
        {"name": "Sonipat", "place": "Sonipat, Haryana, India", "direction": "n", "center": (28.99, 77.02)},
    ],
    "Mumbai, India": [
        {"name": "Thane", "place": "Thane, Maharashtra, India", "direction": "ne", "center": (19.22, 72.97)},
        {"name": "Navi Mumbai", "place": "Navi Mumbai, Maharashtra, India", "direction": "e", "center": (19.03, 73.03)},
        {"name": "Kalyan", "place": "Kalyan, Maharashtra, India", "direction": "ne", "center": (19.24, 73.13)},
        {"name": "Mira-Bhayandar", "place": "Mira-Bhayandar, Maharashtra, India", "direction": "n", "center": (19.29, 72.85)},
    ],
    "Chennai, India": [
        {"name": "Kanchipuram", "place": "Kanchipuram, Tamil Nadu, India", "direction": "sw", "center": (12.83, 79.70)},
        {"name": "Tiruvallur", "place": "Tiruvallur, Tamil Nadu, India", "direction": "nw", "center": (13.14, 79.91)},
        {"name": "Chengalpattu", "place": "Chengalpattu, Tamil Nadu, India", "direction": "s", "center": (12.69, 79.97)},
    ],
    "Bangalore, India": [
        {"name": "Hosur", "place": "Hosur, Tamil Nadu, India", "direction": "se", "center": (12.73, 77.83)},
        {"name": "Tumkur", "place": "Tumkur, Karnataka, India", "direction": "nw", "center": (13.34, 77.10)},
        {"name": "Kolar", "place": "Kolar, Karnataka, India", "direction": "e", "center": (13.14, 78.13)},
        {"name": "Ramanagara", "place": "Ramanagara, Karnataka, India", "direction": "sw", "center": (12.72, 77.28)},
    ],
    "Kolkata, India": [
        {"name": "Howrah", "place": "Howrah, West Bengal, India", "direction": "w", "center": (22.59, 88.26)},
        {"name": "Salt Lake", "place": "Bidhannagar, West Bengal, India", "direction": "ne", "center": (22.58, 88.41)},
        {"name": "Barrackpore", "place": "Barrackpore, West Bengal, India", "direction": "n", "center": (22.76, 88.37)},
    ],
    "Hyderabad, India": [
        {"name": "Secunderabad", "place": "Secunderabad, Telangana, India", "direction": "n", "center": (17.44, 78.50)},
        {"name": "Shamshabad", "place": "Shamshabad, Telangana, India", "direction": "s", "center": (17.24, 78.43)},
        {"name": "Medchal", "place": "Medchal, Telangana, India", "direction": "n", "center": (17.63, 78.48)},
    ],
}

# Approximate bounding boxes for supported cities (min_lat, min_lon, max_lat, max_lon)
CITY_BBOXES: Dict[str, Tuple[float, float, float, float]] = {
    "New Delhi, India": (28.40, 76.84, 28.88, 77.35),
    "Mumbai, India": (18.89, 72.77, 19.27, 72.98),
    "Chennai, India": (12.83, 80.10, 13.23, 80.33),
    "Bangalore, India": (12.85, 77.45, 13.15, 77.75),
    "Kolkata, India": (22.45, 88.25, 22.65, 88.45),
    "Hyderabad, India": (17.30, 78.35, 17.50, 78.60),
}


class BorderDetector:
    """
    Detects when routing points are near city boundaries and identifies
    which neighboring cities should have their maps downloaded.
    """

    def __init__(
        self,
        border_threshold_km: float = None,
        nearby_radius_km: float = None,
    ):
        self.border_threshold_km = border_threshold_km or settings.BORDER_THRESHOLD_KM
        self.nearby_radius_km = nearby_radius_km or settings.NEARBY_CITY_RADIUS_KM

    def is_near_border(
        self,
        lat: float,
        lon: float,
        place: str,
    ) -> Tuple[bool, str]:
        """
        Check if a point is near the border of a city.

        Args:
            lat, lon: Point to check
            place: City/place name (e.g. "New Delhi, India")

        Returns:
            (is_near_border: bool, direction: str)
            direction is one of: 'n', 's', 'e', 'w', 'ne', 'nw', 'se', 'sw', ''
        """
        bbox = CITY_BBOXES.get(place)
        if not bbox:
            # Unknown city — can't determine border
            return False, ""

        min_lat, min_lon, max_lat, max_lon = bbox

        # Calculate distances to each edge
        center_lat = (min_lat + max_lat) / 2
        center_lon = (min_lon + max_lon) / 2

        dist_north = haversine_km(lat, lon, max_lat, lon)
        dist_south = haversine_km(lat, lon, min_lat, lon)
        dist_east = haversine_km(lat, lon, lat, max_lon)
        dist_west = haversine_km(lat, lon, lat, min_lon)

        # Check if point is within threshold of any edge
        near_north = dist_north < self.border_threshold_km
        near_south = dist_south < self.border_threshold_km
        near_east = dist_east < self.border_threshold_km
        near_west = dist_west < self.border_threshold_km

        if not (near_north or near_south or near_east or near_west):
            return False, ""

        # Determine primary direction
        direction = ""
        if near_north:
            direction += "n"
        if near_south:
            direction += "s"
        if near_east:
            direction += "e"
        if near_west:
            direction += "w"

        return True, direction

    def get_nearby_cities(
        self,
        lat: float,
        lon: float,
        place: str,
        direction: str = "",
    ) -> List[Dict[str, str]]:
        """
        Get list of nearby cities that should be downloaded based on
        the user's position and direction toward the border.

        Args:
            lat, lon: Point near the border
            place: Current city
            direction: Direction toward border (from is_near_border)

        Returns:
            List of dicts with 'name' and 'place' keys for each city to download
        """
        neighbors = CITY_NEIGHBORS.get(place, [])

        if not neighbors:
            # Unknown city — try to find nearby cities dynamically
            return self._find_nearby_cities_dynamic(lat, lon, place)

        # Filter neighbors by direction if provided
        if direction:
            # Match neighbors whose direction contains any of our direction chars
            relevant = []
            for neighbor in neighbors:
                n_dir = neighbor.get("direction", "")
                # Check if directions are compatible
                if self._directions_compatible(direction, n_dir):
                    relevant.append(neighbor)
            
            # If no direction match, check distance-based
            if not relevant:
                relevant = [
                    n for n in neighbors
                    if haversine_km(lat, lon, n["center"][0], n["center"][1]) < self.nearby_radius_km
                ]
            return relevant

        # No direction — return all within radius
        return [
            n for n in neighbors
            if haversine_km(lat, lon, n["center"][0], n["center"][1]) < self.nearby_radius_km
        ]

    def detect_cross_city_route(
        self,
        start_lat: float,
        start_lon: float,
        end_lat: float,
        end_lon: float,
        place: str,
    ) -> List[Dict[str, str]]:
        """
        Detect ALL additional cities needed for routing.

        Strategy:
        1. ALWAYS download pre-defined neighbors within radius (for known cities)
        2. If destination is OUTSIDE the primary city → also download destination's area
        3. If origin is OUTSIDE the primary city → also download origin's area

        This handles:
        - "Noida to Gurgaon" (origin city primary, dest city added)
        - "Delhi to Delhi" (neighbors downloaded for better routes)
        - "Dehradun to Rishikesh" (both added as dynamic areas)

        Args:
            start_lat, start_lon: Origin
            end_lat, end_lon: Destination
            place: Primary city (usually origin city)

        Returns:
            List of cities/areas to download in addition to the primary city
        """
        cities_to_download = []
        seen_places = {place}

        # ── Step 1: Add pre-defined neighbors within radius ──────────────
        neighbors = CITY_NEIGHBORS.get(place, [])
        if neighbors:
            bbox = CITY_BBOXES.get(place)
            if bbox:
                city_center_lat = (bbox[0] + bbox[2]) / 2
                city_center_lon = (bbox[1] + bbox[3]) / 2
            else:
                city_center_lat = start_lat
                city_center_lon = start_lon

            for neighbor in neighbors:
                n_center = neighbor["center"]
                dist = haversine_km(city_center_lat, city_center_lon, n_center[0], n_center[1])
                if dist < self.nearby_radius_km and neighbor["place"] not in seen_places:
                    cities_to_download.append(neighbor)
                    seen_places.add(neighbor["place"])

        # ── Step 2: Check if destination is outside primary city ──────────
        bbox = CITY_BBOXES.get(place)
        if bbox:
            min_lat, min_lon, max_lat, max_lon = bbox
            dest_outside = (
                end_lat < min_lat - 0.01 or end_lat > max_lat + 0.01 or
                end_lon < min_lon - 0.01 or end_lon > max_lon + 0.01
            )
            origin_outside = (
                start_lat < min_lat - 0.01 or start_lat > max_lat + 0.01 or
                start_lon < min_lon - 0.01 or start_lon > max_lon + 0.01
            )
        else:
            # Unknown city — check distance between origin and destination
            dist_apart = haversine_km(start_lat, start_lon, end_lat, end_lon)
            dest_outside = dist_apart > 10  # If >10km apart, likely different areas
            origin_outside = False

        # If destination is outside, add it as a dynamic download
        if dest_outside:
            # Check if destination matches any known neighbor already added
            dest_covered = False
            for city in cities_to_download:
                if city.get("center"):
                    dist_to_dest = haversine_km(end_lat, end_lon, city["center"][0], city["center"][1])
                    if dist_to_dest < 10:  # Destination is within 10km of a known neighbor
                        dest_covered = True
                        break

            if not dest_covered:
                # Add destination area as dynamic download
                dest_entry = {
                    "name": f"Destination area ({end_lat:.3f}, {end_lon:.3f})",
                    "place": None,  # Signals point-based download
                    "lat": end_lat,
                    "lon": end_lon,
                    "radius_m": 10000,  # 10km radius around destination
                }
                cities_to_download.append(dest_entry)
                logger.info(f"Destination ({end_lat:.4f}, {end_lon:.4f}) is outside '{place}' — adding dynamic area")

        # If origin is outside (user passed a "wrong" primary city), add origin area too
        if origin_outside:
            origin_covered = False
            for city in cities_to_download:
                if city.get("center"):
                    dist_to_origin = haversine_km(start_lat, start_lon, city["center"][0], city["center"][1])
                    if dist_to_origin < 10:
                        origin_covered = True
                        break

            if not origin_covered:
                origin_entry = {
                    "name": f"Origin area ({start_lat:.3f}, {start_lon:.3f})",
                    "place": None,
                    "lat": start_lat,
                    "lon": start_lon,
                    "radius_m": 10000,
                }
                cities_to_download.append(origin_entry)
                logger.info(f"Origin ({start_lat:.4f}, {start_lon:.4f}) is outside '{place}' — adding dynamic area")

        if cities_to_download:
            names = [c["name"] for c in cities_to_download]
            logger.info(f"Multi-city routing for '{place}': downloading {names}")

        return cities_to_download

    def _directions_compatible(self, user_dir: str, neighbor_dir: str) -> bool:
        """Check if user's border direction is compatible with a neighbor's direction."""
        # e.g. user near "ne" border → neighbors in "n", "ne", "e" are relevant
        for char in user_dir:
            if char in neighbor_dir:
                return True
        return False

    def _find_nearby_cities_dynamic(
        self,
        lat: float,
        lon: float,
        current_place: str,
    ) -> List[Dict[str, str]]:
        """
        Dynamically identify nearby cities when pre-defined neighbors aren't available.
        Uses a bounding box expansion approach — downloads a larger area around the point.

        For unknown cities, we return a bbox-based download suggestion instead of named places.
        """
        # For non-preset cities, suggest downloading a radius around the border point
        # This uses download_road_network_point with expanded radius
        return [
            {
                "name": f"Area around ({lat:.3f}, {lon:.3f})",
                "place": None,  # Signals to use bbox/point download instead
                "lat": lat,
                "lon": lon,
                "radius_m": int(self.nearby_radius_km * 1000),
            }
        ]
