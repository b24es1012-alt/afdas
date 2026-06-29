"""
Graph edge models — representing road segments between nodes.
"""

from pydantic import BaseModel, Field
from typing import Optional


class GraphEdge(BaseModel):
    """An edge in the road network graph."""

    source_node: int
    target_node: int
    key: int = 0  # multi-edge key
    length_m: float
    road_type: str = "residential"
    max_speed: Optional[float] = None
    name: Optional[str] = None
    is_oneway: bool = False
    is_bridge: bool = False

    # Flood attributes (populated after flood intersection)
    flood_depth: float = 0.0
    is_flooded: bool = False

    # Weight attributes (computed per vehicle)
    base_weight: float = 0.0
    flood_penalty: float = 0.0
    total_weight: float = 0.0


class WeightedEdge(BaseModel):
    """Edge with vehicle-specific computed weight."""

    source_node: int
    target_node: int
    weight: float
    is_blocked: bool = False
    flood_depth: float = 0.0
    length_m: float = 0.0
    travel_time_s: float = 0.0
