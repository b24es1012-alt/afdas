"""
Weight builder job — pre-computes vehicle weight tables when flood data changes.
"""

from typing import List

from graph.loader import GraphLoader
from graph.weights import WeightEngine
from cache.graph_cache import GraphCache
from models.vehicle import VEHICLE_PROFILES, VehicleType
from config.settings import settings
from utils.logger import scheduler_logger as logger


# Popular vehicles to pre-compute (most requested)
PRECOMPUTE_VEHICLES = [
    VehicleType.CAR,
    VehicleType.AMBULANCE,
    VehicleType.TRUCK,
]


class WeightBuilderJob:
    """
    Pre-builds weighted graphs for popular vehicle types.
    
    Triggered when:
    - New flood data is imported
    - Flood zones are updated
    - Cache expires
    """

    def __init__(self):
        self.graph_cache = GraphCache()
        self.graph_loader = GraphLoader(graph_cache=self.graph_cache)
        self.weight_engine = WeightEngine()

    async def run(
        self,
        place: str = "New Delhi, India",
        flood_shapefile: str = None,
        event_id: str = None,
    ) -> dict:
        """
        Pre-compute weighted graphs for all popular vehicles.
        
        Args:
            place: Target area
            flood_shapefile: Path to current flood data
            event_id: Flood event ID
        
        Returns:
            Status dict
        """
        logger.info(f"Weight builder started for '{place}'")
        results = {"computed": 0, "failed": 0, "vehicles": []}

        for vehicle_type in PRECOMPUTE_VEHICLES:
            try:
                # This will build and cache the weighted graph
                await self.graph_loader.get_weighted_graph(
                    place=place,
                    vehicle_type=vehicle_type.value,
                    flood_shapefile=flood_shapefile,
                    event_id=event_id,
                )

                results["computed"] += 1
                results["vehicles"].append(vehicle_type.value)
                logger.info(f"Pre-computed weights for: {vehicle_type.value}")

            except Exception as e:
                logger.error(f"Weight build failed for {vehicle_type.value}: {e}")
                results["failed"] += 1

        logger.info(f"Weight builder complete: {results}")
        return results

    async def invalidate_and_rebuild(
        self,
        place: str = "New Delhi, India",
        flood_shapefile: str = None,
        event_id: str = None,
    ) -> dict:
        """Invalidate existing caches and rebuild all weights."""
        logger.info("Invalidating caches and rebuilding weights...")

        # Clear existing
        await self.graph_loader.invalidate()

        # Rebuild
        return await self.run(place, flood_shapefile, event_id)
