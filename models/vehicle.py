"""
Vehicle profile models.
Each vehicle type has specific flood tolerance, speed, and road restrictions.
"""

from pydantic import BaseModel, Field
from enum import Enum
from typing import Dict, List, Optional


class VehicleType(str, Enum):
    WALKING = "walking"
    MOTORCYCLE = "motorcycle"
    CAR = "car"
    SUV = "suv"
    AMBULANCE = "ambulance"
    TRUCK = "truck"
    BOAT = "boat"


class VehicleProfile(BaseModel):
    """Defines a vehicle's capabilities in flood conditions."""

    vehicle_type: VehicleType
    display_name: str
    max_flood_depth: float = Field(description="Maximum passable water depth in metres")
    average_speed: float = Field(description="Average speed in km/h under normal conditions")
    flood_speed_factor: float = Field(
        default=0.5, description="Speed multiplier when in shallow flood"
    )
    flood_penalty_factor: float = Field(
        default=20.0, description="Weight penalty multiplier for flooded edges"
    )
    road_restrictions: List[str] = Field(
        default_factory=list,
        description="Road types this vehicle cannot use (e.g. 'motorway' for walking)"
    )
    priority: int = Field(
        default=0, description="Priority level (higher = more priority, e.g. ambulance=10)"
    )


# ============================================================================
# DEFAULT VEHICLE PROFILES
# ============================================================================

VEHICLE_PROFILES: Dict[VehicleType, VehicleProfile] = {
    VehicleType.WALKING: VehicleProfile(
        vehicle_type=VehicleType.WALKING,
        display_name="Walking",
        max_flood_depth=0.15,
        average_speed=5,
        flood_speed_factor=0.3,
        flood_penalty_factor=30,
        road_restrictions=["motorway", "trunk"],
        priority=0,
    ),
    VehicleType.MOTORCYCLE: VehicleProfile(
        vehicle_type=VehicleType.MOTORCYCLE,
        display_name="Motorcycle",
        max_flood_depth=0.20,
        average_speed=30,
        flood_speed_factor=0.4,
        flood_penalty_factor=25,
        road_restrictions=[],
        priority=1,
    ),
    VehicleType.CAR: VehicleProfile(
        vehicle_type=VehicleType.CAR,
        display_name="Car",
        max_flood_depth=0.30,
        average_speed=40,
        flood_speed_factor=0.5,
        flood_penalty_factor=20,
        road_restrictions=[],
        priority=2,
    ),
    VehicleType.SUV: VehicleProfile(
        vehicle_type=VehicleType.SUV,
        display_name="SUV / 4x4",
        max_flood_depth=0.50,
        average_speed=35,
        flood_speed_factor=0.6,
        flood_penalty_factor=15,
        road_restrictions=[],
        priority=3,
    ),
    VehicleType.AMBULANCE: VehicleProfile(
        vehicle_type=VehicleType.AMBULANCE,
        display_name="Ambulance",
        max_flood_depth=0.45,
        average_speed=50,
        flood_speed_factor=0.5,
        flood_penalty_factor=15,
        road_restrictions=[],
        priority=10,
    ),
    VehicleType.TRUCK: VehicleProfile(
        vehicle_type=VehicleType.TRUCK,
        display_name="Truck",
        max_flood_depth=0.70,
        average_speed=30,
        flood_speed_factor=0.5,
        flood_penalty_factor=10,
        road_restrictions=["residential", "service"],
        priority=4,
    ),
    VehicleType.BOAT: VehicleProfile(
        vehicle_type=VehicleType.BOAT,
        display_name="Rescue Boat",
        max_flood_depth=999.0,
        average_speed=15,
        flood_speed_factor=1.0,
        flood_penalty_factor=0,
        road_restrictions=[],
        priority=10,
    ),
}


def get_vehicle_profile(vehicle_type: str) -> VehicleProfile:
    """Retrieve a vehicle profile by string name."""
    try:
        vt = VehicleType(vehicle_type.lower())
    except ValueError:
        vt = VehicleType.CAR
    return VEHICLE_PROFILES[vt]
