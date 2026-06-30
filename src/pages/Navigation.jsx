import React, { useState } from 'react';
import { Loader2, RotateCcw, Navigation as NavIcon, Droplets } from 'lucide-react';
import { MapContainer, TileLayer, Marker, Polyline, Popup, useMapEvents, GeoJSON, Polygon, useMap } from 'react-leaflet';
import L from 'leaflet';
import VehicleSelector from '../components/navigation/VehicleSelector';
import { useVehicleStore } from '../store/vehicleStore';
import axios from 'axios';

const API_URL = 'http://localhost:8000/api/v1';
const ROUTE_COLORS = ['#9B30FF', '#FF6600', '#000000'];
const originIcon = L.divIcon({ className: '', html: '<div style="background:#22c55e;width:28px;height:28px;border-radius:50%;border:3px solid white;box-shadow:0 2px 8px rgba(0,0,0,0.3);display:flex;align-items:center;justify-content:center;color:white;font-weight:bold;font-size:12px;">A</div>', iconSize: [28, 28], iconAnchor: [14, 14] });
const destIcon = L.divIcon({ className: '', html: '<div style="background:#ef4444;width:28px;height:28px;border-radius:50%;border:3px solid white;box-shadow:0 2px 8px rgba(0,0,0,0.3);display:flex;align-items:center;justify-content:center;color:white;font-weight:bold;font-size:12px;">B</div>', iconSize: [28, 28], iconAnchor: [14, 14] });
const cityPresets = [{ name: 'Delhi', place: 'New Delhi, India' }, { name: 'Gujrat PK', place: 'Gujrat, Punjab, Pakistan' }, { name: 'Mumbai', place: 'Mumbai, India' }, { name: 'Lahore', place: 'Lahore, Pakistan' }, { name: 'Chennai', place: 'Chennai, India' }];
const mapCenters = { 'New Delhi, India': [28.63, 77.22], 'Mumbai, India': [19.07, 72.87], 'Chennai, India': [13.08, 80.27], 'Gujrat, Punjab, Pakistan': [32.57, 73.67], 'Lahore, Pakistan': [31.52, 74.35] };

// City boundaries (approximate administrative polygons)
const cityBounds = {
  'New Delhi, India': [[28.40, 76.84], [28.88, 77.35]],
  'Mumbai, India': [[18.89, 72.77], [19.27, 72.98]],
  'Chennai, India': [[12.83, 80.10], [13.23, 80.33]],
  'Gujrat, Punjab, Pakistan': [[32.50, 73.60], [32.65, 73.80]],
  'Lahore, Pakistan': [[31.35, 74.20], [31.65, 74.45]],
};

const cityPolygons = {
  'New Delhi, India': [
    [28.88, 77.10], [28.85, 77.28], [28.78, 77.34], [28.70, 77.33],
    [28.62, 77.35], [28.55, 77.32], [28.50, 77.25], [28.48, 77.15],
    [28.50, 77.05], [28.55, 76.95], [28.62, 76.87], [28.70, 76.84],
    [28.78, 76.87], [28.85, 76.95], [28.88, 77.10],
  ],
  'Mumbai, India': [
    [19.27, 72.82], [19.25, 72.90], [19.20, 72.95], [19.12, 72.97],
    [19.05, 72.95], [18.97, 72.92], [18.92, 72.87], [18.90, 72.82],
    [18.92, 72.78], [18.97, 72.77], [19.05, 72.78], [19.12, 72.78],
    [19.20, 72.79], [19.25, 72.80], [19.27, 72.82],
  ],
  'Chennai, India': [
    [13.23, 80.18], [13.20, 80.28], [13.15, 80.32], [13.08, 80.30],
    [13.00, 80.28], [12.92, 80.25], [12.85, 80.22], [12.83, 80.18],
    [12.85, 80.14], [12.92, 80.12], [13.00, 80.11], [13.08, 80.12],
    [13.15, 80.14], [13.20, 80.16], [13.23, 80.18],
  ],
  'Gujrat, Punjab, Pakistan': [
    [32.62, 73.64], [32.61, 73.72], [32.59, 73.77], [32.56, 73.78],
    [32.53, 73.76], [32.51, 73.72], [32.50, 73.67], [32.51, 73.63],
    [32.53, 73.60], [32.56, 73.59], [32.59, 73.60], [32.61, 73.62],
    [32.62, 73.64],
  ],
  'Lahore, Pakistan': [
    [31.63, 74.28], [31.62, 74.38], [31.58, 74.43], [31.53, 74.44],
    [31.47, 74.42], [31.42, 74.38], [31.38, 74.33], [31.37, 74.28],
    [31.38, 74.23], [31.42, 74.20], [31.47, 74.20], [31.53, 74.21],
    [31.58, 74.23], [31.62, 74.25], [31.63, 74.28],
  ],
};

