"""
Flood-related data models.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class FloodSeverity(str, Enum):
    NONE = "none"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


class FloodEvent(BaseModel):
    """Metadata about a single flood activation/event."""

    id: Optional[int] = None
    activation_id: str = Field(description="Copernicus EMS activation ID, e.g. EMSR838")
    event_name: str
    country: str
    region: str
    start_date: datetime
    end_date: Optional[datetime] = None
    is_active: bool = True
    data_source: str = "copernicus_ems"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class FloodZone(BaseModel):
    """A flood polygon with depth information."""

    id: Optional[int] = None
    event_id: int
    geometry_wkt: str = Field(description="Well-Known Text of the flood polygon")
    max_depth: Optional[float] = None
    avg_depth: Optional[float] = None
    area_km2: Optional[float] = None
    centroid_lat: Optional[float] = None
    centroid_lon: Optional[float] = None
    source_file: Optional[str] = None
    created_at: Optional[datetime] = None


class FloodDepthCheck(BaseModel):
    """Result of a flood depth check at a point."""

    latitude: float
    longitude: float
    depth: float
    is_flooded: bool
    severity: FloodSeverity
    description: str


class FloodedRoad(BaseModel):
    """A road segment affected by flooding."""

    id: Optional[int] = None
    event_id: int
    road_id: int
    max_depth: float
    avg_depth: float
    flooded_percentage: float = Field(ge=0, le=100)
    risk_score: float = Field(ge=0, le=1)
    is_passable_car: bool = True
    is_passable_truck: bool = True
    is_passable_ambulance: bool = True


class FloodedBuilding(BaseModel):
    """A building affected by flooding."""

    id: Optional[int] = None
    event_id: int
    building_id: int
    water_depth: float
    is_accessible: bool = True
    evacuation_needed: bool = False


class FloodRiskAssessment(BaseModel):
    """Risk assessment for a path or location."""

    overall_risk: FloodSeverity
    max_depth: float
    avg_depth: float
    flooded_percentage: float
    checkpoints_total: int
    checkpoints_flooded: int
    recommendation: str
    tier_breakdown: dict = Field(default_factory=dict)
