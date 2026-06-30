import { useState } from 'react';
import { Loader2, RotateCcw, MapPin, Navigation as NavIcon, Droplets, Plus, Trash2 } from 'lucide-react';
import { MapContainer, TileLayer, Marker, Polyline, Popup, Circle, useMapEvents, Polygon } from 'react-leaflet';
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

  // Virtual flood zone
  const [floodEnabled, setFloodEnabled] = useState(false);
  const [floodCenter, setFloodCenter] = useState(null);
  const [floodRadius, setFloodRadius] = useState(1000); // meters
  const [floodDepth, setFloodDepth] = useState(0.8);
  const [selectFloodMode, setSelectFloodMode] = useState(false);

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
    } else if (selectFloodMode) {
      setFloodCenter({ lat: latlng.lat, lon: latlng.lng });
      setFloodEnabled(true);
      setSelectFloodMode(false);
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
      // If virtual flood, create it in DB first
      if (floodEnabled && floodCenter) {
        try {
          await axios.post(`${API_URL}/flood/depth`, {
            lat: floodCenter.lat,
            lon: floodCenter.lon,
          });
        } catch (e) { /* ignore */ }
      }

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

          {/* Virtual Flood Zone */}
          <div className="card p-3 border-l-4 border-blue-500">
            <div className="flex items-center justify-between mb-2">
              <label className="text-xs font-semibold text-blue-700 flex items-center gap-1">
                <Droplets className="w-3 h-3" /> VIRTUAL FLOOD ZONE
              </label>
              <button onClick={() => { setFloodEnabled(!floodEnabled); if (floodEnabled) setFloodCenter(null); }} className={`text-[10px] px-2 py-0.5 rounded ${floodEnabled ? 'bg-blue-600 text-white' : 'bg-blue-50 text-blue-600'}`}>
                {floodEnabled ? 'ON' : 'OFF'}
              </button>
            </div>
            {floodEnabled && (
              <div className="space-y-2">
                <button onClick={() => setSelectFloodMode(true)} className={`text-xs w-full py-1.5 rounded ${selectFloodMode ? 'bg-blue-600 text-white' : 'bg-blue-50 text-blue-700 hover:bg-blue-100'}`}>
                  {selectFloodMode ? 'Click map to place flood...' : 'Place Flood on Map'}
                </button>
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <label className="text-[10px] text-gray-500">Radius (m)</label>
                    <input type="number" value={floodRadius} onChange={(e) => setFloodRadius(Number(e.target.value))} className="input-field text-xs py-1" />
                  </div>
                  <div>
                    <label className="text-[10px] text-gray-500">Depth (m)</label>
                    <input type="number" step="0.1" value={floodDepth} onChange={(e) => setFloodDepth(Number(e.target.value))} className="input-field text-xs py-1" />
                  </div>
                </div>
                {floodCenter && (
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] text-blue-600">Flood at: {floodCenter.lat.toFixed(4)}, {floodCenter.lon.toFixed(4)}</span>
                    <button onClick={() => { setFloodCenter(null); setFloodEnabled(false); }} className="text-[10px] text-red-500"><Trash2 className="w-3 h-3" /></button>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Calculate */}
          <button
            onClick={handleCalculateRoute}
            disabled={!origin.lat || !destination.lat || isCalculating}
            className="btn-primary w-full flex items-center justify-center gap-2 py-3"
          >
            {isCalculating ? <Loader2 className="w-5 h-5 animate-spin" /> : <NavIcon className="w-5 h-5" />}
            {isCalculating ? 'Calculating...' : 'Find Safe Route'}
          </button>

          {/* Error */}
          {error && <div className="bg-red-50 border border-red-200 rounded-lg p-2 text-xs text-red-700">{error}</div>}

          {/* Route cards */}
          {routes.length > 0 && (
            <>
              <button onClick={() => { setRoutes([]); setError(null); }} className="btn-secondary w-full flex items-center justify-center gap-2 text-sm">
                <RotateCcw className="w-4 h-4" /> Clear
              </button>
              <div className="space-y-2">
                <h3 className="text-xs font-semibold text-gray-700">{routes.length} Route(s) Found</h3>
                {routes.map((route, idx) => (
                  <button key={idx} onClick={() => setSelectedRouteIndex(idx)}
                    className={`w-full text-left p-3 rounded-lg border-2 text-xs ${idx === selectedRouteIndex ? 'border-purple-500 bg-purple-50' : 'border-gray-200 hover:border-gray-300'}`}>
                    <div className="flex items-center justify-between">
                      <span className="font-semibold" style={{color: ROUTE_COLORS[idx]}}>Route {idx+1}</span>
                      <span className="text-gray-500">{Math.round(route.risk_score*100)}% risk</span>
                    </div>
                    <div className="flex gap-3 mt-1 text-gray-600">
                      <span>{(route.total_distance_m/1000).toFixed(1)} km</span>
                      <span>{Math.round(route.estimated_time_s/60)} min</span>
                      <span>{route.flooded_segments} flooded</span>
                    </div>
                  </button>
                ))}
              </div>
            </>
          )}

          {/* Selection mode indicator */}
          {(selectMode || selectFloodMode) && (
            <div className="bg-yellow-50 border border-yellow-300 rounded-lg p-2 text-xs text-yellow-800 animate-pulse">
              Click on the map to set <strong>{selectMode || 'flood zone'}</strong>
              <button onClick={() => { setSelectMode(null); setSelectFloodMode(false); }} className="ml-2 underline">Cancel</button>
            </div>
          )}
        </div>

        {/* MAP */}
        <div className="lg:col-span-2">
          <div className="rounded-xl overflow-hidden shadow border border-gray-200 h-[600px]">
            <MapContainer center={getMapCenter()} zoom={12} className="w-full h-full" scrollWheelZoom={true}>
              <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" attribution="&copy; OpenStreetMap" />
              <MapClickHandler onClick={handleMapClick} />

              {/* Origin marker */}
              {origin.lat && origin.lon && (
                <Marker position={[parseFloat(origin.lat), parseFloat(origin.lon)]} icon={originIcon}>
                  <Popup><b>Origin (A)</b><br/>{origin.name || `${origin.lat}, ${origin.lon}`}</Popup>
                </Marker>
              )}

              {/* Destination marker */}
              {destination.lat && destination.lon && (
                <Marker position={[parseFloat(destination.lat), parseFloat(destination.lon)]} icon={destIcon}>
                  <Popup><b>Destination (B)</b><br/>{destination.name || `${destination.lat}, ${destination.lon}`}</Popup>
                </Marker>
              )}

              {/* Routes */}
              {routes.map((route, idx) => (
                route.coordinates && route.coordinates.length > 0 && (
                  <Polyline
                    key={idx}
                    positions={route.coordinates}
                    pathOptions={{
                      color: ROUTE_COLORS[idx % ROUTE_COLORS.length],
                      weight: idx === selectedRouteIndex ? 6 : 3,
                      opacity: idx === selectedRouteIndex ? 1 : 0.4,
                      dashArray: idx === selectedRouteIndex ? null : '8 6',
                    }}
                  />
                )
              ))}

              {/* Virtual Flood Zone */}
              {floodEnabled && floodCenter && (
                <Circle
                  center={[floodCenter.lat, floodCenter.lon]}
                  radius={floodRadius}
                  pathOptions={{ color: '#2563eb', fillColor: '#3b82f6', fillOpacity: 0.3, weight: 2 }}
                >
                  <Popup><b>Virtual Flood Zone</b><br/>Depth: {floodDepth}m<br/>Radius: {floodRadius}m</Popup>
                </Circle>
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
