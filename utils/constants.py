"""
Application-wide constants.
"""

# ── Coordinate Reference Systems ─────────────────────────────────────────────
CRS_WGS84 = "EPSG:4326"  # Standard GPS (lat/lon)
CRS_WEB_MERCATOR = "EPSG:3857"  # Web mapping projection

# ── Flood Risk Thresholds ────────────────────────────────────────────────────
FLOOD_DEPTH_NONE = 0.0
FLOOD_DEPTH_LOW = 0.10
FLOOD_DEPTH_MODERATE = 0.30
FLOOD_DEPTH_HIGH = 0.60
FLOOD_DEPTH_CRITICAL = 1.0

# ── Risk Tiers ───────────────────────────────────────────────────────────────
RISK_TIERS = [
    (FLOOD_DEPTH_NONE, "NONE", "No flood exposure"),
    (FLOOD_DEPTH_LOW, "LOW", "Shallow water - passable on foot, most vehicles"),
    (FLOOD_DEPTH_MODERATE, "MODERATE", "Car limit reached - SUVs and trucks may pass"),
    (FLOOD_DEPTH_HIGH, "HIGH", "Impassable for most vehicles - specialist only"),
    (float("inf"), "CRITICAL", "Impassable - risk to life, do not attempt"),
]

# ── Routing ──────────────────────────────────────────────────────────────────
IMPASSABLE_WEIGHT = 1e9  # Weight assigned to completely blocked edges
DEFAULT_EDGE_LENGTH = 1.0  # Fallback length in meters if missing
MAX_K_ROUTES = 5
DEFAULT_K_ROUTES = 3

# ── OSM Network Types ────────────────────────────────────────────────────────
OSM_NETWORK_DRIVE = "drive"
OSM_NETWORK_WALK = "walk"
OSM_NETWORK_BIKE = "bike"

# ── Earth Radius ─────────────────────────────────────────────────────────────
EARTH_RADIUS_KM = 6371.0

# ── API Limits ───────────────────────────────────────────────────────────────
MAX_AMENITY_RESULTS = 15
MAX_ROUTE_HISTORY = 100
NOMINATIM_RATE_LIMIT_SECONDS = 1.0

# ── Cache Keys ───────────────────────────────────────────────────────────────
CACHE_KEY_GRAPH = "graph:{event_id}:{place}"
CACHE_KEY_WEIGHTS = "weights:{event_id}:{vehicle_type}"
CACHE_KEY_ROUTE = "route:{start}:{end}:{vehicle_type}"
