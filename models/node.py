"""
Graph node models — representing road intersections.
"""

from pydantic import BaseModel, Field
from typing import Optional


class GraphNode(BaseModel):
    """A node in the road network graph (intersection or endpoint)."""

    id: int = Field(description="OSM node ID or internal ID")
    latitude: float
    longitude: float
    elevation: Optional[float] = None
    is_intersection: bool = False
    street_count: int = 0  # number of streets meeting at this node


class NodeLocation(BaseModel):
    """Simplified node for spatial lookups."""

    node_id: int
    lat: float
    lon: float
