"""
Route visualization endpoint — generates an interactive HTML map.
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from typing import List, Tuple, Optional

router = APIRouter(prefix="/visualize", tags=["Visualization"])


class VisualizeRequest(BaseModel):
    """Request to visualize routes on a map."""
    routes: List[dict] = Field(..., description="Route objects from /navigation/route response")
    flood_zone: Optional[dict] = None  # Optional GeoJSON flood polygon
    center_lat: float = 28.63
    center_lon: float = 77.22
    zoom: int = 13


@router.post("/route", response_class=HTMLResponse)
async def visualize_route(request: VisualizeRequest):
    """Generate an interactive HTML map with routes."""

    if not request.routes:
        raise HTTPException(status_code=400, detail="No routes provided")

    # Generate route polylines JavaScript
    route_js = ""
    colors = ["#9B30FF", "#FF6600", "#000000", "#00AA00", "#FF0000"]

    for i, route in enumerate(request.routes):
        coords = route.get("coordinates", [])
        if not coords:
            continue

        color = colors[i % len(colors)]
        weight = 6 if i == 0 else 4
        opacity = 1.0 if i == 0 else 0.6
        dash = "null" if i == 0 else "'8 6'"

        coords_js = str(coords)
        distance = route.get("total_distance_m", 0)
        time_s = route.get("estimated_time_s", 0)
        risk = route.get("risk_score", 0)
        flooded = route.get("flooded_segments", 0)

        route_js += f"""
        var route{i} = L.polyline({coords_js}, {{
            color: '{color}', weight: {weight}, opacity: {opacity},
            dashArray: {dash}
        }}).addTo(map);
        route{i}.bindPopup('<b>Route {i+1}</b><br>Distance: {distance:.0f}m<br>Time: {time_s/60:.1f} min<br>Risk: {risk*100:.0f}%<br>Flooded segments: {flooded}');
        """

        # Add start/end markers for first route
        if i == 0 and len(coords) >= 2:
            route_js += f"""
            L.marker({coords[0]}).addTo(map).bindPopup('<b>START</b>');
            L.marker({coords[-1]}).addTo(map).bindPopup('<b>DESTINATION</b>');
            """

    # Flood zone overlay
    flood_js = ""
    if request.flood_zone:
        flood_js = f"""
        var floodZone = L.geoJSON({request.flood_zone}, {{
            style: {{ color: 'blue', fillColor: 'blue', fillOpacity: 0.25, weight: 1 }}
        }}).addTo(map);
        """

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>AFDAS - Route Visualization</title>
        <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
        <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
        <style>
            body {{ margin: 0; padding: 0; }}
            #map {{ height: 100vh; width: 100%; }}
            .legend {{
                position: fixed; bottom: 20px; left: 20px; z-index: 1000;
                background: white; padding: 12px 16px; border-radius: 8px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.2); font-size: 12px;
                font-family: sans-serif; line-height: 1.8;
            }}
        </style>
    </head>
    <body>
        <div id="map"></div>
        <div class="legend">
            <b>AFDAS Route Map</b><br>
            <span style="color:#9B30FF;">━━</span> Route 1 (Best)<br>
            <span style="color:#FF6600;">╌╌</span> Route 2 (Alt)<br>
            <span style="color:#000000;">┄┄</span> Route 3 (Alt)<br>
            <span style="color:blue; opacity:0.5;">▓▓</span> Flood zone
        </div>
        <script>
            var map = L.map('map').setView([{request.center_lat}, {request.center_lon}], {request.zoom});
            L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
                attribution: '&copy; OpenStreetMap'
            }}).addTo(map);

            {route_js}
            {flood_js}

            // Auto-fit bounds to routes
            var allCoords = [];
            {'; '.join([f"allCoords = allCoords.concat({route.get('coordinates', [])})" for route in request.routes])}
            if (allCoords.length > 0) {{
                map.fitBounds(allCoords);
            }}
        </script>
    </body>
    </html>
    """

    return HTMLResponse(content=html)


@router.get("/test", response_class=HTMLResponse)
async def test_map():
    """Simple test map to verify visualization works."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>AFDAS - Test Map</title>
        <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
        <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
        <style>#map { height: 100vh; width: 100%; }</style>
    </head>
    <body>
        <div id="map"></div>
        <script>
            var map = L.map('map').setView([28.63, 77.22], 12);
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(map);
            L.marker([28.6139, 77.2090]).addTo(map).bindPopup('India Gate');
            L.marker([28.6562, 77.2410]).addTo(map).bindPopup('Kashmere Gate');
            L.circle([28.64, 77.235], {radius: 1500, color: 'blue', fillOpacity: 0.2}).addTo(map).bindPopup('Flood Zone');
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html)
