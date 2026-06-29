"""
Alert system — sends flood warnings and road closure notifications.
"""

from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel
from enum import Enum

from utils.logger import logger


class AlertType(str, Enum):
    FLOOD_WARNING = "flood_warning"
    ROAD_CLOSED = "road_closed"
    REROUTE_NEEDED = "reroute_needed"
    EVACUATION = "evacuation"
    NEW_FLOOD_DATA = "new_flood_data"


class AlertSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class Alert(BaseModel):
    """A system alert/notification."""
    id: Optional[str] = None
    alert_type: AlertType
    severity: AlertSeverity
    title: str
    message: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    radius_km: Optional[float] = None
    created_at: datetime = None
    expires_at: Optional[datetime] = None
    target_users: Optional[List[str]] = None  # None = broadcast to all

    def __init__(self, **data):
        if data.get("created_at") is None:
            data["created_at"] = datetime.utcnow()
        super().__init__(**data)


class AlertService:
    """
    Manages and dispatches alerts to users.
    
    In production, this would integrate with:
    - WebSocket connections for real-time push
    - Push notification services (FCM, APNS)
    - SMS gateway for critical alerts
    """

    def __init__(self):
        self._alerts: List[Alert] = []
        self._subscribers: dict = {}  # user_id → callback

    def create_alert(
        self,
        alert_type: AlertType,
        severity: AlertSeverity,
        title: str,
        message: str,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        radius_km: Optional[float] = None,
    ) -> Alert:
        """Create and store a new alert."""
        alert = Alert(
            alert_type=alert_type,
            severity=severity,
            title=title,
            message=message,
            latitude=lat,
            longitude=lon,
            radius_km=radius_km,
        )
        self._alerts.append(alert)
        logger.info(f"Alert created: [{severity.value}] {title}")
        return alert

    def get_active_alerts(
        self,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
    ) -> List[Alert]:
        """Get active alerts, optionally filtered by location."""
        now = datetime.utcnow()
        active = [
            a for a in self._alerts
            if a.expires_at is None or a.expires_at > now
        ]

        # TODO: Filter by proximity if lat/lon provided
        return active

    def flood_warning(
        self,
        lat: float,
        lon: float,
        depth: float,
        area_name: str = "area",
    ) -> Alert:
        """Create a flood warning alert."""
        severity = AlertSeverity.WARNING
        if depth > 1.0:
            severity = AlertSeverity.CRITICAL

        return self.create_alert(
            alert_type=AlertType.FLOOD_WARNING,
            severity=severity,
            title=f"Flood Warning — {area_name}",
            message=f"Flooding detected (depth: {depth:.2f}m). Avoid this area.",
            lat=lat,
            lon=lon,
            radius_km=2.0,
        )

    def road_closure(
        self,
        road_name: str,
        lat: float,
        lon: float,
        reason: str = "flooding",
    ) -> Alert:
        """Create a road closure alert."""
        return self.create_alert(
            alert_type=AlertType.ROAD_CLOSED,
            severity=AlertSeverity.WARNING,
            title=f"Road Closed — {road_name}",
            message=f"{road_name} is closed due to {reason}. Use alternative routes.",
            lat=lat,
            lon=lon,
        )

    def clear_expired(self) -> int:
        """Remove expired alerts. Returns count removed."""
        now = datetime.utcnow()
        before = len(self._alerts)
        self._alerts = [
            a for a in self._alerts
            if a.expires_at is None or a.expires_at > now
        ]
        removed = before - len(self._alerts)
        if removed:
            logger.info(f"Cleared {removed} expired alerts")
        return removed


# Module-level singleton
alert_service = AlertService()