function MapClickHandler({ onClick }) { 
  const map = useMapEvents({ click: (e) => onClick(e.latlng) }); 
  // Fix map size calculation (prevents click offset in flex layouts)
  React.useEffect(() => {
    const timer = setInterval(() => map.invalidateSize(), 500);
    return () => clearInterval(timer);
  }, [map]);
  return null; 
}

function FitBounds({ bounds }) {
  const map = useMap();
  const [lastBounds, setLastBounds] = React.useState(null);
  React.useEffect(() => {
    if (bounds && JSON.stringify(bounds) !== JSON.stringify(lastBounds)) {
      map.fitBounds(bounds, { padding: [20, 20] });
      setLastBounds(bounds);
    }
  }, [bounds]);
  return null;
}

export default function Navigation() {
  const [originLat, setOriginLat] = useState('');
  const [originLon, setOriginLon] = useState('');
  const [originName, setOriginName] = useState('');
  const [destLat, setDestLat] = useState('');
  const [destLon, setDestLon] = useState('');
  const [destName, setDestName] = useState('');
  const [place, setPlace] = useState('New Delhi, India');
  const [routes, setRoutes] = useState([]);
  const [selectedRouteIndex, setSelectedRouteIndex] = useState(0);
  const [isCalculating, setIsCalculating] = useState(false);
  const [error, setError] = useState(null);
  const [selectMode, setSelectMode] = useState(null);
  const [dbFloodZones, setDbFloodZones] = useState(null);
  const [loadingFlood, setLoadingFlood] = useState(false);
  const { selectedVehicle } = useVehicleStore();

  const hasOrigin = originLat !== '' && originLon !== '' && !isNaN(parseFloat(originLat)) && !isNaN(parseFloat(originLon));
  const hasDest = destLat !== '' && destLon !== '' && !isNaN(parseFloat(destLat)) && !isNaN(parseFloat(destLon));
  const getMapCenter = () => { if (hasOrigin) return [parseFloat(originLat), parseFloat(originLon)]; return mapCenters[place] || [28.63, 77.22]; };

  const handleMapClick = (latlng) => {
    if (selectMode === 'origin') { setOriginLat(latlng.lat.toFixed(5)); setOriginLon(latlng.lng.toFixed(5)); setOriginName(`${latlng.lat.toFixed(4)}, ${latlng.lng.toFixed(4)}`); setSelectMode(null); }
    else if (selectMode === 'destination') { setDestLat(latlng.lat.toFixed(5)); setDestLon(latlng.lng.toFixed(5)); setDestName(`${latlng.lat.toFixed(4)}, ${latlng.lng.toFixed(4)}`); setSelectMode(null); }
  };

  const useGPS = () => { navigator.geolocation?.getCurrentPosition((pos) => { setOriginLat(pos.coords.latitude.toFixed(5)); setOriginLon(pos.coords.longitude.toFixed(5)); setOriginName('My Location'); }, () => setError('GPS denied')); };

  const loadFloodZones = async () => {
    setLoadingFlood(true);
    try { const res = await axios.get(`${API_URL}/flood/zones/geojson`); console.log('Flood data:', res.data); setDbFloodZones(res.data); }
    catch (err) { console.error('Flood load error:', err); setError('Failed to load flood zones'); }
    finally { setLoadingFlood(false); }
  };

  const handleCalculateRoute = async () => {
    if (!hasOrigin || !hasDest) { setError('Set both origin and destination'); return; }
    setIsCalculating(true); setError(null); setRoutes([]);
    try {
      const res = await axios.post(`${API_URL}/navigation/route`, { start_lat: parseFloat(originLat), start_lon: parseFloat(originLon), end_lat: parseFloat(destLat), end_lon: parseFloat(destLon), vehicle_type: selectedVehicle, k: 3, place, event_id: null });
      if (res.data.success && res.data.routes.length > 0) { setRoutes(res.data.routes); setSelectedRouteIndex(0); }
      else { setError(res.data.message || 'No routes found'); }
    } catch (err) { setError(err.response?.data?.detail || err.message || 'Failed'); }
    finally { setIsCalculating(false); }
  };

  return (
    <div className="p-4 max-w-7xl mx-auto">
      <h1 className="text-2xl font-bold text-gray-800 mb-4 flex items-center gap-2"><NavIcon className="w-6 h-6 text-primary-600" /> Flood-Safe Navigation</h1>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="space-y-3 overflow-y-auto max-h-[85vh]">
          {/* City */}
          <div className="card p-3">
            <label className="text-xs font-semibold text-gray-600 block mb-1">CITY / AREA</label>
            <input type="text" value={place} onChange={(e) => setPlace(e.target.value)} className="input-field text-sm mb-2" placeholder="City name..." />
            <div className="flex flex-wrap gap-1">{cityPresets.map((c) => (<button key={c.name} onClick={() => setPlace(c.place)} className={`text-[10px] px-2 py-1 rounded ${place === c.place ? 'bg-primary-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}>{c.name}</button>))}</div>
          </div>
          {/* Origin */}
          <div className="card p-3 border-l-4 border-green-500">
            <div className="flex items-center justify-between mb-2">
              <label className="text-xs font-semibold text-green-700">ORIGIN (A)</label>
              <div className="flex gap-2">
                <button onClick={useGPS} className="text-[10px] px-2 py-0.5 bg-blue-50 text-blue-600 rounded">GPS</button>
                <button onClick={() => setSelectMode('origin')} className={`text-[10px] px-2 py-0.5 rounded ${selectMode === 'origin' ? 'bg-green-600 text-white' : 'bg-green-50 text-green-600'}`}>{selectMode === 'origin' ? 'Clicking...' : 'Pick Map'}</button>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <input type="text" value={originLat} onChange={(e) => setOriginLat(e.target.value)} className="input-field text-xs py-1.5" placeholder="Latitude" />
              <input type="text" value={originLon} onChange={(e) => setOriginLon(e.target.value)} className="input-field text-xs py-1.5" placeholder="Longitude" />
            </div>
            {originName && <p className="text-[10px] text-green-600 mt-1">{originName}</p>}
          </div>
          {/* Destination */}
          <div className="card p-3 border-l-4 border-red-500">
            <div className="flex items-center justify-between mb-2">
              <label className="text-xs font-semibold text-red-700">DESTINATION (B)</label>
              <button onClick={() => setSelectMode('destination')} className={`text-[10px] px-2 py-0.5 rounded ${selectMode === 'destination' ? 'bg-red-600 text-white' : 'bg-red-50 text-red-600'}`}>{selectMode === 'destination' ? 'Clicking...' : 'Pick Map'}</button>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <input type="text" value={destLat} onChange={(e) => setDestLat(e.target.value)} className="input-field text-xs py-1.5" placeholder="Latitude" />
              <input type="text" value={destLon} onChange={(e) => setDestLon(e.target.value)} className="input-field text-xs py-1.5" placeholder="Longitude" />
            </div>
            {destName && <p className="text-[10px] text-red-600 mt-1">{destName}</p>}
          </div>
          {/* Vehicle */}
          <VehicleSelector />
          {/* Flood */}
          <div className="card p-3 border-l-4 border-blue-500">
            <div className="flex items-center justify-between mb-1">
              <label className="text-xs font-semibold text-blue-700 flex items-center gap-1"><Droplets className="w-3 h-3" /> FLOOD ZONES</label>
              <button onClick={loadFloodZones} disabled={loadingFlood} className="text-[10px] px-2 py-0.5 rounded bg-blue-50 text-blue-600 hover:bg-blue-100">{loadingFlood ? 'Loading...' : 'Load from DB'}</button>
            </div>
            {dbFloodZones && dbFloodZones.features?.length > 0 && <div className="text-[10px] text-blue-600 bg-blue-50 p-1.5 rounded flex justify-between"><span>{dbFloodZones.features.length} zone(s) on map</span><button onClick={() => setDbFloodZones(null)} className="text-red-500 underline">Hide</button></div>}
            {dbFloodZones && dbFloodZones.features?.length === 0 && <p className="text-[10px] text-gray-400 mt-1">No flood zones in DB. Insert via pgAdmin.</p>}
          </div>
          {/* Calculate */}
          <button onClick={handleCalculateRoute} disabled={!hasOrigin || !hasDest || isCalculating} className="btn-primary w-full flex items-center justify-center gap-2 py-3">
            {isCalculating ? <Loader2 className="w-5 h-5 animate-spin" /> : <NavIcon className="w-5 h-5" />}
            {isCalculating ? 'Calculating...' : 'Find Safe Route'}
          </button>
          {error && <div className="bg-red-50 border border-red-200 rounded-lg p-2 text-xs text-red-700">{error}</div>}
          {routes.length > 0 && <button onClick={() => { setRoutes([]); setError(null); }} className="btn-secondary w-full text-sm"><RotateCcw className="w-4 h-4 inline mr-1" />Clear</button>}
          {routes.length > 0 && <div className="space-y-2">{routes.map((route, idx) => (<button key={idx} onClick={() => setSelectedRouteIndex(idx)} className={`w-full text-left p-3 rounded-lg border-2 text-xs ${idx === selectedRouteIndex ? 'border-purple-500 bg-purple-50' : 'border-gray-200'}`}><div className="flex justify-between"><span className="font-semibold" style={{color:ROUTE_COLORS[idx]}}>Route {idx+1}</span><span>{Math.round(route.risk_score*100)}%</span></div><div className="flex gap-3 mt-1 text-gray-600"><span>{(route.total_distance_m/1000).toFixed(1)}km</span><span>{Math.round(route.estimated_time_s/60)}min</span><span>{route.flooded_segments} flooded</span></div></button>))}</div>}
          {selectMode && <div className="bg-yellow-50 border border-yellow-300 rounded-lg p-2 text-xs text-yellow-800 animate-pulse">Click map for <b>{selectMode}</b> <button onClick={() => setSelectMode(null)} className="ml-2 underline">Cancel</button></div>}
        </div>
        {/* Map */}
        <div className="lg:col-span-2">
          <div className="rounded-xl overflow-hidden shadow border border-gray-200 h-[600px]">
            <MapContainer center={getMapCenter()} zoom={12} className="w-full h-full" scrollWheelZoom={true}>
              <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" attribution="&copy; OpenStreetMap" />
              <MapClickHandler onClick={handleMapClick} />
              {cityBounds[place] && <FitBounds bounds={cityBounds[place]} />}
              {cityPolygons[place] && <Polygon positions={cityPolygons[place]} pathOptions={{color: '#6366f1', weight: 2, fillOpacity: 0.02, dashArray: '8 4'}} />}
              {hasOrigin && <Marker position={[parseFloat(originLat), parseFloat(originLon)]} icon={originIcon}><Popup><b>Origin (A)</b></Popup></Marker>}
              {hasDest && <Marker position={[parseFloat(destLat), parseFloat(destLon)]} icon={destIcon}><Popup><b>Destination (B)</b></Popup></Marker>}
              {routes.map((route, idx) => route.coordinates?.length > 0 && <Polyline key={idx} positions={route.coordinates} pathOptions={{color:ROUTE_COLORS[idx%3],weight:idx===selectedRouteIndex?6:3,opacity:idx===selectedRouteIndex?1:0.4,dashArray:idx===selectedRouteIndex?null:'8 6'}} />)}
              {dbFloodZones?.features?.length > 0 && <GeoJSON key={JSON.stringify(dbFloodZones)} data={dbFloodZones} style={(f) => ({fillColor: f.properties.max_depth > 1 ? '#ef4444' : f.properties.max_depth > 0.5 ? '#f97316' : '#3b82f6', color: '#1e40af', fillOpacity: 0.4, weight: 2})} onEachFeature={(f, layer) => layer.bindPopup(`<b>${f.properties.event_name||'Flood'}</b><br/>Depth: ${f.properties.max_depth}m<br/>Area: ${f.properties.area_km2} km2`)} />}
            </MapContainer>
          </div>
          {routes[selectedRouteIndex] && <div className="mt-4 card p-4"><h3 className="text-sm font-semibold mb-2" style={{color:ROUTE_COLORS[selectedRouteIndex]}}>Route {selectedRouteIndex+1}</h3><div className="grid grid-cols-4 gap-3 text-center text-sm"><div className="bg-gray-50 p-2 rounded"><p className="font-bold">{(routes[selectedRouteIndex].total_distance_m/1000).toFixed(1)}km</p><p className="text-[10px] text-gray-500">Distance</p></div><div className="bg-gray-50 p-2 rounded"><p className="font-bold">{Math.round(routes[selectedRouteIndex].estimated_time_s/60)}min</p><p className="text-[10px] text-gray-500">Time</p></div><div className="bg-gray-50 p-2 rounded"><p className="font-bold">{Math.round(routes[selectedRouteIndex].risk_score*100)}%</p><p className="text-[10px] text-gray-500">Risk</p></div><div className="bg-gray-50 p-2 rounded"><p className="font-bold">{routes[selectedRouteIndex].flooded_segments}</p><p className="text-[10px] text-gray-500">Flooded</p></div></div></div>}
        </div>
      </div>
    </div>
  );
}
