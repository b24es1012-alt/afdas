"""
OpenStreetMap data downloader using OSMnx and Nominatim.
Downloads road networks and building/POI data for a given area.
"""

import time
import httpx
import osmnx as ox
import geopandas as gpd
import networkx as nx
from typing import Optional, List, Tuple
from pathlib import Path

from config.settings import settings
from utils.logger import logger


class OSMDownloader:
    """
    Downloads OpenStreetMap data for a specified area.
    
    Capabilities:
    - Download road network as a graph (via OSMnx)
    - Geocode place names to coordinates
    - Search amenities (hospitals, shelters, schools, etc.)
    - Get bounding box for a city/region
    """

    def __init__(self):
        self.data_dir = Path(settings.OSM_DATA_DIR)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.nominatim_url = settings.OSM_NOMINATIM_URL
        self.user_agent = settings.OSM_USER_AGENT
        self.rate_limit = settings.OSM_RATE_LIMIT

        # Configure OSMnx
        ox.settings.use_cache = True
        ox.settings.cache_folder = str(self.data_dir / "cache")
        ox.settings.log_console = False

    def download_road_network(
        self,
        place: str,
        network_type: str = "drive",
    ) -> nx.MultiDiGraph:
        """
        Download the road network for a place as a NetworkX graph.
        
        Args:
            place: Place name (e.g. "Gujrat, Punjab, Pakistan")
            network_type: 'drive', 'walk', 'bike', or 'all'
        
        Returns:
            NetworkX MultiDiGraph with road network
        """
        logger.info(f"Downloading road network for '{place}' (type={network_type})")
        G = ox.graph_from_place(place, network_type=network_type)
        logger.info(
            f"Downloaded: {G.number_of_nodes()} nodes, "
            f"{G.number_of_edges()} edges"
        )
        return G

    def download_road_network_bbox(
        self,
        north: float,
        south: float,
        east: float,
        west: float,
        network_type: str = "drive",
    ) -> nx.MultiDiGraph:
        """
        Download road network within a bounding box.
        
        Args:
            north, south, east, west: Bounding box coordinates
            network_type: Network type
        
        Returns:
            NetworkX MultiDiGraph
        """
        logger.info(f"Downloading road network for bbox [{south},{west}]-[{north},{east}]")
        G = ox.graph_from_bbox(
            north=north, south=south, east=east, west=west,
            network_type=network_type,
        )
        return G

    def download_road_network_point(
        self,
        lat: float,
        lon: float,
        dist_m: int = 5000,
        network_type: str = "drive",
    ) -> nx.MultiDiGraph:
        """
        Download road network around a point within a radius.
        
        Args:
            lat, lon: Center point
            dist_m: Radius in meters
            network_type: Network type
        
        Returns:
            NetworkX MultiDiGraph
        """
        logger.info(f"Downloading road network around ({lat},{lon}), radius={dist_m}m")
        G = ox.graph_from_point(
            (lat, lon), dist=dist_m, network_type=network_type
        )
        return G

    async def geocode_location(
        self,
        location_name: str,
        city: str = "Gujrat",
        state: str = "Punjab",
        country: str = "Pakistan",
        limit: int = 3,
    ) -> List[dict]:
        """
        Convert a location name to coordinates using Nominatim.
        
        Args:
            location_name: Name of the place
            city, state, country: Context for geocoding
            limit: Max results
        
        Returns:
            List of matching location dicts
        """
        query = f"{location_name}, {city}, {state}, {country}"
        params = {
            "q": query,
            "format": "json",
            "addressdetails": 1,
            "limit": limit,
        }

        time.sleep(self.rate_limit)

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.nominatim_url}/search",
                params=params,
                headers={"User-Agent": self.user_agent},
                timeout=10.0,
            )

        if response.status_code != 200:
            logger.error(f"Nominatim returned {response.status_code}")
            return []

        data = response.json()
        results = []
        for place in data:
            results.append({
                "name": place.get("display_name", ""),
                "lat": float(place.get("lat", 0)),
                "lon": float(place.get("lon", 0)),
                "type": place.get("type", ""),
                "osm_id": place.get("osm_id"),
            })

        return results

    async def search_amenities(
        self,
        amenity_type: str,
        city: str = "Gujrat",
        state: str = "Punjab",
        country: str = "Pakistan",
        limit: int = 15,
    ) -> List[dict]:
        """
        Search for amenities (hospitals, schools, shelters, etc.).
        
        Args:
            amenity_type: Type of amenity
            city, state, country: Location context
            limit: Max results
        
        Returns:
            List of amenity dicts with coordinates
        """
        query = f"{amenity_type} in {city}, {state}, {country}"
        params = {
            "q": query,
            "format": "json",
            "addressdetails": 1,
            "limit": limit,
        }

        time.sleep(self.rate_limit)

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.nominatim_url}/search",
                params=params,
                headers={"User-Agent": self.user_agent},
                timeout=10.0,
            )

        if response.status_code != 200:
            return []

        data = response.json()
        results = []
        for place in data:
            results.append({
                "name": place.get("display_name", "").split(",")[0].strip(),
                "full_name": place.get("display_name", ""),
                "lat": float(place.get("lat", 0)),
                "lon": float(place.get("lon", 0)),
                "type": place.get("type", ""),
                "osm_id": place.get("osm_id"),
            })

        return results

    async def get_city_bbox(
        self,
        city: str = "Gujrat",
        state: str = "Punjab",
        country: str = "Pakistan",
    ) -> Optional[dict]:
        """
        Get the bounding box for a city.
        
        Returns:
            Dict with min_lat, min_lon, max_lat, max_lon or None
        """
        params = {
            "format": "json",
            "city": city,
            "state": state,
            "country": country,
            "limit": 1,
        }

        time.sleep(self.rate_limit)

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.nominatim_url}/search",
                params=params,
                headers={"User-Agent": self.user_agent},
                timeout=10.0,
            )

        if response.status_code != 200:
            return None

        data = response.json()
        if not data:
            return None

        bbox = data[0].get("boundingbox")
        if not bbox:
            return None

        return {
            "min_lat": float(bbox[0]),
            "max_lat": float(bbox[1]),
            "min_lon": float(bbox[2]),
            "max_lon": float(bbox[3]),
            "center_lat": float(data[0].get("lat", 0)),
            "center_lon": float(data[0].get("lon", 0)),
        }
