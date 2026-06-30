-- ═══════════════════════════════════════════════════════════════════════════
-- AFDAS Database Schema — PostgreSQL + PostGIS
-- AI Flood Disaster Assistance System
-- ═══════════════════════════════════════════════════════════════════════════

-- Enable PostGIS extension
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;

-- ─── FLOOD EVENTS ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS flood_events (
    id              SERIAL PRIMARY KEY,
    activation_id   VARCHAR(50) UNIQUE NOT NULL,
    event_name      VARCHAR(255) NOT NULL,
    country         VARCHAR(100) NOT NULL,
    region          VARCHAR(100) NOT NULL,
    start_date      TIMESTAMP NOT NULL,
    end_date        TIMESTAMP,
    is_active       BOOLEAN DEFAULT TRUE,
    data_source     VARCHAR(50) DEFAULT 'copernicus_ems',
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_flood_events_active ON flood_events (is_active);
CREATE INDEX IF NOT EXISTS idx_flood_events_activation ON flood_events (activation_id);

-- ─── FLOOD ZONES (Polygons) ──────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS flood_zones (
    id              SERIAL PRIMARY KEY,
    event_id        INTEGER NOT NULL REFERENCES flood_events(id) ON DELETE CASCADE,
    geometry        GEOMETRY(MultiPolygon, 4326) NOT NULL,
    max_depth       FLOAT,
    avg_depth       FLOAT,
    area_km2        FLOAT,
    source_file     VARCHAR(255),
    created_at      TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_flood_zones_geom ON flood_zones USING GIST (geometry);
CREATE INDEX IF NOT EXISTS idx_flood_zones_event ON flood_zones (event_id);

-- ─── ROADS ───────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS roads (
    id              SERIAL PRIMARY KEY,
    osm_id          BIGINT UNIQUE,
    name            VARCHAR(255),
    road_type       VARCHAR(50) NOT NULL DEFAULT 'residential',
    geometry        GEOMETRY(LineString, 4326) NOT NULL,
    length_m        FLOAT NOT NULL DEFAULT 0,
    max_speed       FLOAT,
    lanes           INTEGER,
    is_bridge       BOOLEAN DEFAULT FALSE,
    is_tunnel       BOOLEAN DEFAULT FALSE,
    is_oneway       BOOLEAN DEFAULT FALSE,
    surface         VARCHAR(50),
    event_id        INTEGER REFERENCES flood_events(id),
    created_at      TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_roads_geom ON roads USING GIST (geometry);
CREATE INDEX IF NOT EXISTS idx_roads_type ON roads (road_type);
CREATE INDEX IF NOT EXISTS idx_roads_osm_id ON roads (osm_id);

-- ─── BUILDINGS ───────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS buildings (
    id                    SERIAL PRIMARY KEY,
    osm_id                BIGINT UNIQUE,
    name                  VARCHAR(255) NOT NULL,
    building_type         VARCHAR(50) NOT NULL,
    latitude              FLOAT NOT NULL,
    longitude             FLOAT NOT NULL,
    address               TEXT,
    phone                 VARCHAR(50),
    capacity              INTEGER,
    is_emergency_facility BOOLEAN DEFAULT FALSE,
    event_id              INTEGER REFERENCES flood_events(id),
    created_at            TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_buildings_type ON buildings (building_type);
CREATE INDEX IF NOT EXISTS idx_buildings_location ON buildings USING GIST (
    ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)
);

-- ─── USERS ───────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id              SERIAL PRIMARY KEY,
    email           VARCHAR(255) UNIQUE NOT NULL,
    password_hash   VARCHAR(255) NOT NULL,
    full_name       VARCHAR(255),
    role            VARCHAR(20) DEFAULT 'user',
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMP DEFAULT NOW(),
    last_login      TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users (email);

-- ─── FLOODED ROADS ───────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS flooded_roads (
    id                  SERIAL PRIMARY KEY,
    event_id            INTEGER NOT NULL REFERENCES flood_events(id) ON DELETE CASCADE,
    road_id             INTEGER NOT NULL REFERENCES roads(id) ON DELETE CASCADE,
    max_depth           FLOAT NOT NULL DEFAULT 0,
    avg_depth           FLOAT NOT NULL DEFAULT 0,
    flooded_percentage  FLOAT NOT NULL DEFAULT 0,
    risk_score          FLOAT NOT NULL DEFAULT 0,
    created_at          TIMESTAMP DEFAULT NOW(),
    UNIQUE(event_id, road_id)
);

CREATE INDEX IF NOT EXISTS idx_flooded_roads_event ON flooded_roads (event_id);
CREATE INDEX IF NOT EXISTS idx_flooded_roads_risk ON flooded_roads (risk_score DESC);

-- ─── FLOODED BUILDINGS ───────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS flooded_buildings (
    id                  SERIAL PRIMARY KEY,
    event_id            INTEGER NOT NULL REFERENCES flood_events(id) ON DELETE CASCADE,
    building_id         INTEGER NOT NULL REFERENCES buildings(id) ON DELETE CASCADE,
    water_depth         FLOAT NOT NULL DEFAULT 0,
    is_accessible       BOOLEAN DEFAULT TRUE,
    evacuation_needed   BOOLEAN DEFAULT FALSE,
    created_at          TIMESTAMP DEFAULT NOW(),
    UNIQUE(event_id, building_id)
);

CREATE INDEX IF NOT EXISTS idx_flooded_buildings_event ON flooded_buildings (event_id);

-- ─── ROUTE HISTORY ───────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS route_history (
    id                  SERIAL PRIMARY KEY,
    event_id            INTEGER REFERENCES flood_events(id),
    user_id             INTEGER REFERENCES users(id),
    start_lat           FLOAT NOT NULL,
    start_lon           FLOAT NOT NULL,
    end_lat             FLOAT NOT NULL,
    end_lon             FLOAT NOT NULL,
    vehicle_type        VARCHAR(20) NOT NULL DEFAULT 'car',
    total_distance_m    FLOAT NOT NULL DEFAULT 0,
    estimated_time_s    FLOAT NOT NULL DEFAULT 0,
    risk_score          FLOAT NOT NULL DEFAULT 0,
    route_geometry      GEOMETRY(LineString, 4326),
    flooded_segments    INTEGER DEFAULT 0,
    is_reroute          BOOLEAN DEFAULT FALSE,
    created_at          TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_route_history_event ON route_history (event_id);
CREATE INDEX IF NOT EXISTS idx_route_history_user ON route_history (user_id);
CREATE INDEX IF NOT EXISTS idx_route_history_date ON route_history (created_at DESC);

-- ─── GRAPH METADATA ──────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS graph_metadata (
    id              SERIAL PRIMARY KEY,
    event_id        INTEGER REFERENCES flood_events(id),
    place           VARCHAR(255) NOT NULL,
    vehicle_type    VARCHAR(20) NOT NULL,
    node_count      INTEGER DEFAULT 0,
    edge_count      INTEGER DEFAULT 0,
    blocked_edges   INTEGER DEFAULT 0,
    version         INTEGER DEFAULT 1,
    built_at        TIMESTAMP DEFAULT NOW(),
    expires_at      TIMESTAMP,
    UNIQUE(event_id, place, vehicle_type)
);

-- ─── VEHICLE PROFILES ────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS vehicle_profiles (
    id                    SERIAL PRIMARY KEY,
    vehicle_type          VARCHAR(20) UNIQUE NOT NULL,
    display_name          VARCHAR(50) NOT NULL,
    max_flood_depth       FLOAT NOT NULL,
    average_speed         FLOAT NOT NULL,
    flood_speed_factor    FLOAT DEFAULT 0.5,
    flood_penalty_factor  FLOAT DEFAULT 20.0,
    priority              INTEGER DEFAULT 0,
    created_at            TIMESTAMP DEFAULT NOW()
);

INSERT INTO vehicle_profiles (vehicle_type, display_name, max_flood_depth, average_speed, flood_penalty_factor, priority)
VALUES
    ('walking', 'Walking', 0.15, 5, 30, 0),
    ('motorcycle', 'Motorcycle', 0.20, 30, 25, 1),
    ('car', 'Car', 0.30, 40, 20, 2),
    ('suv', 'SUV / 4x4', 0.50, 35, 15, 3),
    ('ambulance', 'Ambulance', 0.45, 50, 15, 10),
    ('truck', 'Truck', 0.70, 30, 10, 4),
    ('boat', 'Rescue Boat', 999.0, 15, 0, 10)
ON CONFLICT (vehicle_type) DO NOTHING;

-- ─── VIEW: Active Flood Summary ──────────────────────────────────────────────
CREATE OR REPLACE VIEW v_active_flood_summary AS
SELECT
    fe.id as event_id,
    fe.activation_id,
    fe.event_name,
    fe.region,
    fe.start_date,
    COUNT(DISTINCT fz.id) as zone_count,
    COUNT(DISTINCT fr.id) as flooded_road_count,
    COUNT(DISTINCT fb.id) as flooded_building_count
FROM flood_events fe
LEFT JOIN flood_zones fz ON fz.event_id = fe.id
LEFT JOIN flooded_roads fr ON fr.event_id = fe.id
LEFT JOIN flooded_buildings fb ON fb.event_id = fe.id
WHERE fe.is_active = TRUE
GROUP BY fe.id;
