# AFDAS — AI Flood Disaster Assistance System

## Complete User Guide

---

## Table of Contents

1. [Getting Started](#getting-started)
2. [Dashboard](#dashboard)
3. [Navigation — Flood-Safe Routing](#navigation)
4. [AI Chat Assistant](#ai-chat-assistant)
5. [Flood Zones](#flood-zones)
6. [Analytics](#analytics)
7. [Settings](#settings)
8. [Admin Panel](#admin-panel)
9. [API Reference](#api-reference)
10. [Troubleshooting](#troubleshooting)

---

## Getting Started

### Creating an Account

1. Open the AFDAS website
2. Click **"Register"** on the landing page
3. Fill in:
   - **Email**: Your email address
   - **Password**: Minimum 8 characters, must include one uppercase letter and one number
   - **Full Name**: Your display name
4. Click **"Create Account"**
5. You'll be automatically logged in and redirected to the Dashboard

### Logging In

1. Click **"Login"**
2. Enter your email and password
3. Click **"Sign In"**

> **Note**: After 5 failed login attempts, your account is locked for 15 minutes (brute force protection).

### Session

- Your login session lasts **24 hours**
- The app will automatically refresh your token in the background
- If your session expires, you'll be redirected to the login page

---

## Dashboard

The Dashboard is your home screen after logging in. It shows:

- **Your current GPS location** (if permission granted)
- **Quick links** to Navigation, Chat, and Analytics
- **Active flood alerts** in your area
- **Recent route history**

---

## Navigation

The Navigation page is the core feature — finding **flood-safe routes** between two points.

### Step-by-Step: Finding a Safe Route

#### 1. Select Your City/Area

- Use the **city preset buttons** (Delhi, Mumbai, Chennai, Bangalore, Kolkata, Hyderabad)
- OR type any city name in the text field (e.g., "Dehradun, India")
- The map will center on your selected city

> **Auto-detection**: If you allow GPS, the app automatically detects your city and switches to it.

#### 2. Set Your Origin (Point A - Green)

You have 3 ways to set the origin:

| Method | How |
|--------|-----|
| **Search by name** | Type a place name (e.g., "India Gate", "AIIMS Hospital") and click "Find" |
| **Pick on map** | Click "Pick Map" button, then click anywhere on the map |
| **Use GPS** | Click "GPS" to use your current location |

#### 3. Set Your Destination (Point B - Red)

Same 3 methods as origin:
- **Search by name**: Type and click "Find"
- **Pick on map**: Click "Pick Map", then click the map
- **Enter coordinates**: Manually type latitude/longitude

#### 4. Select Vehicle Type

Choose your vehicle from the selector:

| Vehicle | Max Flood Depth | Best For |
|---------|----------------|----------|
| Walking | 0.15m | Pedestrians |
| Motorcycle | 0.20m | Two-wheelers |
| Car | 0.30m | Standard cars |
| SUV | 0.50m | Off-road vehicles |
| Ambulance | 0.45m | Emergency services |
| Truck | 0.70m | Heavy vehicles |

> The vehicle selection affects which flooded roads are marked as passable vs blocked.

#### 5. Custom Clearance (Optional)

If you know your vehicle's exact water wading depth:
1. Toggle **"Custom Clearance"** to ON
2. Enter depth in meters (e.g., 0.45)
3. This overrides the vehicle's default limit

#### 6. Load Flood Zones (Optional but Recommended)

Click **"Load from DB"** in the Flood Zones section to display active flood polygons on the map:
- **Blue zones**: Shallow flooding (< 0.5m)
- **Orange zones**: Moderate flooding (0.5 - 1.0m)
- **Red zones**: Deep flooding (> 1.0m)

#### 7. Calculate Route

Click **"Find Safe Route"**

The system will:
1. Download the road network for your area (cached after first use)
2. Download neighboring city maps for cross-boundary routing
3. Apply flood data to mark dangerous roads
4. Calculate up to 3 alternative routes
5. Display them on the map

#### 8. Understanding Route Results

Routes are displayed as colored lines on the map:

| Color | Meaning |
|-------|---------|
| Purple (thick) | Best/selected route |
| Orange (thin dashed) | Alternative route 2 |
| Black (thin dashed) | Alternative route 3 |

Each route card shows:
- **Distance**: Total route length in km
- **Time**: Estimated travel time
- **Risk %**: Flood risk score (0% = safe, 100% = very dangerous)
- **Flooded segments**: Number of road segments passing through flood zones

Click a route card to select it and highlight it on the map.

#### 9. Start Navigation (Follow Me)

After selecting a route:
1. Click **"Start Navigation (Follow Me)"**
2. The map will follow your GPS position in real-time
3. The blue pulsing dot shows your current location
4. Click again to stop following

### Cross-City Routing

AFDAS automatically handles routes that cross city boundaries:

- If your destination is outside the current city, the system downloads additional map data
- For known metro areas (Delhi-NCR, Mumbai metro, etc.), neighboring cities are pre-loaded
- Example: A route from Delhi to Noida will automatically download both city maps and merge them

### Nearby Cities Indicator

When your origin or destination is near a city boundary, you'll see an **indigo "NEAR CITY BORDER"** indicator showing:
- Which direction the border is
- Which neighboring cities will be auto-downloaded
- Message: "Maps for these areas will auto-download for best routing"

---

## AI Chat Assistant

The AI assistant is available on every page as a **floating chat bubble** (bottom-right corner).

### Opening the Chat

Click the **blue chat bubble** in the bottom-right corner to open the assistant.

### What You Can Ask

| Category | Example Questions |
|----------|------------------|
| **Safe routes** | "Find a safe route to the nearest hospital" |
| **Flood info** | "Is India Gate area flooded?" |
| **Flood depth** | "What's the flood depth at 28.61, 77.23?" |
| **Vehicle check** | "Can my car pass through Connaught Place?" |
| **Amenity search** | "Find shelters near me" |
| **Route calculation** | "Route from India Gate to AIIMS" |
| **Multi-stop** | "Safest order to visit 3 hospitals" |
| **Area status** | "Which hospitals in Delhi are flooded?" |

### How It Works

1. Type your question and press Enter (or click Send)
2. The AI will:
   - Classify your query (flood navigation, emergency, amenity search, etc.)
   - Plan which tools to use
   - Execute searches, flood checks, and route calculations
   - Generate a safety-focused response

### AI Routes on Map

When the AI calculates a route:
- The route is **automatically displayed on the navigation map**
- A purple **"Route displayed on map"** badge appears on the message
- Click **"Show on Map Again"** to re-display a previous route
- Origin (A) and Destination (B) markers are set automatically

### Session Memory

The AI **remembers your conversation** within a session:
- You can say "now route me there" after asking about a location
- It remembers your vehicle type, locations mentioned, and context
- Sessions expire after 1 hour of inactivity
- Click the **reset button** (circular arrow icon) in the chat header to start fresh

### Quick Suggestions

Pre-built prompts are shown below the messages:
- "Safe route to hospital"
- "Route from India Gate to AIIMS"
- "Which areas are flooded?"
- "Can ambulance reach me?"

Click any suggestion to auto-fill it.

### GPS Context

If you've allowed GPS:
- The AI automatically knows your location
- It detects your city from GPS (not always Delhi!)
- You can ask "route me to nearest hospital" without specifying origin

---

## Flood Zones

### Viewing Flood Data

On the Navigation page:
1. Click **"Load from DB"** in the Flood Zones section
2. Flood polygons appear on the map with color coding:
   - **Blue**: Shallow (< 0.5m) — passable for most vehicles
   - **Orange**: Moderate (0.5 - 1.0m) — SUVs and trucks only
   - **Red**: Deep (> 1.0m) — impassable for all road vehicles
3. Click any flood polygon to see details (event name, depth, area)

### How Flood Data Affects Routing

- Routes are calculated **avoiding flooded roads** based on your vehicle type
- If a car route must pass through shallow water, it's marked in the risk score
- The system uses real Copernicus EMS data loaded into the database

### Hide Flood Zones

Click **"Hide"** next to the flood zone count to remove them from the map.

---

## Analytics

The Analytics page shows post-flood analysis:

- **Affected roads**: How many roads are flooded, by severity
- **Affected buildings**: Hospitals, schools, shelters in flood zones
- **Route history**: Your past routes with risk scores
- **Event timeline**: When floods started/ended

---

## Settings

Access from the sidebar menu:

- **Profile**: Update name, email
- **Vehicle default**: Set your default vehicle type
- **Notifications**: Enable/disable flood alerts
- **GPS**: Enable/disable background location tracking
- **Theme**: Light/dark mode (if available)

---

## Admin Panel

> Admin access requires the `admin` role. Contact your system administrator.

### Admin Capabilities

- **View all users**: `GET /api/v1/auth/users` — see registered users
- **Promote users**: Direct database access (SQL)

### Granting Admin Access

```sql
-- Run this in your PostgreSQL database
UPDATE users SET role = 'admin' WHERE email = 'admin@example.com';
```

---

## API Reference

### Authentication

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/v1/auth/register` | POST | No | Create account |
| `/api/v1/auth/login` | POST | No | Login (returns JWT) |
| `/api/v1/auth/refresh` | POST | No | Refresh access token |
| `/api/v1/auth/users` | GET | Admin | List all users |

### Navigation

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/v1/navigation/route` | POST | Optional | Calculate flood-safe route |
| `/api/v1/navigation/reroute` | POST | Optional | Reroute from current position |
| `/api/v1/navigation/nearby-cities` | POST | No | Check border proximity |
| `/api/v1/navigation/neighbors/{place}` | GET | No | List neighboring cities |
| `/api/v1/navigation/route/history` | GET | Required | Get route history |

### AI Chat

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/v1/chat` | POST | Optional | Send message to AI agent |
| `/api/v1/chat/session/{id}` | GET | No | Get session info |
| `/api/v1/chat/session/{id}/history` | GET | No | Get chat history |
| `/api/v1/chat/session/{id}` | DELETE | No | Clear session |

### Flood Data

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/v1/flood/zones/geojson` | GET | No | Get flood zones as GeoJSON |
| `/api/v1/flood/events` | GET | No | List flood events |

### Health

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/health` | GET | No | System health check |

---

## Troubleshooting

### "No routes found"

**Causes and fixes:**
1. **Points too far from roads**: Pick points closer to actual roads/intersections
2. **All roads flooded**: Try a vehicle with higher flood tolerance (truck, SUV)
3. **Different city**: Make sure both points are in the selected city area
4. **Custom clearance too low**: Increase the clearance value

### "Rate limit exceeded"

You've made too many requests. Wait:
- General endpoints: 60 seconds
- Login: 5 minutes
- AI chat: 60 seconds

### GPS not working

1. Check browser permissions (allow location)
2. Use HTTPS (geolocation requires secure context)
3. Try the "GPS" button on the origin section

### AI not responding

1. Check your internet connection
2. The AI needs the GROQ_API_KEY to be configured on the backend
3. Try refreshing the page and sending again

### Map not loading tiles

1. Check internet connection (map tiles come from OpenStreetMap)
2. Try zooming in/out
3. Clear browser cache

### "Source and target are the same node"

The origin and destination are too close together or both snap to the same road intersection. Move one of them slightly.

### Login locked out

After 5 failed attempts, wait 15 minutes. The lockout resets automatically.

---

## Technical Notes

### Copernicus EMS — How Flood Data is Collected

AFDAS uses **Copernicus Emergency Management Service (EMS) Rapid Mapping** as its primary flood data source. Here's the complete pipeline:

#### What is Copernicus EMS?

Copernicus EMS is a European Union satellite-based service that provides rapid mapping of natural disasters. When a flood occurs, they:
1. Acquire satellite imagery of the affected area
2. Produce **flood extent** and **flood depth** maps as shapefiles
3. Publish them with activation IDs (e.g., `EMSR838`)

#### The Data Pipeline (How AFDAS Gets Flood Data)

```
┌─────────────────────────────────────────────────────────────┐
│  COPERNICUS EMS                                             │
│  https://emergency.copernicus.eu/mapping                    │
│                                                             │
│  Publishes: Flood extent/depth shapefiles (.shp/.zip)      │
│  Format: GeoJSON / Shapefile with depth column              │
│  IDs: EMSR838, EMSR900, etc.                               │
└────────────────────────────┬────────────────────────────────┘
                             │
                    ┌────────▼────────┐
                    │  DOWNLOADER      │
                    │  flood/          │
                    │  downloader.py   │
                    │                  │
                    │  1. Check if     │
                    │     activation   │
                    │     exists       │
                    │  2. List products│
                    │  3. Download ZIP │
                    │  4. Extract .shp │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │  POLYGON LOADER  │
                    │  flood/          │
                    │  polygon_loader  │
                    │                  │
                    │  1. Read .shp    │
                    │  2. Set CRS to   │
                    │     WGS-84       │
                    │  3. Detect depth │
                    │     column       │
                    │  4. Insert into  │
                    │     PostGIS      │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │  DATABASE        │
                    │  (PostGIS)       │
                    │                  │
                    │  flood_events    │
                    │  flood_zones     │
                    │  (geometry +     │
                    │   max_depth)     │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
     ┌────────▼───┐  ┌──────▼──────┐  ┌───▼────────┐
     │ ROUTING    │  │ AI AGENT    │  │ FRONTEND   │
     │            │  │             │  │            │
     │ Marks roads│  │ check_flood │  │ GeoJSON    │
     │ as flooded │  │ _depth()    │  │ on map     │
     │ in graph   │  │             │  │ (blue/     │
     │            │  │ assess_path │  │  orange/   │
     │ Avoids in  │  │ _flood_risk │  │  red)      │
     │ route calc │  │             │  │            │
     └────────────┘  └─────────────┘  └────────────┘
```

#### Step-by-Step Breakdown

**Step 1: Scheduler Polls Copernicus (Background Job)**

File: `scheduler/copernicus_job.py`

```python
# Runs every 5 minutes (configurable: COPERNICUS_POLL_INTERVAL)
# Checks tracked activations for updates
active_events = await repo.get_active_events()
for event in active_events:
    exists = await downloader.check_activation_exists(event["activation_id"])
```

**Step 2: Download Flood Data**

File: `flood/downloader.py` — `CopernicusDownloader`

```python
# Full workflow for a new activation:
success, shapefile_path, message = await downloader.download_flood_data("EMSR838")

# Internally:
# 1. GET https://emergency.copernicus.eu/mapping/list-of-components/EMSR838
# 2. Parse HTML for ZIP download links
# 3. Prefer "flood_depth" product, then "flood_extent"
# 4. Download ZIP → extract → find .shp file
# 5. Return path to shapefile
```

**Step 3: Load into PostGIS**

File: `flood/polygon_loader.py` — `FloodPolygonLoader`

```python
# Read shapefile → insert each polygon into flood_zones table
loader = FloodPolygonLoader(session)
count = await loader.load_from_shapefile(shapefile_path, event_id)

# For each polygon:
#   - Geometry stored as PostGIS geometry (SRID 4326)
#   - Auto-detects depth column (depth, water_depth, max_depth, etc.)
#   - Computes area in km²
#   - Links to flood_event
```

**Step 4: Create Flood Event Record**

File: `database/flood_repository.py`

```python
event_id = await repo.create_flood_event(
    activation_id="EMSR838",
    event_name="Flood EMSR838",
    country="India",
    region="Punjab",
    start_date=datetime.utcnow(),
    data_source="copernicus_ems",
)
```

**Step 5: Flood Data Used in Routing**

File: `graph/builder.py` → `api/navigation.py`

When a route is calculated:
1. `navigation.py` queries PostGIS for active flood zones
2. Builds a GeoDataFrame from the results
3. Passes to `GraphBuilder._annotate_flood()` 
4. Spatial join: each road edge gets a `flood_level` based on which polygons it intersects
5. `WeightEngine` marks edges with `flood_level > vehicle.max_flood_depth` as IMPASSABLE
6. Routing algorithm avoids those edges

**Step 6: Flood Data Used by AI Agent**

The AI uses PostGIS spatial queries directly:
- `check_flood_depth(lat, lon)` → `ST_Intersects(geometry, ST_MakePoint(lon, lat))`
- `check_amenity_flood_status()` → finds buildings inside flood polygons
- `assess_path_flood_risk()` → checks multiple points along a corridor

#### Database Schema for Flood Data

```sql
-- Flood events (one per Copernicus activation)
flood_events:
  id, activation_id, event_name, country, region,
  start_date, end_date, is_active, data_source, created_at

-- Flood zone polygons (many per event)
flood_zones:
  id, event_id, geometry (PostGIS), max_depth, avg_depth,
  area_km2, source_file, created_at

-- Roads affected by flooding (computed by intersection engine)
flooded_roads:
  id, event_id, road_id, max_depth, avg_depth,
  flooded_percentage, risk_score, created_at

-- Buildings affected by flooding
flooded_buildings:
  id, event_id, building_id, water_depth,
  is_accessible, evacuation_needed, created_at
```

#### How to Import Real Flood Data

**Option A: Via Activation ID (automatic)**
```python
from scheduler.copernicus_job import CopernicusPollingJob
job = CopernicusPollingJob()
event_id = await job.check_new_activation("EMSR838")
```

**Option B: Manual shapefile import (via pgAdmin or script)**
```python
from flood.polygon_loader import FloodPolygonLoader
from database.connection import DatabaseManager

async with DatabaseManager.session() as session:
    repo = FloodRepository(session)
    
    # Create event first
    event_id = await repo.create_flood_event(
        activation_id="MANUAL_001",
        event_name="Delhi Floods July 2024",
        country="India",
        region="Delhi",
        start_date=datetime(2024, 7, 15),
    )
    
    # Load shapefile
    loader = FloodPolygonLoader(session)
    count = await loader.load_from_shapefile(
        "/path/to/flood_extent.shp", event_id
    )
    await session.commit()
```

**Option C: Insert GeoJSON directly via SQL**
```sql
-- Create event
INSERT INTO flood_events (activation_id, event_name, country, region, start_date, is_active, data_source, created_at)
VALUES ('MANUAL_DELHI', 'Delhi Flood Test', 'India', 'Delhi', NOW(), TRUE, 'manual', NOW())
RETURNING id;  -- e.g. returns id = 1

-- Insert a flood polygon (rectangle around Connaught Place)
INSERT INTO flood_zones (event_id, geometry, max_depth, area_km2, created_at)
VALUES (
  1,
  ST_GeomFromText('POLYGON((77.20 28.62, 77.24 28.62, 77.24 28.65, 77.20 28.65, 77.20 28.62))', 4326),
  0.8,
  1.2,
  NOW()
);
```

#### Supported Flood Data Formats

| Format | Extension | Supported |
|--------|-----------|-----------|
| ESRI Shapefile | .shp + .dbf + .shx | Yes |
| GeoJSON | .geojson / .json | Yes |
| GeoPackage | .gpkg | Yes |
| KML/KMZ | .kml / .kmz | Via conversion |

#### Depth Column Auto-Detection

The loader automatically detects the depth column by searching for:
- `depth`
- `water_depth`
- `flood_depth`
- `max_depth`
- `wdepth`

If no depth column exists, all intersecting polygons default to **1.0m depth**.

---

### Data Sources

| Data | Source | Update Frequency |
|------|--------|-----------------|
| Road network | OpenStreetMap (via OSMnx) | Cached 24h, re-downloads on cache miss |
| Flood zones | Copernicus EMS / Manual import | As events occur |
| Geocoding | Nominatim (OpenStreetMap) | Real-time |
| AI responses | Groq (Llama 3.3 70B) | Real-time |

### Caching Strategy

| What | Where | TTL |
|------|-------|-----|
| Road graphs | Redis | 24 hours |
| Route weights | Redis | 1 hour |
| Computed routes | Redis | 30 minutes |
| Chat sessions | Redis | 1 hour |
| Merged multi-city graphs | Redis | 24 hours |

### Security

- Passwords: bcrypt (12 rounds)
- Authentication: JWT (24h access, 7d refresh)
- Rate limiting: Redis-based sliding window
- Brute force: 5 attempts → 15min lockout
- CORS: Restricted to configured origins
- Headers: HSTS, CSP, X-Frame-Options, nosniff
- Docs: Disabled in production

---

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| Enter (in search) | Search for place |
| Enter (in chat) | Send message |
| Escape | Cancel map pick mode |

---

## Browser Support

| Browser | Supported |
|---------|-----------|
| Chrome 90+ | Yes |
| Firefox 90+ | Yes |
| Safari 14+ | Yes |
| Edge 90+ | Yes |
| Mobile Chrome/Safari | Yes |

---

## Contact & Support

For issues, bugs, or feature requests:
- GitHub: https://github.com/b24es1012-alt/afdas
- Create an issue on the repository

---

*AFDAS v1.0.0 — AI Flood Disaster Assistance System*
