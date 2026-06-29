"""
Road and road network models.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum


class RoadType(str, Enum):
    MOTORWAY = "motorway"
    TRUNK = "trunk"
    PRIMARY = "primary"
    SECONDARY = "secondary"
    TERTIARY = "tertiary"
    RESIDENTIAL = "residential"
    SERVICE = "service"
    UNCLASSIFIED = "unclassified"
    LIVING_STREET = "living_street"
    PEDESTRIAN = "pedestrian"
    TRACK = "track"


class Road(BaseModel):
    """A road segment in the network."""

    id: Optional[int] = None
    osm_id: Optional[int] = None
    name: Optional[str] = None
    road_type: RoadType = RoadType.RESIDENTIAL
    geometry_wkt: str
    length_m: float
    max_speed: Optional[float] = None  # km/h
    lanes: Optional[int] = None
    is_bridge: bool = False
    is_tunnel: bool = False
    is_oneway: bool = False
    surface: Optional[str] = None
    event_id: Optional[int] = None  # associated flood event context


class RoadCondition(BaseModel):
    """Current condition of a road segment during a flood event."""

    road_id: int
    event_id: int
    flood_depth: float = 0.0
    is_blocked: bool = False
    risk_score: float = 0.0
    last_updated: Optional[str] = None


# Road type speed factors for weight computation
ROAD_TYPE_FACTORS = {
    RoadType.MOTORWAY: 0.8,
    RoadType.TRUNK: 0.9,
    RoadType.PRIMARY: 1.0,
    RoadType.SECONDARY: 1.2,
    RoadType.TERTIARY: 1.3,
    RoadType.RESIDENTIAL: 1.5,
    RoadType.SERVICE: 1.8,
    RoadType.UNCLASSIFIED: 1.6,
    RoadType.LIVING_STREET: 2.0,
    RoadType.PEDESTRIAN: 2.5,
    RoadType.TRACK: 2.2,
}
