import { useState } from 'react';
import { Loader2, RotateCcw, Navigation as NavIcon, Droplets } from 'lucide-react';
import { MapContainer, TileLayer, Marker, Polyline, Popup, useMapEvents, GeoJSON } from 'react-leaflet';
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

function MapClickHandler({ onClick }) { useMapEvents({ click: (e) => onClick(e.latlng) }); return null; }

export default function Navigation() {
  const [origin, setOrigin] = useState({ lat: '', lon: '', name: '' });
  const [destination, setDestination] = useState({ lat: '', lon: '', name: '' });
  const [place, setPlace] = useState('New Delhi, India');
  const [routes, setRoutes] = useState([]);
  const [selectedRouteIndex, setSelectedRouteIndex] = useState(0);
  const [isCalculating, setIsCalculating] = useState(false);
  const [error, setError] = useState(null);
  const [selectMode, setSelectMode] = useState(null);
  const [dbFloodZones, setDbFloodZones] = useState(null);
  const [loadingFlood, setLoadingFlood] = useState(false);
  const { selectedVehicle } = useVehicleStore();

  const getMapCenter = () => { if (origin.lat) return [parseFloat(origin.lat), parseFloat(origin.lon)]; return mapCenters[place] || [28.63, 77.22]; };
  const handleMapClick = (latlng) => { if (selectMode === 'origin') { setOrigin({ lat: latlng.lat.toFixed(5), lon: latlng.lng.toFixed(5), name: `${latlng.lat.toFixed(4)}, ${latlng.lng.toFixed(4)}` }); setSelectMode(null); } else if (selectMode === 'destination') { setDestination({ lat: latlng.lat.toFixed(5), lon: latlng.lng.toFixed(5), name: `${latlng.lat.toFixed(4)}, ${latlng.lng.toFixed(4)}` }); setSelectMode(null); } };
  const useGPS = () => { navigator.geolocation?.getCurrentPosition((pos) => setOrigin({ lat: pos.coords.latitude.toFixed(5), lon: pos.coords.longitude.toFixed(5), name: 'My Location' }), () => setError('GPS denied')); };
  const loadFloodZones = async () => { setLoadingFlood(true); try { const res = await axios.get(`${API_URL}/flood/zones/geojson`); setDbFloodZones(res.data); } catch (err) { console.error(err); } finally { setLoadingFlood(false); } };
  const handleCalculateRoute = async () => {
    if (!origin.lat || !destination.lat) { setError('Set both origin and destination'); return; }
    setIsCalculating(true); setError(null); setRoutes([]);
    try {
      const res = await axios.post(`${API_URL}/navigation/route`, { start_lat: parseFloat(origin.lat), start_lon: parseFloat(origin.lon), end_lat: parseFloat(destination.lat), end_lon: parseFloat(destination.lon), vehicle_type: selectedVehicle, k: 3, place, event_id: null });
      if (res.data.success && res.data.routes.length > 0) { setRoutes(res.data.routes); setSelectedRouteIndex(0); } else { setError(res.data.message || 'No routes found'); }
    } catch (err) { setError(err.response?.data?.detail || err.message || 'Failed'); }
    finally { setIsCalculating(false); }
  };

  return (
    <div className="p-4 max-w-7xl mx-auto">
      <h1 className="text-2xl font-bold text-gray-800 mb-4 flex items-center gap-2"><NavIcon className="w-6 h-6 text-primary-600" /> Flood-Safe Navigation</h1>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="space-y-3 overflow-y-auto max-h-[85vh]">
          <div className="card p-3"><label className="text-xs font-semibold text-gray-600 block mb-1">CITY / AREA</label><input type="text" value={place} onChange={(e) => setPlace(e.target.value)} className="input-field text-sm mb-2" placeholder="City name..." /><div className="flex flex-wrap gap-1">{cityPresets.map((c) => (<button key={c.name} onClick={() => setPlace(c.place)} className={`text-[10px] px-2 py-1 rounded ${place === c.place ? 'bg-primary-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}>{c.name}</button>))}</div></div>
          <div className="card p-3 border-l-4 border-green-500"><div className="flex items-center justify-between mb-2"><label className="text-xs font-semibold text-green-700">ORIGIN (A)</label><div className="flex gap-2"><button onClick={useGPS} className="text-[10px] px-2 py-0.5 bg-blue-50 text-blue-600 rounded">GPS</button><button onClick={() => setSelectMode('origin')} className={`text-[10px] px-2 py-0.5 rounded ${selectMode === 'origin' ? 'bg-green-600 text-white' : 'bg-green-50 text-green-600'}`}>{selectMode === 'origin' ? 'Clicking...' : 'Pick Map'}</button></div></div><div className="grid grid-cols-2 gap-2"><input type="number" step="any" value={origin.lat} onChange={(e) => setOrigin({...origin, lat: e.target.value})} className="input-field text-xs py-1.5" placeholder="Latitude" /><input type="number" step="any" value={origin.lon} onChange={(e) => setOrigin({...origin, lon: e.target.value})} className="input-field text-xs py-1.5" placeholder="Longitude" /></div>{origin.name && <p className="text-[10px] text-green-600 mt-1">{origin.name}</p>}</div>
          <div className="card p-3 border-l-4 border-red-500"><div className="flex items-center justify-between mb-2"><label className="text-xs font-semibold text-red-700">DESTINATION (B)</label><button onClick={() => setSelectMode('destination')} className={`text-[10px] px-2 py-0.5 rounded ${selectMode === 'destination' ? 'bg-red-600 text-white' : 'bg-red-50 text-red-600'}`}>{selectMode === 'destination' ? 'Clicking...' : 'Pick Map'}</button></div><div className="grid grid-cols-2 gap-2"><input type="number" step="any" value={destination.lat} onChange={(e) => setDestination({...destination, lat: e.target.value})} className="input-field text-xs py-1.5" placeholder="Latitude" /><input type="number" step="any" value={destination.lon} onChange={(e) => setDestination({...destination, lon: e.target.value})} className="input-field text-xs py-1.5" placeholder="Longitude" /></div>{destination.name && <p className="text-[10px] text-red-600 mt-1">{destination.name}</p>}</div>
          <VehicleSelector />
          <div className="card p-3 border-l-4 border-blue-500"><div className="flex items-center justify-between mb-1"><label className="text-xs font-semibold text-blue-700 flex items-center gap-1"><Droplets className="w-3 h-3" /> FLOOD ZONES</label><button onClick={loadFloodZones} className="text-[10px] px-2 py-0.5 rounded bg-blue-50 text-blue-600 hover:bg-blue-100">{loadingFlood ? 'Loading...' : 'Load from DB'}</button></div>{dbFloodZones && dbFloodZones.features?.length > 0 && (<div className="text-[10px] text-blue-600 bg-blue-50 p-1.5 rounded flex justify-between"><span>{dbFloodZones.features.length} zone(s)</span><button onClick={() => setDbFloodZones(null)} className="text-red-500 underline">Hide</button></div>)}</div>
          <button onClick={handleCalculateRoute} disabled={!origin.lat || !destination.lat || isCalculating} className="btn-primary w-full flex items-center justify-center gap-2 py-3">{isCalculating ? <Loader2 className="w-5 h-5 animate-spin" /> : <NavIcon className="w-5 h-5" />}{isCalculating ? 'Calculating...' : 'Find Safe Route'}</button>
          {error && <div className="bg-red-50 border border-red-200 rounded-lg p-2 text-xs text-red-700">{error}</div>}
          {routes.length > 0 && <button onClick={() => { setRoutes([]); setError(null); }} className="btn-secondary w-full flex items-center justify-center gap-2 text-sm"><RotateCcw className="w-4 h-4" /> Clear</button>}
          {routes.length > 0 && <div className="space-y-2">{routes.map((route, idx) => (<button key={idx} onClick={() => setSelectedRouteIndex(idx)} className={`w-full text-left p-3 rounded-lg border-2 text-xs ${idx === selectedRouteIndex ? 'border-purple-500 bg-purple-50' : 'border-gray-200'}`}><div className="flex justify-between"><span className="font-semibold" style={{color: ROUTE_COLORS[idx]}}>Route {idx+1}</span><span>{Math.round(route.risk_score*100)}% risk</span></div><div className="flex gap-3 mt-1 text-gray-600"><span>{(route.total_distance_m/1000).toFixed(1)}km</span><span>{Math.round(route.estimated_time_s/60)}min</span><span>{route.flooded_segments} flooded</span></div></button>))}</div>}
          {selectMode && <div className="bg-yellow-50 border border-yellow-300 rounded-lg p-2 text-xs text-yellow-800 animate-pulse">Click map for <strong>{selectMode}</strong> <button onClick={() => setSelectMode(null)} className="ml-2 underline">Cancel</button></div>}
        </div>
        <div className="lg:col-span-2">
          <div className="rounded-xl overflow-hidden shadow border border-gray-200 h-[600px]">
            <MapContainer center={getMapCenter()} zoom={12} className="w-full h-full" scrollWheelZoom={true}>
              <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" attribution="&copy; OpenStreetMap" />
              <MapClickHandler onClick={handleMapClick} />
              {origin.lat && <Marker position={[parseFloat(origin.lat), parseFloat(origin.lon)]} icon={originIcon}><Popup><b>Origin (A)</b></Popup></Marker>}
              {destination.lat && <Marker position={[parseFloat(destination.lat), parseFloat(destination.lon)]} icon={destIcon}><Popup><b>Destination (B)</b></Popup></Marker>}
              {routes.map((route, idx) => route.coordinates?.length > 0 && <Polyline key={idx} positions={route.coordinates} pathOptions={{ color: ROUTE_COLORS[idx % 3], weight: idx === selectedRouteIndex ? 6 : 3, opacity: idx === selectedRouteIndex ? 1 : 0.4, dashArray: idx === selectedRouteIndex ? null : '8 6' }} />)}
              {dbFloodZones?.features?.length > 0 && <GeoJSON key={JSON.stringify(dbFloodZones)} data={dbFloodZones} style={(f) => { const d = f.properties.max_depth || 0.5; return { color: d > 1 ? '#7f1d1d' : d > 0.6 ? '#ef4444' : d > 0.3 ? '#f97316' : '#3b82f6', fillOpacity: 0.3, weight: 2 }; }} onEachFeature={(f, layer) => layer.bindPopup(`<b>${f.properties.event_name||'Flood'}</b><br/>Depth: ${f.properties.max_depth}m`)} />}
            </MapContainer>
          </div>
          {routes[selectedRouteIndex] && <div className="mt-4 card p-4"><h3 className="text-sm font-semibold mb-2" style={{color: ROUTE_COLORS[selectedRouteIndex]}}>Route {selectedRouteIndex+1} Summary</h3><div className="grid grid-cols-4 gap-3 text-center text-sm"><div className="bg-gray-50 p-2 rounded"><p className="font-bold">{(routes[selectedRouteIndex].total_distance_m/1000).toFixed(1)}km</p><p className="text-[10px] text-gray-500">Distance</p></div><div className="bg-gray-50 p-2 rounded"><p className="font-bold">{Math.round(routes[selectedRouteIndex].estimated_time_s/60)}min</p><p className="text-[10px] text-gray-500">Time</p></div><div className="bg-gray-50 p-2 rounded"><p className="font-bold">{Math.round(routes[selectedRouteIndex].risk_score*100)}%</p><p className="text-[10px] text-gray-500">Risk</p></div><div className="bg-gray-50 p-2 rounded"><p className="font-bold">{routes[selectedRouteIndex].flooded_segments}</p><p className="text-[10px] text-gray-500">Flooded</p></div></div></div>}
        </div>
      </div>
    </div>
  );
}
