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
