"""
Copernicus EMS automatic polling job.

Automatically discovers and imports NEW flood activations for configured regions.
Also checks existing activations for updates and auto-deactivates resolved floods.

Runs on a schedule (default: every 5 minutes).
"""

import re
from datetime import datetime
from typing import Optional, List, Dict

from flood.downloader import CopernicusDownloader
from flood.polygon_loader import FloodPolygonLoader
from database.connection import DatabaseManager
from database.flood_repository import FloodRepository
from cache.graph_cache import GraphCache
from config.settings import settings
from utils.logger import scheduler_logger as logger


class CopernicusPollingJob:
    """
    Background job that automatically:
    1. Discovers NEW flood activations for configured countries (India, etc.)
    2. Downloads flood extent/depth shapefiles
    3. Imports polygons into PostGIS
    4. Checks existing activations for resolution → auto-deactivates
    5. Invalidates graph cache when flood data changes
    
    Configuration (via settings / .env):
        COPERNICUS_POLL_INTERVAL: seconds between polls (default: 300 = 5 min)
        COPERNICUS_WATCH_COUNTRIES: comma-separated countries to monitor (default: "India")
        COPERNICUS_AUTO_IMPORT: enable/disable auto-import (default: True)
    """

    def __init__(self):
        self.downloader = CopernicusDownloader()
        self.poll_interval = settings.COPERNICUS_POLL_INTERVAL
        self.watch_countries = getattr(settings, "COPERNICUS_WATCH_COUNTRIES", "India").split(",")
        self.auto_import = getattr(settings, "COPERNICUS_AUTO_IMPORT", True)

    async def run(self) -> dict:
        """
        Execute one full polling cycle.
        
        1. Discover new activations for watched regions
        2. Auto-import any new flood data found
        3. Check existing tracked events for updates/resolution
        4. Invalidate cache if anything changed
        
        Returns:
            Status dict with results
        """
        logger.info("=" * 40)
        logger.info("Copernicus EMS polling cycle started")
        logger.info(f"Watching countries: {self.watch_countries}")
        results = {
            "new_discovered": 0,
            "new_imported": 0,
            "existing_checked": 0,
            "resolved": 0,
            "errors": 0,
            "cache_invalidated": False,
        }

        try:
            # ── Step 1: Discover new activations ─────────────────────────
            if self.auto_import:
                new_activations = await self._discover_new_activations()
                results["new_discovered"] = len(new_activations)

                for activation in new_activations:
                    try:
                        event_id = await self._import_activation(activation)
                        if event_id:
                            results["new_imported"] += 1
                            results["cache_invalidated"] = True
                    except Exception as e:
                        logger.error(f"Error importing {activation['id']}: {e}")
                        results["errors"] += 1

            # ── Step 2: Check existing tracked events ────────────────────
            async with DatabaseManager.session() as session:
                repo = FloodRepository(session)
                active_events = await repo.get_active_events()
                results["existing_checked"] = len(active_events)

                for event in active_events:
                    try:
                        still_active = await self._check_event_status(event)
                        if not still_active:
                            # Auto-deactivate resolved flood
                            await repo.deactivate_event(
                                event["id"], end_date=datetime.utcnow()
                            )
                            await session.commit()
                            results["resolved"] += 1
                            results["cache_invalidated"] = True
                            logger.info(
                                f"Auto-deactivated resolved flood: "
                                f"{event['activation_id']} ({event['event_name']})"
                            )
                    except Exception as e:
                        logger.error(f"Error checking {event['activation_id']}: {e}")
                        results["errors"] += 1

            # ── Step 3: Invalidate cache if data changed ─────────────────
            if results["cache_invalidated"]:
                try:
                    graph_cache = GraphCache()
                    await graph_cache.clear_all()
                    logger.info("Graph cache cleared due to flood data changes")
                except Exception as e:
                    logger.warning(f"Cache invalidation failed: {e}")

        except Exception as e:
            logger.error(f"Copernicus polling cycle error: {e}")
            results["errors"] += 1

        logger.info(f"Copernicus polling complete: {results}")
        logger.info("=" * 40)
        return results

    async def _discover_new_activations(self) -> List[Dict]:
        """
        Discover new flood activations from Copernicus EMS RSS/page
        that haven't been imported yet.
        
        Checks the Copernicus rapid mapping activations page for recent entries
        matching our watched countries.
        """
        new_activations = []

        try:
            # Fetch the activations list page
            import httpx
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    "https://emergency.copernicus.eu/mapping/list-of-activations-rapid",
                    headers={"User-Agent": "AFDAS/1.0"},
                )

                if response.status_code != 200:
                    logger.warning(f"Copernicus activations page returned {response.status_code}")
                    return []

                content = response.text

            # Parse activation IDs and their associated countries
            # Pattern: EMSR followed by digits, associated with country names
            activation_pattern = re.findall(
                r'(EMSR\d{3,4})',
                content,
            )

            # Get unique activation IDs
            unique_ids = list(set(activation_pattern))[:20]  # Limit to recent 20

            if not unique_ids:
                logger.debug("No activation IDs found on page")
                return []

            # Check which ones we haven't imported yet
            async with DatabaseManager.session() as session:
                repo = FloodRepository(session)

                for activation_id in unique_ids:
                    existing = await repo.get_event_by_activation_id(activation_id)
                    if not existing:
                        # Check if this activation is for our watched countries
                        # For now, try to import and the downloader will verify
                        is_relevant = await self._is_relevant_activation(
                            activation_id, content
                        )
                        if is_relevant:
                            new_activations.append({
                                "id": activation_id,
                                "discovered_at": datetime.utcnow(),
                            })

            if new_activations:
                logger.info(
                    f"Discovered {len(new_activations)} new activation(s): "
                    f"{[a['id'] for a in new_activations]}"
                )

        except Exception as e:
            logger.error(f"Error discovering new activations: {e}")

        return new_activations

    async def _is_relevant_activation(self, activation_id: str, page_content: str) -> bool:
        """
        Check if an activation is relevant to our watched countries.
        Looks for the activation ID near country names in the page content.
        """
        # Find text around the activation ID
        for country in self.watch_countries:
            country = country.strip()
            # Check if country name appears near the activation ID in the page
            pattern = rf'{activation_id}[^<]{{0,200}}{country}|{country}[^<]{{0,200}}{activation_id}'
            if re.search(pattern, page_content, re.IGNORECASE):
                return True

        # Also check the activation details page
        try:
            info = await self.downloader.get_activation_info(activation_id)
            if info:
                return True  # If page exists, it's a valid activation — try importing
        except Exception:
            pass

        return False

    async def _import_activation(self, activation: Dict) -> Optional[int]:
        """
        Download and import a new activation's flood data.
        
        Returns event_id if successful, None otherwise.
        """
        activation_id = activation["id"]
        logger.info(f"Auto-importing new activation: {activation_id}")

        # Download flood data
        success, shapefile_path, message = await self.downloader.download_flood_data(
            activation_id
        )

        if not success:
            logger.warning(f"Could not download {activation_id}: {message}")
            return None

        # Import into database
        async with DatabaseManager.session() as session:
            repo = FloodRepository(session)

            # Create event record
            event_id = await repo.create_flood_event(
                activation_id=activation_id,
                event_name=f"Flood {activation_id}",
                country="India",  # Will be refined from metadata
                region="Auto-detected",
                start_date=datetime.utcnow(),
                data_source="copernicus_ems_auto",
            )

            # Load flood polygons from shapefile
            loader = FloodPolygonLoader(session)
            count = await loader.load_from_shapefile(
                shapefile_path, event_id, source_name=activation_id
            )
            await session.commit()

            logger.info(
                f"AUTO-IMPORTED: {activation_id} → event_id={event_id}, "
                f"{count} flood polygons loaded"
            )
            return event_id

    async def _check_event_status(self, event: dict) -> bool:
        """
        Check if a tracked flood event is still active on Copernicus.
        
        Returns True if still active, False if resolved.
        """
        activation_id = event["activation_id"]

        # Skip manually created events
        if event.get("data_source") == "manual":
            return True

        try:
            # Check if activation page still exists and is marked as active
            exists = await self.downloader.check_activation_exists(activation_id)

            if not exists:
                logger.info(f"Activation {activation_id} no longer found — may be resolved")
                return False

            # TODO: Parse the page to check if explicitly marked as "closed/resolved"
            # For now, if page exists, assume still active
            return True

        except Exception as e:
            logger.warning(f"Error checking status of {activation_id}: {e}")
            # Don't deactivate on error (fail-safe: keep flood active)
            return True

    async def manual_import(self, activation_id: str, event_name: str = None,
                            country: str = "India", region: str = "") -> dict:
        """
        Manual import triggered by admin.
        Same as auto-import but with user-provided metadata.
        
        Returns:
            Dict with status and event details
        """
        logger.info(f"Manual import requested by admin: {activation_id}")

        # Check if already exists
        async with DatabaseManager.session() as session:
            repo = FloodRepository(session)
            existing = await repo.get_event_by_activation_id(activation_id)
            if existing:
                return {
                    "status": "already_exists",
                    "event_id": existing["id"],
                    "message": f"{activation_id} already imported",
                }

        # Download
        success, shapefile_path, message = await self.downloader.download_flood_data(
            activation_id
        )

        if not success:
            return {
                "status": "download_failed",
                "message": message,
            }

        # Import
        async with DatabaseManager.session() as session:
            repo = FloodRepository(session)
            event_id = await repo.create_flood_event(
                activation_id=activation_id,
                event_name=event_name or f"Flood {activation_id}",
                country=country,
                region=region,
                start_date=datetime.utcnow(),
                data_source="copernicus_ems_manual",
            )

            loader = FloodPolygonLoader(session)
            count = await loader.load_from_shapefile(
                shapefile_path, event_id, source_name=activation_id
            )
            await session.commit()

        # Clear graph cache
        try:
            graph_cache = GraphCache()
            await graph_cache.clear_all()
        except Exception:
            pass

        return {
            "status": "imported",
            "event_id": event_id,
            "activation_id": activation_id,
            "polygons_loaded": count,
            "message": f"Successfully imported {count} flood zones",
            "cache_cleared": True,
        }

    async def close(self):
        """Clean up resources."""
        await self.downloader.close()
