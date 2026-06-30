import { useState } from 'react';
import { Loader2, RotateCcw, MapPin, Navigation as NavIcon, Droplets } from 'lucide-react';
import { MapContainer, TileLayer, Marker, Polyline, Popup, useMapEvents, GeoJSON } from 'react-leaflet';
import L from 'leaflet';
import VehicleSelector from '../components/navigation/VehicleSelector';
import { useVehicleStore } from '../store/vehicleStore';
import axios from 'axios';

const API_URL = 'http://localhost:8000/api/v1';

// Custom marker icons
const originIcon = L.divIcon({
  className: '',
  html: '<div style="background:#22c55e;width:28px;height:28px;border-radius:50%;border:3px solid white;box-shadow:0 2px 8px rgba(0,0,0,0.3);display:flex;align-items:center;justify-content:center;color:white;font-weight:bold;font-size:12px;">A</div>',
  iconSize: [28, 28],
  iconAnchor: [14, 14],
});

const destIcon = L.divIcon({
  className: '',
  html: '<div style="background:#ef4444;width:28px;height:28px;border-radius:50%;border:3px solid white;box-shadow:0 2px 8px rgba(0,0,0,0.3);display:flex;align-items:center;justify-content:center;color:white;font-weight:bold;font-size:12px;">B</div>',
  iconSize: [28, 28],
  iconAnchor: [14, 14],
});

// Route colors
const ROUTE_COLORS = ['#9B30FF', '#FF6600', '#000000'];

