"""
Copernicus EMS polling job — checks for new or updated flood activations.
Runs on a schedule (default: every 5 minutes during active floods).
"""

from datetime import datetime
from typing import Optional

from flood.downloader import CopernicusDownloader
from flood.polygon_loader import FloodPolygonLoader
from database.connection import DatabaseManager
from database.flood_repository import FloodRepository
from config.settings import settings
from utils.logger import scheduler_logger as logger


class CopernicusPollingJob:
    """
    Background job that periodically checks Copernicus EMS for updates.
    
    Workflow:
    1. Check currently tracked activations for updates
    2. Download new/updated flood data
    3. Load into PostGIS
    4. Trigger cache invalidation
    """

    def __init__(self):
        self.downloader = CopernicusDownloader()
        self.poll_interval = settings.COPERNICUS_POLL_INTERVAL

    async def run(self) -> dict:
        """
        Execute one polling cycle.
        
        Returns:
            Status dict with results
        """
        logger.info("Copernicus polling job started")
        results = {"checked": 0, "updated": 0, "errors": 0}

        try:
            async with DatabaseManager.session() as session:
                repo = FloodRepository(session)

                # Get active events to check
                active_events = await repo.get_active_events()
                results["checked"] = len(active_events)

                for event in active_events:
                    try:
                        activation_id = event["activation_id"]
                        # Check if new data available
                        exists = await self.downloader.check_activation_exists(activation_id)

                        if exists:
                            logger.info(f"Activation {activation_id} still active")
                            # TODO: Compare file hashes to detect actual updates
                        else:
                            logger.info(f"Activation {activation_id} may be resolved")

                    except Exception as e:
                        logger.error(f"Error checking {event['activation_id']}: {e}")
                        results["errors"] += 1

        except Exception as e:
            logger.error(f"Copernicus polling job error: {e}")
            results["errors"] += 1

        logger.info(f"Copernicus polling complete: {results}")
        return results

    async def check_new_activation(self, activation_id: str) -> Optional[int]:
        """
        Check and import a specific new activation.
        
        Returns:
            event_id if new data found and imported, None otherwise
        """
        success, shapefile_path, message = await self.downloader.download_flood_data(
            activation_id
        )

        if not success:
            logger.warning(f"No data for {activation_id}: {message}")
            return None

        # Import into database
        async with DatabaseManager.session() as session:
            repo = FloodRepository(session)

            # Create event
            event_id = await repo.create_flood_event(
                activation_id=activation_id,
                event_name=f"Flood {activation_id}",
                country="India",  # TODO: Extract from metadata
                region="Punjab",
                start_date=datetime.utcnow(),
            )

            # Load polygons
            loader = FloodPolygonLoader(session)
            count = await loader.load_from_shapefile(
                shapefile_path, event_id, source_name=activation_id
            )
            logger.info(f"Imported {count} polygons for {activation_id}")

        return event_id

    async def close(self):
        """Clean up resources."""
        await self.downloader.close()
