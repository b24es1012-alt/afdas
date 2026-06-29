-- ═══════════════════════════════════════════════════════════════════════════
-- AFDAS Database Schema — PostgreSQL + PostGIS
-- AI Flood Disaster Assistance System
-- ═══════════════════════════════════════════════════════════════════════════

-- Enable PostGIS extension
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;

-- ─── FLOOD EVENTS ────────────────────────────────────────────────────────────
-- Metadata about each flood activation from Copernicus EMS
CREATE TABLE IF NOT EXISTS flood_events (
    id              SERIAL PRIMARY KEY,
    activation_id   VARCHAR(50) UNIQUE NOT NULL,  -- e.g. EMSR838
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

CREATE INDEX idx_flood_events_active ON flood_events (is_active);
CREATE INDEX idx_flood_events_activation ON flood_events (activation_id);

-- ─── FLOOD ZONES (Polygons) ──────────────────────────────────────────────────
-- Actual flood extent polygons from shapefiles
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

-- Spatial index for fast intersection queries
CREATE INDEX idx_flood_zones_geom ON flood_zones USING GIST (geometry);
CREATE INDEX idx_flood_zones_event ON flood_zones (event_id);

-- ─── ROADS ───────────────────────────────────────────────────────────────────
-- Road network from OpenStreetMap
CREATE TABLE IF NOT EXISTS roads (
    id              SERIAL PRIMARY KEY,
    osm_id          BIGINT UNIQUE,
    name            VARCHAR(255),
    road_type       VARCHAR(50) NOT NULL DEFAULT 'residential',
    geometry        GEOMETRY(LineString, 4326) NOT NULL,
    length_m        FLOAT NOT NULL DEFAULT 0,
    max_speed       FLOAT,           -- km/h
    lanes           INTEGER,
    is_bridge       BOOLEAN DEFAULT FALSE,
    is_tunnel       BOOLEAN DEFAULT FALSE,
    is_oneway       BOOLEAN DEFAULT FALSE,
    surface         VARCHAR(50),
    event_id        INTEGER REFERENCES flood_events(id),
    created_at      TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_roads_geom ON roads USING GIST (geometry);
CREATE INDEX idx_roads_type ON roads (road_type);
CREATE INDEX idx_roads_osm_id ON roads (osm_id);

-- ─── BUILDINGS ───────────────────────────────────────────────────────────────
-- Hospitals, schools, shelters, and other infrastructure
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

CREATE INDEX idx_buildings_type ON buildings (building_type);
CREATE INDEX idx_buildings_location ON buildings USING GIST (
    ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)
);
