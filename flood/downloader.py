"""
Copernicus Emergency Management Service (EMS) data downloader.
Checks for available flood activations, downloads shapefiles/GeoJSON.
"""

import os
import re
import zipfile
import tempfile
import httpx
from typing import Optional, List, Tuple
from pathlib import Path

from config.settings import settings
from utils.logger import flood_logger as logger


class CopernicusDownloader:
    """
    Downloads flood data from Copernicus EMS Rapid Mapping.
    
    Workflow:
    1. Check if activation exists (e.g. EMSR838)
    2. List available products/components for the activation
    3. Download the flood extent/depth shapefile
    4. Extract and return path to shapefile
    """

    BASE_URL = "https://emergency.copernicus.eu/mapping"
    ACTIVATIONS_URL = f"{BASE_URL}/list-of-activations-rapid"

    def __init__(self, data_dir: Optional[str] = None):
        self.data_dir = Path(data_dir or settings.FLOOD_DATA_DIR)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.client = httpx.AsyncClient(
            timeout=120.0,
            headers={"User-Agent": "AFDAS-FloodNavigation/1.0"},
        )

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

    async def check_activation_exists(self, activation_id: str) -> bool:
        """
        Check if a Copernicus EMS activation exists.
        
        Args:
            activation_id: e.g. "EMSR838"
        
        Returns:
            True if activation found
        """
        try:
            url = f"{self.BASE_URL}/list-of-components/{activation_id}"
            response = await self.client.get(url)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Error checking activation {activation_id}: {e}")
            return False

    async def get_activation_info(self, activation_id: str) -> Optional[dict]:
        """
        Get metadata for a Copernicus EMS activation.
        
        Returns:
            Dict with activation details or None
        """
        try:
            url = f"{self.BASE_URL}/list-of-components/{activation_id}"
            response = await self.client.get(url)

            if response.status_code != 200:
                return None

            # Parse the HTML response for activation info
            # In production, use the Copernicus CEMS API or RSS feed
            return {
                "activation_id": activation_id,
                "url": url,
                "status": "available",
            }
        except Exception as e:
            logger.error(f"Error fetching activation info: {e}")
            return None


    async def list_products(self, activation_id: str) -> List[dict]:
        """
        List available data products for an activation.
        Products include: flood extent, flood depth, delineation, grading.
        
        Returns:
            List of available product dicts
        """
        try:
            url = f"{self.BASE_URL}/list-of-components/{activation_id}"
            response = await self.client.get(url)

            if response.status_code != 200:
                return []

            # Parse available products from the activation page
            # Each product has: AOI, product type, version
            products = []

            # Look for download links in the page
            content = response.text

            # Pattern for product ZIP files
            zip_pattern = re.findall(
                r'href="([^"]*' + activation_id + r'[^"]*\.zip)"',
                content,
            )

            for i, link in enumerate(zip_pattern):
                product_type = "unknown"
                if "floodDepth" in link or "DEL" in link:
                    product_type = "flood_depth"
                elif "floodExtent" in link or "DEL" in link:
                    product_type = "flood_extent"
                elif "observedEvent" in link:
                    product_type = "observed_event"

                products.append({
                    "index": i,
                    "url": link if link.startswith("http") else f"{self.BASE_URL}/{link}",
                    "product_type": product_type,
                    "filename": link.split("/")[-1],
                })

            logger.info(f"Found {len(products)} products for {activation_id}")
            return products

        except Exception as e:
            logger.error(f"Error listing products for {activation_id}: {e}")
            return []

    async def download_product(
        self, download_url: str, activation_id: str
    ) -> Optional[str]:
        """
        Download a product ZIP file and extract it.
        
        Args:
            download_url: Direct URL to the ZIP file
            activation_id: For organizing storage
        
        Returns:
            Path to extracted directory, or None on failure
        """
        try:
            activation_dir = self.data_dir / activation_id
            activation_dir.mkdir(parents=True, exist_ok=True)

            # Download the ZIP
            logger.info(f"Downloading: {download_url}")
            response = await self.client.get(download_url, follow_redirects=True)

            if response.status_code != 200:
                logger.error(f"Download failed with status {response.status_code}")
                return None

            # Save ZIP file
            zip_filename = download_url.split("/")[-1]
            zip_path = activation_dir / zip_filename

            with open(zip_path, "wb") as f:
                f.write(response.content)

            logger.info(f"Downloaded {zip_filename} ({len(response.content)} bytes)")

            # Extract
            extract_dir = activation_dir / zip_filename.replace(".zip", "")
            extract_dir.mkdir(parents=True, exist_ok=True)

            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(extract_dir)

            logger.info(f"Extracted to {extract_dir}")
            return str(extract_dir)

        except Exception as e:
            logger.error(f"Error downloading product: {e}")
            return None

    async def find_shapefile(self, directory: str, pattern: str = "flood") -> Optional[str]:
        """
        Find a shapefile (.shp) in a directory matching a pattern.
        
        Args:
            directory: Directory to search
            pattern: Substring to match in filename (case-insensitive)
        
        Returns:
            Path to .shp file or None
        """
        dir_path = Path(directory)
        for shp_file in dir_path.rglob("*.shp"):
            if pattern.lower() in shp_file.name.lower():
                logger.info(f"Found shapefile: {shp_file}")
                return str(shp_file)

        # Fallback: any .shp file
        for shp_file in dir_path.rglob("*.shp"):
            return str(shp_file)

        return None

    async def download_flood_data(
        self, activation_id: str
    ) -> Tuple[bool, Optional[str], str]:
        """
        Full workflow: check activation → list products → download → extract → find shapefile.
        
        Args:
            activation_id: Copernicus EMS ID (e.g. "EMSR838")
        
        Returns:
            (success, shapefile_path, message)
        """
        # Check if already downloaded
        activation_dir = self.data_dir / activation_id
        if activation_dir.exists():
            existing_shp = await self.find_shapefile(str(activation_dir))
            if existing_shp:
                logger.info(f"Flood data already exists: {existing_shp}")
                return True, existing_shp, "Data already downloaded"

        # Check activation exists
        exists = await self.check_activation_exists(activation_id)
        if not exists:
            return False, None, f"Activation {activation_id} not found on Copernicus EMS"

        # List available products
        products = await self.list_products(activation_id)
        if not products:
            return False, None, f"No downloadable products found for {activation_id}"

        # Prefer flood_depth, then flood_extent
        target = None
        for ptype in ["flood_depth", "flood_extent", "observed_event"]:
            target = next((p for p in products if p["product_type"] == ptype), None)
            if target:
                break

        if not target:
            target = products[0]  # Take first available

        # Download and extract
        extract_path = await self.download_product(target["url"], activation_id)
        if not extract_path:
            return False, None, "Download failed"

        # Find the shapefile
        shp_path = await self.find_shapefile(extract_path)
        if not shp_path:
            return False, None, "No shapefile found in downloaded data"

        return True, shp_path, f"Successfully downloaded {activation_id}"
