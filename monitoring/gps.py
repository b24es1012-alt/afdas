"""
GPS tracking service — receives and processes real-time location updates.
"""

from typing import Optional, Dict
from datetime import datetime
from pydantic import BaseModel

from utils.logger import logger


class GPSUpdate(BaseModel):
    """A GPS position update from a user."""
    user_id: str
    latitude: float
    longitude: float
    accuracy_m: Optional[float] = None
    speed_kmh: Optional[float] = None
    bearing: Optional[float] = None
    timestamp: datetime = None

    def __init__(self, **data):
        if data.get("timestamp") is None:
            data["timestamp"] = datetime.utcnow()
        super().__init__(**data)


class GPSTrackingService:
    """
    Manages real-time GPS position tracking for active navigation sessions.
    
    Stores the latest position per user for:
    - Route deviation detection
    - Rerouting triggers
    - ETA updates
    """

    def __init__(self):
        # In-memory store for active sessions (use Redis for production scaling)
        self._positions: Dict[str, GPSUpdate] = {}

    def update_position(self, update: GPSUpdate) -> None:
        """Record a new GPS position for a user."""
        self._positions[update.user_id] = update

    def get_position(self, user_id: str) -> Optional[GPSUpdate]:
        """Get the latest known position for a user."""
        return self._positions.get(user_id)

    def remove_user(self, user_id: str) -> None:
        """Remove a user from active tracking (navigation ended)."""
        self._positions.pop(user_id, None)

    def get_active_users(self) -> int:
        """Get count of users currently being tracked."""
        return len(self._positions)

    def is_user_active(self, user_id: str) -> bool:
        """Check if a user has an active navigation session."""
        return user_id in self._positions


# Module-level singleton
gps_service = GPSTrackingService()
