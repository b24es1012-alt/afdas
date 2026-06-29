"""
Building and POI parser — extracts infrastructure from OSM data.
"""

import osmnx as ox
import geopandas as gpd
from typing import List, Optional
from shapely.geometry import Point

from utils.logger import logger


class BuildingParser:
    """
    Parses buildings and points of interest from OpenStreetMap.
    
    Extracts:
    - Hospitals
    - Schools
    - Shelters / evacuation centers
    - Police stations
    - Fire stations
    - Pharmacies
    - Mosques / religious buildings
    """

    # OSM tags for different building types
    AMENITY_TAGS = {
        "hospital": {"amenity": "hospital"},
        "school": {"amenity": "school"},
        "shelter": {"amenity": "shelter"},
        "police_station": {"amenity": "police"},
        "fire_station": {"amenity": "fire_station"},
        "pharmacy": {"amenity": "pharmacy"},
        "mosque": {"amenity": "place_of_worship"},
    }

    def download_buildings_for_place(
        self, place: str, building_type: Optional[str] = None
    ) -> gpd.GeoDataFrame:
        """
        Download buildings/POIs for a place from OSM.
        
        Args:
            place: Place name (e.g. "Gujrat, Punjab, Pakistan")
            building_type: Specific type or None for all
        
        Returns:
            GeoDataFrame of buildings
        """
        if building_type and building_type in self.AMENITY_TAGS:
            tags = self.AMENITY_TAGS[building_type]
        else:
            # Download all relevant amenities
            tags = {"amenity": True}

        try:
            gdf = ox.features_from_place(place, tags=tags)
            logger.info(f"Downloaded {len(gdf)} buildings/POIs for '{place}'")
            return gdf
        except Exception as e:
            logger.error(f"Error downloading buildings: {e}")
            return gpd.GeoDataFrame()

    def extract_buildings(
        self,
        gdf: gpd.GeoDataFrame,
        building_types: Optional[List[str]] = None,
    ) -> List[dict]:
        """
        Extract structured building data from a GeoDataFrame.
        
        Args:
            gdf: GeoDataFrame from OSM
            building_types: Filter to these types, or None for all
        
        Returns:
            List of building dicts
        """
        if gdf.empty:
            return []

        buildings = []
        target_amenities = set()

        if building_types:
            for bt in building_types:
                if bt in self.AMENITY_TAGS:
                    tag_val = list(self.AMENITY_TAGS[bt].values())[0]
                    target_amenities.add(tag_val)

        for idx, row in gdf.iterrows():
            amenity = row.get("amenity", "")
            if target_amenities and amenity not in target_amenities:
                continue

            # Get centroid for point representation
            geom = row.geometry
            if geom is None:
                continue

            if geom.geom_type == "Point":
                lat, lon = geom.y, geom.x
            else:
                centroid = geom.centroid
                lat, lon = centroid.y, centroid.x

            # Map OSM amenity to our building type
            building_type = self._map_amenity_type(amenity)

            name = row.get("name", "")
            if not name or name == "":
                name = f"{building_type.replace('_', ' ').title()} (unnamed)"

            # Check if it's an emergency facility
            is_emergency = building_type in (
                "hospital", "fire_station", "police_station", "shelter"
            )

            osm_id = None
            if isinstance(idx, tuple):
                osm_id = idx[1] if len(idx) > 1 else None
            elif isinstance(idx, int):
                osm_id = idx

            buildings.append({
                "osm_id": osm_id,
                "name": str(name),
                "building_type": building_type,
                "latitude": lat,
                "longitude": lon,
                "address": row.get("addr:full", row.get("addr:street", None)),
                "phone": row.get("phone", row.get("contact:phone", None)),
                "capacity": self._parse_capacity(row.get("capacity")),
                "is_emergency_facility": is_emergency,
            })

        logger.info(f"Extracted {len(buildings)} buildings")
        return buildings

    @staticmethod
    def _map_amenity_type(amenity: str) -> str:
        """Map OSM amenity value to our BuildingType."""
        mapping = {
            "hospital": "hospital",
            "clinic": "hospital",
            "doctors": "hospital",
            "school": "school",
            "university": "school",
            "college": "school",
            "shelter": "shelter",
            "police": "police_station",
            "fire_station": "fire_station",
            "pharmacy": "pharmacy",
            "place_of_worship": "mosque",
        }
        return mapping.get(amenity, "other")

    @staticmethod
    def _parse_capacity(value) -> Optional[int]:
        """Try to parse a capacity value."""
        if value is None:
            return None
        try:
            return int(value)
        except (ValueError, TypeError):
            return None
