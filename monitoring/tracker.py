"""
Route tracker — monitors user progress along planned routes.
Detects deviations and triggers rerouting when needed.
"""

from typing import Optional, Tuple, List
from datetime import datetime

from monitoring.gps import GPSUpdate, gps_service
from utils.distance import haversine_meters
from utils.logger import logger


# Deviation threshold: if user is more than this far from route, trigger reroute
DEVIATION_THRESHOLD_M = 100.0


class RouteTracker:
    """
    Tracks a user's progress along a planned route.
    
    Checks:
    - Is the user still on the planned route?
    - Has the user reached their destination?
    - Should we trigger a reroute?
    """

    def __init__(self):
        # Active routes: user_id → route data
        self._active_routes: dict = {}

    def start_navigation(
        self,
        user_id: str,
        route_coordinates: List[Tuple[float, float]],
        destination_lat: float,
        destination_lon: float,
    ) -> None:
        """
        Start tracking a user along a route.
        
        Args:
            user_id: Unique user identifier
            route_coordinates: List of (lat, lon) waypoints
            destination_lat, destination_lon: Final destination
        """
        self._active_routes[user_id] = {
            "coordinates": route_coordinates,
            "destination": (destination_lat, destination_lon),
            "current_waypoint_idx": 0,
            "started_at": datetime.utcnow(),
            "last_check": datetime.utcnow(),
        }
        logger.info(f"Navigation started for user {user_id} ({len(route_coordinates)} waypoints)")

    def stop_navigation(self, user_id: str) -> None:
        """Stop tracking a user."""
        self._active_routes.pop(user_id, None)
        gps_service.remove_user(user_id)
        logger.info(f"Navigation stopped for user {user_id}")

    def check_progress(
        self, user_id: str, gps_update: GPSUpdate
    ) -> Tuple[str, Optional[dict]]:
        """
        Check user's progress against their planned route.
        
        Args:
            user_id: User ID
            gps_update: Latest GPS position
        
        Returns:
            (status, details) where status is one of:
            - "on_track": User is following the route
            - "deviated": User has left the route (reroute needed)
            - "arrived": User reached destination
            - "no_route": No active route for this user
        """
        route_data = self._active_routes.get(user_id)
        if not route_data:
            return "no_route", None

        coords = route_data["coordinates"]
        dest = route_data["destination"]

        # Check if arrived at destination
        dist_to_dest = haversine_meters(
            gps_update.latitude, gps_update.longitude, dest[0], dest[1]
        )
        if dist_to_dest < 50:  # Within 50m of destination
            self.stop_navigation(user_id)
            return "arrived", {"distance_to_dest": dist_to_dest}

        # Find nearest point on route
        min_dist = float("inf")
        nearest_idx = 0

        for i, (lat, lon) in enumerate(coords):
            dist = haversine_meters(gps_update.latitude, gps_update.longitude, lat, lon)
            if dist < min_dist:
                min_dist = dist
                nearest_idx = i

        # Update waypoint index
        route_data["current_waypoint_idx"] = nearest_idx
        route_data["last_check"] = datetime.utcnow()

        # Check deviation
        if min_dist > DEVIATION_THRESHOLD_M:
            return "deviated", {
                "deviation_m": min_dist,
                "nearest_waypoint": nearest_idx,
                "threshold": DEVIATION_THRESHOLD_M,
            }

        return "on_track", {
            "distance_to_route": min_dist,
            "waypoint_progress": f"{nearest_idx}/{len(coords)}",
            "distance_to_dest": dist_to_dest,
        }

    def get_active_navigations(self) -> int:
        """Get count of active navigation sessions."""
        return len(self._active_routes)


# Module-level singleton
route_tracker = RouteTracker()
