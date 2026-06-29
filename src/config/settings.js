// Application-wide settings
const settings = {
  // Map defaults (Gujrat, Punjab, Pakistan)
  map: {
    center: [
      parseFloat(import.meta.env.VITE_MAP_CENTER_LAT) || 32.574,
      parseFloat(import.meta.env.VITE_MAP_CENTER_LON) || 73.677,
    ],
    zoom: parseInt(import.meta.env.VITE_MAP_ZOOM) || 13,
    maxZoom: 18,
    minZoom: 5,
    tileUrl: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
    tileAttribution:
      '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
  },

  // Vehicle types
  vehicles: [
    { id: 'walking', label: 'Walking', icon: 'footprints', maxDepth: 0.15 },
    { id: 'motorcycle', label: 'Motorcycle', icon: 'bike', maxDepth: 0.2 },
    { id: 'car', label: 'Car', icon: 'car', maxDepth: 0.3 },
    { id: 'suv', label: 'SUV / 4x4', icon: 'truck', maxDepth: 0.5 },
    { id: 'ambulance', label: 'Ambulance', icon: 'ambulance', maxDepth: 0.45 },
    { id: 'truck', label: 'Truck', icon: 'truck', maxDepth: 0.7 },
  ],

  // GPS tracking
  gps: {
    updateInterval: 5000, // ms
    highAccuracy: true,
    maxAge: 10000,
    timeout: 15000,
  },

  // Route options
  routing: {
    defaultK: 3,
    maxK: 5,
    defaultVehicle: 'car',
    defaultPlace: 'Gujrat, Punjab, Pakistan',
  },

  // Flood severity colors
  floodColors: {
    none: '#22c55e',
    low: '#eab308',
    moderate: '#f97316',
    high: '#ef4444',
    critical: '#7f1d1d',
  },

  // Route colors
  routeColors: ['#9B30FF', '#FF6600', '#000000'],
};

export default settings;