export default function Navigation() {
  // Origin & Destination
  const [origin, setOrigin] = useState({ lat: '', lon: '', name: '' });
  const [destination, setDestination] = useState({ lat: '', lon: '', name: '' });
  const [place, setPlace] = useState('New Delhi, India');

  // Routes
  const [routes, setRoutes] = useState([]);
  const [selectedRouteIndex, setSelectedRouteIndex] = useState(0);
  const [isCalculating, setIsCalculating] = useState(false);
  const [error, setError] = useState(null);

  // Map interaction
  const [selectMode, setSelectMode] = useState(null);

  // Flood zones from database
  const [dbFloodZones, setDbFloodZones] = useState(null);
  const [loadingFlood, setLoadingFlood] = useState(false);

  const { selectedVehicle } = useVehicleStore();

  // Map center based on place
  const getMapCenter = () => {
    if (origin.lat && origin.lon) return [parseFloat(origin.lat), parseFloat(origin.lon)];
    const centers = {
      'New Delhi, India': [28.63, 77.22],
      'Central Delhi, India': [28.63, 77.22],
      'Mumbai, India': [19.07, 72.87],
      'Chennai, India': [13.08, 80.27],
      'Gujrat, Punjab, Pakistan': [32.57, 73.67],
      'Lahore, Pakistan': [31.52, 74.35],
    };
    return centers[place] || [28.63, 77.22];
  };

  // Handle map click
  const handleMapClick = (latlng) => {
    if (selectMode === 'origin') {
      setOrigin({ lat: latlng.lat.toFixed(5), lon: latlng.lng.toFixed(5), name: `${latlng.lat.toFixed(4)}, ${latlng.lng.toFixed(4)}` });
      setSelectMode(null);
    } else if (selectMode === 'destination') {
      setDestination({ lat: latlng.lat.toFixed(5), lon: latlng.lng.toFixed(5), name: `${latlng.lat.toFixed(4)}, ${latlng.lng.toFixed(4)}` });
      setSelectMode(null);
    }
  };

  // Calculate route
  const handleCalculateRoute = async () => {
    if (!origin.lat || !destination.lat) {
      setError('Set both origin and destination');
      return;
    }
    setIsCalculating(true);
    setError(null);
    setRoutes([]);

    try {
      const response = await axios.post(`${API_URL}/navigation/route`, {
        start_lat: parseFloat(origin.lat),
        start_lon: parseFloat(origin.lon),
        end_lat: parseFloat(destination.lat),
        end_lon: parseFloat(destination.lon),
        vehicle_type: selectedVehicle,
        k: 3,
        place: place,
        event_id: null,
      });

      if (response.data.success && response.data.routes.length > 0) {
        setRoutes(response.data.routes);
        setSelectedRouteIndex(0);
      } else {
        setError(response.data.message || 'No routes found');
      }
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed');
    } finally {
      setIsCalculating(false);
    }
  };

  // Use GPS
  const useGPS = () => {
    navigator.geolocation?.getCurrentPosition(
      (pos) => setOrigin({ lat: pos.coords.latitude.toFixed(5), lon: pos.coords.longitude.toFixed(5), name: 'My Location' }),
      () => setError('GPS denied')
    );
  };

  // Load flood zones from database
  const loadFloodZones = async (eventId = null) => {
    setLoadingFlood(true);
    try {
      const url = eventId
        ? `${API_URL}/flood/zones/geojson?event_id=${eventId}`
        : `${API_URL}/flood/zones/geojson`;
      const res = await axios.get(url);
      setDbFloodZones(res.data);
    } catch (err) {
      console.error('Failed to load flood zones:', err);
    } finally {
      setLoadingFlood(false);
    }
  };

  // City presets
  const cityPresets = [
    { name: 'Delhi', place: 'New Delhi, India', center: [28.63, 77.22] },
    { name: 'Gujrat PK', place: 'Gujrat, Punjab, Pakistan', center: [32.57, 73.67] },
    { name: 'Mumbai', place: 'Mumbai, India', center: [19.07, 72.87] },
    { name: 'Lahore', place: 'Lahore, Pakistan', center: [31.52, 74.35] },
  ];

  return (
    <div className="p-4 max-w-7xl mx-auto">
      <h1 className="text-2xl font-bold text-gray-800 mb-4 flex items-center gap-2">
        <NavIcon className="w-6 h-6 text-primary-600" />
        Flood-Safe Navigation
      </h1>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Controls */}
        <div className="space-y-3 overflow-y-auto max-h-[85vh]">

          {/* City Selection */}
          <div className="card p-3">
            <label className="text-xs font-semibold text-gray-600 block mb-1">CITY / AREA</label>
            <input type="text" value={place} onChange={(e) => setPlace(e.target.value)} className="input-field text-sm mb-2" placeholder="Type city name..." />
            <div className="flex flex-wrap gap-1">
              {cityPresets.map((c) => (
                <button key={c.name} onClick={() => setPlace(c.place)} className={`text-[10px] px-2 py-1 rounded ${place === c.place ? 'bg-primary-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}>
                  {c.name}
                </button>
              ))}
            </div>
          </div>

          {/* Origin */}
          <div className="card p-3 border-l-4 border-green-500">
            <div className="flex items-center justify-between mb-2">
              <label className="text-xs font-semibold text-green-700">ORIGIN (A)</label>
              <div className="flex gap-2">
                <button onClick={useGPS} className="text-[10px] px-2 py-0.5 bg-blue-50 text-blue-600 rounded hover:bg-blue-100">GPS</button>
                <button onClick={() => setSelectMode('origin')} className={`text-[10px] px-2 py-0.5 rounded ${selectMode === 'origin' ? 'bg-green-600 text-white' : 'bg-green-50 text-green-600 hover:bg-green-100'}`}>
                  {selectMode === 'origin' ? 'Clicking...' : 'Pick Map'}
                </button>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <input type="number" step="any" value={origin.lat} onChange={(e) => setOrigin({...origin, lat: e.target.value})} className="input-field text-xs py-1.5" placeholder="Latitude" />
              <input type="number" step="any" value={origin.lon} onChange={(e) => setOrigin({...origin, lon: e.target.value})} className="input-field text-xs py-1.5" placeholder="Longitude" />
            </div>
            {origin.name && <p className="text-[10px] text-green-600 mt-1">{origin.name}</p>}
          </div>

          {/* Destination */}
          <div className="card p-3 border-l-4 border-red-500">
            <div className="flex items-center justify-between mb-2">
              <label className="text-xs font-semibold text-red-700">DESTINATION (B)</label>
              <button onClick={() => setSelectMode('destination')} className={`text-[10px] px-2 py-0.5 rounded ${selectMode === 'destination' ? 'bg-red-600 text-white' : 'bg-red-50 text-red-600 hover:bg-red-100'}`}>
                {selectMode === 'destination' ? 'Clicking...' : 'Pick Map'}
              </button>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <input type="number" step="any" value={destination.lat} onChange={(e) => setDestination({...destination, lat: e.target.value})} className="input-field text-xs py-1.5" placeholder="Latitude" />
              <input type="number" step="any" value={destination.lon} onChange={(e) => setDestination({...destination, lon: e.target.value})} className="input-field text-xs py-1.5" placeholder="Longitude" />
            </div>
            {destination.name && <p className="text-[10px] text-red-600 mt-1">{destination.name}</p>}
          </div>

          {/* Vehicle */}
          <VehicleSelector />

              )}

              {/* Database Flood Zones (GeoJSON) */}
              {dbFloodZones && dbFloodZones.features && dbFloodZones.features.length > 0 && (
                <GeoJSON
                  key={JSON.stringify(dbFloodZones)}
                  data={dbFloodZones}
                  style={(feature) => {
                    const depth = feature.properties.max_depth || 0.5;
                    let color = '#3b82f6';
                    if (depth > 1.0) color = '#7f1d1d';
                    else if (depth > 0.6) color = '#ef4444';
                    else if (depth > 0.3) color = '#f97316';
                    return { color, fillColor: color, fillOpacity: 0.3, weight: 2 };
                  }}
                  onEachFeature={(feature, layer) => {
                    const p = feature.properties;
                    layer.bindPopup(`<b>${p.event_name || 'Flood Zone'}</b><br/>Max Depth: ${p.max_depth || '?'}m<br/>Avg Depth: ${p.avg_depth || '?'}m<br/>Area: ${p.area_km2?.toFixed(2) || '?'} km²`);
                  }}
                />
              )}
            </MapContainer>
          </div>

          {/* Route summary */}
          {routes.length > 0 && routes[selectedRouteIndex] && (
            <div className="mt-4 card p-4">
              <h3 className="text-sm font-semibold mb-2" style={{color: ROUTE_COLORS[selectedRouteIndex]}}>Route {selectedRouteIndex+1} Summary</h3>
              <div className="grid grid-cols-4 gap-3 text-center text-sm">
                <div className="bg-gray-50 p-2 rounded">
                  <p className="font-bold text-gray-800">{(routes[selectedRouteIndex].total_distance_m/1000).toFixed(1)} km</p>
                  <p className="text-[10px] text-gray-500">Distance</p>
                </div>
                <div className="bg-gray-50 p-2 rounded">
                  <p className="font-bold text-gray-800">{Math.round(routes[selectedRouteIndex].estimated_time_s/60)} min</p>
                  <p className="text-[10px] text-gray-500">Time</p>
                </div>
                <div className="bg-gray-50 p-2 rounded">
                  <p className="font-bold text-gray-800">{Math.round(routes[selectedRouteIndex].risk_score*100)}%</p>
                  <p className="text-[10px] text-gray-500">Risk</p>
                </div>
                <div className="bg-gray-50 p-2 rounded">
                  <p className="font-bold text-gray-800">{routes[selectedRouteIndex].flooded_segments}</p>
                  <p className="text-[10px] text-gray-500">Flooded Segs</p>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// Map click handler component
function MapClickHandler({ onClick }) {
  useMapEvents({
    click: (e) => onClick(e.latlng),
  });
  return null;
}
