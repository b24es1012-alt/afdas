"""
Building and infrastructure models.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum


class BuildingType(str, Enum):
    HOSPITAL = "hospital"
    SCHOOL = "school"
    SHELTER = "shelter"
    POLICE_STATION = "police_station"
    FIRE_STATION = "fire_station"
    PHARMACY = "pharmacy"
    MOSQUE = "mosque"
    GOVERNMENT = "government"
    RESIDENTIAL = "residential"
    COMMERCIAL = "commercial"
    OTHER = "other"


class Building(BaseModel):
    """A building or point of interest."""

    id: Optional[int] = None
    osm_id: Optional[int] = None
    name: str
    building_type: BuildingType
    latitude: float
    longitude: float
    address: Optional[str] = None
    phone: Optional[str] = None
    capacity: Optional[int] = None
    is_emergency_facility: bool = False
    geometry_wkt: Optional[str] = None
    event_id: Optional[int] = None


class BuildingFloodStatus(BaseModel):
    """Flood status of a building."""

    building_id: int
    building_name: str
    building_type: BuildingType
    latitude: float
    longitude: float
    flood_depth: float = 0.0
    is_flooded: bool = False
    is_accessible: bool = True
    evacuation_needed: bool = False
    nearest_safe_alternative: Optional[str] = None
