// API endpoints
export const ENDPOINTS = {
  // Auth
  LOGIN: '/auth/login',
  REGISTER: '/auth/register',
  REFRESH: '/auth/refresh',

  // Navigation
  ROUTE: '/navigation/route',
  REROUTE: '/navigation/reroute',
  ROUTE_HISTORY: '/navigation/route/history',

  // Flood
  FLOOD_DEPTH: '/flood/depth',
  FLOOD_ACTIVE: '/flood/active',
  FLOOD_ZONES: '/flood/zones',
  FLOOD_DOWNLOAD: '/flood/download',
  FLOOD_EVENTS: '/flood/events',

  // Chat
  CHAT: '/chat',

  // Analytics
  ANALYTICS_ROADS: '/analytics/roads/most-flooded',
  ANALYTICS_BUILDINGS: '/analytics/buildings/most-affected',
  ANALYTICS_EVENT_SUMMARY: '/analytics/event',
  ANALYTICS_INFRASTRUCTURE: '/analytics/event',

  // Health
  HEALTH: '/health',
};

// Flood severity levels
export const SEVERITY = {
  NONE: 'none',
  LOW: 'low',
  MODERATE: 'moderate',
  HIGH: 'high',
  CRITICAL: 'critical',
};

// Severity labels
export const SEVERITY_LABELS = {
  none: 'Safe',
  low: 'Low Risk',
  moderate: 'Moderate Risk',
  high: 'High Risk',
  critical: 'Critical - Danger',
};

// Vehicle types
export const VEHICLE_TYPES = {
  WALKING: 'walking',
  MOTORCYCLE: 'motorcycle',
  CAR: 'car',
  SUV: 'suv',
  AMBULANCE: 'ambulance',
  TRUCK: 'truck',
};

// WebSocket events
export const WS_EVENTS = {
  GPS_UPDATE: 'gps:update',
  ROUTE_UPDATE: 'route:update',
  FLOOD_ALERT: 'flood:alert',
  REROUTE_NEEDED: 'reroute:needed',
  ROAD_CLOSED: 'road:closed',
};

// Local storage keys
export const STORAGE_KEYS = {
  ACCESS_TOKEN: 'afdas_access_token',
  REFRESH_TOKEN: 'afdas_refresh_token',
  USER: 'afdas_user',
  SETTINGS: 'afdas_settings',
};
